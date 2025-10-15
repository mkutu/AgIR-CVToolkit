# src/agir_cvtoolkit/pipelines/stages/train.py

"""
Training stage for segmentation models using PyTorch Lightning.

Integrates with the AgIR-CVToolkit pipeline:
- Optionally runs preprocessing before training
- Reads from preprocessed train/val splits
- Applies augmentations
- Trains segmentation models
- Saves checkpoints and metrics
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import torch
from omegaconf import DictConfig
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
from pytorch_lightning.loggers import Logger
from torch.utils.data import DataLoader

from agir_cvtoolkit.pipelines.utils.train_utils import (
    LitSegmentation,
    FieldDataset,
    get_batch_collate_fn,
    set_seed,
    seed_worker,
    select_available_gpus,
)

log = logging.getLogger(__name__)


class TrainingStage:
    """Training stage for segmentation models."""
    
    def __init__(self, cfg: DictConfig):
        self.cfg = cfg
        self.train_cfg = cfg.train
        self.paths = cfg.paths
        self.run_root = Path(cfg.paths.run_root)
        
        # Metrics tracking
        self.metrics = {
            "train_samples": 0,
            "val_samples": 0,
            "epochs_completed": 0,
            "best_val_loss": None,
            "best_checkpoint": None,
        }
    
    def _run_preprocessing_if_needed(self) -> None:
        """Run preprocessing if enabled and data not already processed."""
        if not self.train_cfg.get("auto_preprocess", False):
            log.info("Auto-preprocessing disabled, assuming data is ready")
            return
        
        # Check if preprocessed data already exists
        train_images = Path(self.train_cfg.train_images_dir)
        if train_images.exists() and any(train_images.iterdir()):
            log.info("Preprocessed training data found, skipping preprocessing")
            return
        
        # Run preprocessing
        log.info("=" * 80)
        log.info("Running preprocessing before training...")
        log.info("=" * 80)
        
        from agir_cvtoolkit.pipelines.stages.preprocess import PreprocessStage
        
        # Check if preprocess config exists
        if not hasattr(self.cfg, "preprocess"):
            log.warning("No preprocess config found, skipping preprocessing")
            return
        
        preprocess_stage = PreprocessStage(self.cfg)
        preprocess_stage.run()
        
        log.info("Preprocessing complete, continuing to training...")
        log.info("")
    
    def run(self) -> None:
        """Run the training pipeline."""
        log.info("=" * 80)
        log.info("Starting Training Pipeline")
        log.info("=" * 80)
        
        # Run preprocessing if needed
        self._run_preprocessing_if_needed()
        
        # Set seed for reproducibility
        set_seed(self.train_cfg.seed)
        
        # Setup device
        self._setup_device()
        
        # Verify data paths exist
        self._verify_data_paths()
        
        # Create datasets
        train_ds, val_ds = self._create_datasets()
        self.metrics["train_samples"] = len(train_ds)
        self.metrics["val_samples"] = len(val_ds)
        
        # Create dataloaders
        train_loader, val_loader = self._create_dataloaders(train_ds, val_ds)
        
        # Visualize data if enabled
        if self.train_cfg.get("dataloader_visualizer", {}).get("enabled", False):
            self._visualize_dataloader(train_loader)
        
        if self.train_cfg.get("augmentation_visualizer", {}).get("enabled", False):
            self._visualize_augmentations(train_loader)
        
        # Create model
        model = LitSegmentation(self.cfg)
        
        # Create loggers
        loggers = self._create_loggers()
        
        # Create callbacks
        checkpoint_cb, earlystop_cb = self._create_callbacks()
        
        # Create trainer
        trainer = self._create_trainer(loggers, [checkpoint_cb, earlystop_cb])
        
        # Train
        log.info(f"Training for {self.train_cfg.max_epochs} epochs...")
        trainer.fit(model, train_loader, val_loader)
        
        # Save metrics
        self.metrics["epochs_completed"] = trainer.current_epoch
        if checkpoint_cb.best_model_path:
            self.metrics["best_checkpoint"] = str(checkpoint_cb.best_model_path)
            self.metrics["best_val_loss"] = float(checkpoint_cb.best_model_score)
        
        metrics_path = Path(self.paths.metrics_path)
        with open(metrics_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
        
        # Export best model
        self._export_best_model(checkpoint_cb)
        
        # Summary
        log.info("=" * 80)
        log.info("Training Complete")
        log.info("=" * 80)
        log.info(f"Epochs completed: {self.metrics['epochs_completed']}")
        log.info(f"Best val loss: {self.metrics['best_val_loss']}")
        log.info(f"Best checkpoint: {self.metrics['best_checkpoint']}")
        log.info(f"Metrics saved to: {metrics_path}")
        log.info("=" * 80)
    
    def _verify_data_paths(self) -> None:
        """Verify that data directories exist and contain data."""
        train_images = Path(self.train_cfg.train_images_dir)
        train_masks = Path(self.train_cfg.train_masks_dir)
        val_images = Path(self.train_cfg.val_images_dir)
        val_masks = Path(self.train_cfg.val_masks_dir)
        
        errors = []
        if not train_images.exists():
            errors.append(f"Train images directory not found: {train_images}")
        elif not any(train_images.iterdir()):
            errors.append(f"Train images directory is empty: {train_images}")
        
        if not train_masks.exists():
            errors.append(f"Train masks directory not found: {train_masks}")
        elif not any(train_masks.iterdir()):
            errors.append(f"Train masks directory is empty: {train_masks}")
        
        if not val_images.exists():
            errors.append(f"Val images directory not found: {val_images}")
        elif not any(val_images.iterdir()):
            errors.append(f"Val images directory is empty: {val_images}")
        
        if not val_masks.exists():
            errors.append(f"Val masks directory not found: {val_masks}")
        elif not any(val_masks.iterdir()):
            errors.append(f"Val masks directory is empty: {val_masks}")
        
        if errors:
            error_msg = "\n".join(errors)
            raise FileNotFoundError(
                f"Data directories not found or empty:\n{error_msg}\n\n"
                f"Please run 'agir-cvtoolkit preprocess' first or set auto_preprocess=true"
            )
    
    def _setup_device(self) -> None:
        """Setup GPU device."""
        if torch.cuda.is_available():
            # Enable TF32 for Ampere+ GPUs
            if torch.cuda.get_device_capability(0)[0] >= 8:
                torch.set_float32_matmul_precision("high")
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
            
            # Select GPUs if configured
            if self.train_cfg.get("use_multi_gpu", False):
                gpu_cfg = self.train_cfg.get("gpu", {})
                max_gpus = gpu_cfg.get("max_gpus", 1)
                exclude_ids = gpu_cfg.get("exclude_ids", [])
                device_ids = select_available_gpus(max_gpus, exclude_ids, verbose=True)
                log.info(f"Using GPUs: {device_ids}")
    
    def _create_datasets(self):
        """Create train and validation datasets."""
        log.info("Creating datasets...")
        
        train_ds = FieldDataset(self.cfg, mode="train")
        val_ds = FieldDataset(self.cfg, mode="val")
        
        log.info(f"Train samples: {len(train_ds)}")
        log.info(f"Val samples: {len(val_ds)}")
        
        return train_ds, val_ds
    
    def _create_dataloaders(self, train_ds, val_ds):
        """Create train and validation dataloaders."""
        log.info("Creating dataloaders...")
        
        generator = torch.Generator()
        generator.manual_seed(self.train_cfg.seed)
        
        train_collate_fn = get_batch_collate_fn(
            self.cfg.augment.train.get("batch", {})
        )
        val_collate_fn = get_batch_collate_fn(
            self.cfg.augment.val.get("batch", {})
        )
        
        train_loader = DataLoader(
            train_ds,
            batch_size=self.train_cfg.batch_size,
            shuffle=True,
            num_workers=self.train_cfg.num_workers,
            pin_memory=self.train_cfg.pin_memory,
            worker_init_fn=seed_worker,
            generator=generator,
            collate_fn=train_collate_fn,
        )
        
        val_loader = DataLoader(
            val_ds,
            batch_size=self.train_cfg.batch_size,
            shuffle=False,
            num_workers=self.train_cfg.num_workers,
            pin_memory=self.train_cfg.pin_memory,
            worker_init_fn=seed_worker,
            generator=generator,
            collate_fn=val_collate_fn,
        )
        
        return train_loader, val_loader
    
    def _visualize_dataloader(self, train_loader):
        """Visualize dataloader batches."""
        log.info("Visualizing dataloader batches...")
        from agir_cvtoolkit.pipelines.utils.train_utils import vis_dataloader_batch
        
        vis_cfg = self.train_cfg.dataloader_visualizer
        loggers = self._create_loggers()
        vis_dataloader_batch(
            self.cfg,
            train_loader,
            loggers,
            num_samples=vis_cfg.get("num_samples", 4)
        )
    
    def _visualize_augmentations(self, train_loader):
        """Visualize augmentation pipeline."""
        log.info("Visualizing augmentations...")
        from agir_cvtoolkit.pipelines.utils.train_utils import vis_augmentation_batch
        
        vis_cfg = self.train_cfg.augmentation_visualizer
        loggers = self._create_loggers()
        vis_augmentation_batch(
            train_loader,
            loggers,
            num_samples=vis_cfg.get("num_samples", 4)
        )
    
    def _create_loggers(self) -> List[Logger]:
        """Create PyTorch Lightning loggers."""
        import hydra
        
        loggers = []
        logger_cfg = self.train_cfg.get("logger", {})
        
        # CSV logger
        if logger_cfg.get("csv", {}).get("enable", True):
            csv_cfg = logger_cfg.csv
            loggers.append(hydra.utils.instantiate(csv_cfg))
        
        # WandB logger
        if logger_cfg.get("wandb", {}).get("enable", False):
            wandb_cfg = logger_cfg.wandb
            loggers.append(hydra.utils.instantiate(wandb_cfg))
        
        return loggers
    
    def _create_callbacks(self):
        """Create training callbacks."""
        # Checkpoint callback
        checkpoint_path = self.run_root / "checkpoints"
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        checkpoint_cfg = self.train_cfg.checkpoint
        checkpoint_cb = ModelCheckpoint(
            dirpath=str(checkpoint_path),
            filename="{epoch:02d}-{step}-{val_loss:.2f}",
            monitor=checkpoint_cfg.get("monitor", "val_loss"),
            mode=checkpoint_cfg.get("mode", "min"),
            save_top_k=checkpoint_cfg.get("save_top_k", 3),
            save_last=checkpoint_cfg.get("save_last", True),
        )
        
        # Early stopping callback
        earlystop_cfg = self.train_cfg.early_stop
        earlystop_cb = EarlyStopping(
            monitor=earlystop_cfg.get("monitor", "val_loss"),
            mode=earlystop_cfg.get("mode", "min"),
            patience=earlystop_cfg.get("patience", 10),
        )
        
        return checkpoint_cb, earlystop_cb
    
    def _create_trainer(self, loggers, callbacks):
        """Create PyTorch Lightning trainer."""
        trainer_cfg = self.train_cfg.trainer
        
        trainer = Trainer(
            accelerator=trainer_cfg.get("accelerator", "auto"),
            precision=trainer_cfg.get("precision", "32"),
            max_epochs=self.train_cfg.max_epochs,
            deterministic=trainer_cfg.get("deterministic", False),
            logger=loggers,
            callbacks=callbacks,
            default_root_dir=str(self.run_root),
            strategy=trainer_cfg.get("strategy", "auto"),
        )
        
        return trainer
    
    def _export_best_model(self, checkpoint_cb):
        """Export best model weights as .pth file."""
        best_ckpt_path = checkpoint_cb.best_model_path
        if not best_ckpt_path:
            log.warning("No best checkpoint found, skipping export")
            return
        
        log.info(f"Exporting best model from: {best_ckpt_path}")
        
        # Load checkpoint
        ckpt = torch.load(best_ckpt_path, map_location="cpu", weights_only=False)
        model_weights = ckpt["state_dict"]
        
        # Export directory
        export_path = self.run_root / "model"
        export_path.mkdir(parents=True, exist_ok=True)
        
        # Save weights
        ckpt_filename = Path(best_ckpt_path).stem + ".pth"
        torch.save(model_weights, export_path / ckpt_filename)
        
        log.info(f"Best model weights exported to: {export_path / ckpt_filename}")