# src/agir_cvtoolkit/pipelines/stages/preprocess.py

"""
Preprocessing stage for training data preparation.

Workflow:
1. Load images/masks from CVAT download or custom directory
2. Standardize sizes via pad/grid-crop/resize
3. Split into train/val/test sets
4. Compute dataset statistics for normalization
"""

import json
import logging
from pathlib import Path

from omegaconf import DictConfig

from agir_cvtoolkit.pipelines.utils.preprocess_utils import (
    pad_gridcrop_resize,
    train_val_test_split,
    compute_rgb_mean_std,
)

log = logging.getLogger(__name__)


class PreprocessStage:
    """Preprocessing stage for training data preparation."""
    
    def __init__(self, cfg: DictConfig):
        self.cfg = cfg
        self.preprocess_cfg = cfg.preprocess
        self.paths = cfg.paths
        self.run_root = Path(cfg.paths.run_root)
        
        # Metrics tracking
        self.metrics = {
            "source_images": 0,
            "preprocessed_images": 0,
            "train_samples": 0,
            "val_samples": 0,
            "test_samples": 0,
            "rgb_mean": None,
            "rgb_std": None,
        }
    
    def _find_source_data(self) -> tuple[Path, Path]:
        """
        Find source images and masks based on config.
        
        Returns:
            Tuple of (images_dir, masks_dir)
        """
        source_cfg = self.preprocess_cfg.source
        
        if source_cfg.type == "cvat_download":
            # Find latest CVAT download in run folder
            cvat_downloads = Path(self.paths.cvat_downloads)
            
            if not cvat_downloads.exists():
                raise FileNotFoundError(
                    f"CVAT downloads directory not found: {cvat_downloads}\n"
                    f"Run 'agir-cvtoolkit download-cvat' first"
                )
            
            # Find task directories
            task_dirs = [d for d in cvat_downloads.iterdir() if d.is_dir()]
            if not task_dirs:
                raise FileNotFoundError(
                    f"No CVAT task directories found in: {cvat_downloads}"
                )
            
            # Use first task directory (or could aggregate multiple)
            task_dir = task_dirs[0]
            log.info(f"Using CVAT task directory: {task_dir.name}")
            
            # Find images and annotations
            images_dir = task_dir / "images"
            annotations_dir = task_dir / "annotations"
            
            # For mask-based formats, masks are in annotations/
            # For YOLO/COCO, we'd need to convert - for now assume masks exist
            if not images_dir.exists():
                raise FileNotFoundError(f"Images directory not found: {images_dir}")
            
            # Masks might be in different locations depending on export format
            masks_dir = annotations_dir
            if not masks_dir.exists():
                # Try looking for masks in images dir (some formats put them there)
                masks_dir = images_dir
            
            return images_dir, masks_dir
        
        elif source_cfg.type == "custom":
            images_dir = Path(source_cfg.custom_images_dir)
            masks_dir = Path(source_cfg.custom_masks_dir)
            
            if not images_dir.exists():
                raise FileNotFoundError(f"Custom images directory not found: {images_dir}")
            if not masks_dir.exists():
                raise FileNotFoundError(f"Custom masks directory not found: {masks_dir}")
            
            return images_dir, masks_dir
        
        else:
            raise ValueError(f"Unknown source type: {source_cfg.type}")
    
    def run(self) -> None:
        """Run the preprocessing pipeline."""
        log.info("=" * 80)
        log.info("Starting Preprocessing Pipeline")
        log.info("=" * 80)
        
        # Find source data
        source_images, source_masks = self._find_source_data()
        
        # Count source images
        source_image_files = list(source_images.glob("*.jpg")) + list(source_images.glob("*.png"))
        self.metrics["source_images"] = len(source_image_files)
        log.info(f"Found {self.metrics['source_images']} source images")
        
        # Create output directories
        preprocessed_images = Path(self.paths.preprocessed_images)
        preprocessed_masks = Path(self.paths.preprocessed_masks)
        preprocessed_images.mkdir(parents=True, exist_ok=True)
        preprocessed_masks.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Pad/Grid-Crop/Resize
        if self.preprocess_cfg.pad_gridcrop_resize.enabled:
            log.info("")
            log.info("Step 1: Standardizing image sizes (pad/grid-crop/resize)...")
            log.info("-" * 80)
            
            pad_gridcrop_resize(
                images_dir=source_images,
                masks_dir=source_masks,
                out_images=preprocessed_images,
                out_masks=preprocessed_masks,
                cfg=self.preprocess_cfg.pad_gridcrop_resize,
            )
            
            # Count preprocessed images
            preprocessed_files = list(preprocessed_images.glob("*.jpg")) + list(preprocessed_images.glob("*.png"))
            self.metrics["preprocessed_images"] = len(preprocessed_files)
            log.info(f"Created {self.metrics['preprocessed_images']} preprocessed images")
        else:
            log.info("Skipping pad/grid-crop/resize (disabled)")
            # Copy source files directly
            import shutil
            for img_path in source_image_files:
                shutil.copy2(img_path, preprocessed_images / img_path.name)
                mask_path = source_masks / f"{img_path.stem}_mask.png"
                if mask_path.exists():
                    shutil.copy2(mask_path, preprocessed_masks / mask_path.name)
            self.metrics["preprocessed_images"] = self.metrics["source_images"]
        
        # Step 2: Train/Val/Test Split
        if self.preprocess_cfg.split.enabled:
            log.info("")
            log.info("Step 2: Splitting into train/val/test sets...")
            log.info("-" * 80)
            
            # Output directories
            train_images = self.run_root / "train" / "images"
            train_masks = self.run_root / "train" / "masks"
            val_images = self.run_root / "val" / "images"
            val_masks = self.run_root / "val" / "masks"
            test_images = self.run_root / "test" / "images"
            test_masks = self.run_root / "test" / "masks"
            
            # Use seed from split config or fall back to train seed
            seed = self.preprocess_cfg.split.get('seed') or self.cfg.train.seed
            
            n_train, n_val, n_test = train_val_test_split(
                images_dir=preprocessed_images,
                masks_dir=preprocessed_masks,
                train_images=train_images,
                train_masks=train_masks,
                val_images=val_images,
                val_masks=val_masks,
                test_images=test_images,
                test_masks=test_masks,
                cfg=self.preprocess_cfg.split,
                seed=seed,
            )
            
            self.metrics["train_samples"] = n_train
            self.metrics["val_samples"] = n_val
            self.metrics["test_samples"] = n_test
        else:
            log.info("Skipping train/val/test split (disabled)")
        
        # Step 3: Compute Dataset Statistics
        if self.preprocess_cfg.compute_data_stats.enabled:
            log.info("")
            log.info("Step 3: Computing dataset statistics...")
            log.info("-" * 80)
            
            train_images = self.run_root / "train" / "images"
            stats_file = self.run_root / "datastats" / "rgb_mean_std.json"
            
            if train_images.exists() and any(train_images.iterdir()):
                stats = compute_rgb_mean_std(
                    images_dir=train_images,
                    out_file=stats_file,
                    cfg=self.preprocess_cfg.compute_data_stats,
                )
                
                self.metrics["rgb_mean"] = stats["mean"]
                self.metrics["rgb_std"] = stats["std"]
            else:
                log.warning("Train images not found, skipping statistics computation")
        else:
            log.info("Skipping dataset statistics computation (disabled)")
        
        # Save metrics
        metrics_path = Path(self.paths.metrics_path)
        with open(metrics_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
        
        # Summary
        log.info("")
        log.info("=" * 80)
        log.info("Preprocessing Complete")
        log.info("=" * 80)
        log.info(f"Source images: {self.metrics['source_images']}")
        log.info(f"Preprocessed images: {self.metrics['preprocessed_images']}")
        if self.preprocess_cfg.split.enabled:
            log.info(f"Train samples: {self.metrics['train_samples']}")
            log.info(f"Val samples: {self.metrics['val_samples']}")
            log.info(f"Test samples: {self.metrics['test_samples']}")
        if self.metrics['rgb_mean']:
            log.info(f"RGB mean: {self.metrics['rgb_mean']}")
            log.info(f"RGB std: {self.metrics['rgb_std']}")
        log.info(f"Metrics saved to: {metrics_path}")
        log.info("=" * 80)