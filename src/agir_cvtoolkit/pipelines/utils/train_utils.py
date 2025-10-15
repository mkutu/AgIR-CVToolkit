# src/agir_cvtoolkit/pipelines/utils/train_utils.py

"""
Training utilities for AgIR-CVToolkit.

Consolidates:
- Dataset classes
- Augmentation builders
- Batch collate functions
- Lightning module
- Visualization tools
- Helper utilities
"""

from __future__ import annotations

import json
import logging
import math
import random
import re
from pathlib import Path
from typing import Any, Callable, List, Tuple

import albumentations as A
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import GPUtil
import torch
import torch.nn as nn
import torch.nn.functional as F
from albumentations.pytorch import ToTensorV2
from omegaconf import DictConfig
from PIL import Image
from pytorch_lightning import LightningModule
from torch import Tensor
from torch.utils.data import Dataset
from torch.utils.data._utils.collate import default_collate
from torchmetrics.classification import BinaryJaccardIndex as IoU
from torchmetrics.classification import BinaryF1Score as Dice
from torchvision import transforms
from torchvision.utils import make_grid, save_image
import torchvision
import segmentation_models_pytorch as smp

log = logging.getLogger(__name__)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def set_seed(seed: int) -> None:
    """Set random seed for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def seed_worker(worker_id):
    """Worker seed function for DataLoader."""
    worker_seed = torch.initial_seed() % 2**32
    np.random.seed(worker_seed)
    random.seed(worker_seed)

def select_available_gpus(
    max_gpus: int = 1,
    exclude_ids: List[int] = None,
    verbose: bool = True,
) -> List[int]:
    """Select available GPU IDs, excluding specified ones."""
    if GPUtil is None:
        log.warning("GPUtil not available, returning [0]")
        return [0]
    
    exclude_ids = exclude_ids or []
    available = GPUtil.getAvailable(
        order="memory",
        limit=8,
        maxLoad=0.5,
        maxMemory=0.5,
    )
    filtered = [gpu for gpu in available if gpu not in exclude_ids]
    
    if not filtered:
        log.warning(f"No suitable GPUs after excluding {exclude_ids}, using [0]")
        return [0]
    
    chosen = filtered[:max_gpus]
    if verbose:
        log.info(f"Selected GPU IDs: {chosen}")
    return chosen

def natural_base_key(p: Path) -> List:
    """Natural sorting key for file paths."""
    stem = p.stem
    if stem.endswith("_mask"):
        stem = stem[:-5]
    parts = re.split(r"(\d+)", stem)
    return [int(tok) if tok.isdigit() else tok for tok in parts]

# ============================================================================
# DATASET CLASS
# ============================================================================

class FieldDataset(Dataset):
    """Dataset for field segmentation tasks using image-mask pairs."""
    
    def __init__(self, cfg: DictConfig, mode: str = "train") -> None:
        """
        Initialize the dataset.
        
        Args:
            cfg: Hydra configuration
            mode: Dataset split ('train', 'val', or 'test')
        """
        self.cfg_aug = cfg.augment
        
        # Determine directories
        if mode == "train":
            img_dir = Path(cfg.paths.train_images_dir)
            mask_dir = Path(cfg.paths.train_masks_dir)
        elif mode == "val":
            img_dir = Path(cfg.paths.val_images_dir)
            mask_dir = Path(cfg.paths.val_masks_dir)
        elif mode == "test":
            img_dir = Path(cfg.paths.test_images_dir)
            mask_dir = Path(cfg.paths.test_masks_dir)
        else:
            raise ValueError(f"Unsupported mode: {mode}")
        
        # List files
        self.images = sorted(img_dir.glob("*"), key=natural_base_key)
        self.masks = sorted(mask_dir.glob("*"), key=natural_base_key)
        
        if len(self.images) != len(self.masks):
            raise RuntimeError(
                f"Images ({len(self.images)}) and masks ({len(self.masks)}) mismatch"
            )
        
        # Verify pairing
        mismatches = []
        for img_path, mask_path in zip(self.images, self.masks):
            if not mask_path.stem.startswith(img_path.stem):
                mismatches.append((img_path.name, mask_path.name))
        
        if mismatches:
            raise RuntimeError(f"Found {len(mismatches)} pairing mismatches")
        
        # Normalization
        self.use_norm = bool(cfg.train.get("use_data_normalization", False))
        if self.use_norm:
            stats_path = Path(cfg.paths.project_datastats_dir) / "rgb_mean_std.json"
            with open(stats_path) as f:
                stats = json.load(f)
            self.normalize = transforms.Normalize(
                mean=stats["mean"],
                std=stats["std"]
            )
        else:
            self.normalize = None
        
        # Augmentations
        self.use_augment = bool(cfg.train.get("use_data_augmentation", False))
        if self.use_augment:
            if mode == "train":
                self.transform = get_train_transforms(cfg)
            elif mode == "val":
                self.transform = get_val_transforms(cfg)
            else:
                self.transform = get_test_transforms(cfg)
        else:
            self.transform = get_noop_transform()
    
    def __len__(self) -> int:
        return len(self.images)
    
    def __getitem__(self, idx: int) -> Tuple[Tensor, Tensor]:
        """Get image and mask tensors."""
        # Load images
        img = Image.open(self.images[idx]).convert("RGB")
        mask = Image.open(self.masks[idx]).convert("L")
        
        # Apply augmentations
        arr = self.transform(
            image=np.array(img),
            mask=np.array(mask)
        )
        img_tensor = arr["image"].float() / 255.0
        mask_tensor = arr["mask"].unsqueeze(0).float()
        
        # Apply normalization
        if self.normalize is not None:
            img_tensor = self.normalize(img_tensor)
        
        # Ensure binary mask
        mask_tensor = (mask_tensor > 0.5).float()
        
        return img_tensor, mask_tensor
    
    def get_file_paths(self, idx: int) -> Tuple[str, str]:
        """Get file paths for a sample."""
        return str(self.images[idx]), str(self.masks[idx])

# ============================================================================
# AUGMENTATION BUILDERS
# ============================================================================

def get_train_transforms(cfg) -> A.ReplayCompose:
    """Build training augmentation pipeline."""
    t = cfg.augment.train
    H = int(t.img_size.height)
    W = int(t.img_size.width)
    
    pipeline = []
    
    # Add spatial transforms if enabled
    if getattr(t, "spatial", None) and t.spatial.get("enable", False):
        spatial_ops = _build_spatial_transforms(t.spatial, H, W)
        pipeline.extend(spatial_ops)
    
    # Add pixel transforms if enabled
    if getattr(t, "pixel", None) and t.pixel.get("enable", False):
        pixel_ops = _build_pixel_transforms(t.pixel)
        pipeline.extend(pixel_ops)
    
    # Final resize
    pipeline.append(A.Resize(height=H, width=W, p=1.0))
    
    # Convert to tensor
    pipeline.append(ToTensorV2())
    
    return A.ReplayCompose(
        transforms=pipeline,
        additional_targets={"mask": "mask"},
    )

def get_val_transforms(cfg) -> A.Compose:
    """Build validation augmentation pipeline."""
    t = cfg.augment.val
    H = int(t.img_size.height)
    W = int(t.img_size.width)
    
    pipeline = [
        A.Resize(height=H, width=W, p=1.0),
        ToTensorV2()
    ]
    
    return A.Compose(
        transforms=pipeline,
        additional_targets={"mask": "mask"},
    )

def get_test_transforms(cfg) -> A.Compose:
    """Build test augmentation pipeline."""
    return get_val_transforms(cfg)

def get_noop_transform() -> A.Compose:
    """No-op transform pipeline."""
    return A.Compose(
        [A.NoOp(), ToTensorV2()],
        additional_targets={"mask": "mask"}
    )

def _build_spatial_transforms(cfg, H, W) -> List[A.BasicTransform]:
    """Build spatial augmentations (affect image and mask)."""
    ops = []
    
    # Flips
    if cfg.get("horizontal_flip", {}).get("enable", False):
        p = cfg.horizontal_flip.get("p", 0.5)
        ops.append(A.HorizontalFlip(p=p))
    
    if cfg.get("vertical_flip", {}).get("enable", False):
        p = cfg.vertical_flip.get("p", 0.5)
        ops.append(A.VerticalFlip(p=p))
    
    # Rotation
    if cfg.get("random_rotate90", {}).get("enable", False):
        p = cfg.random_rotate90.get("p", 0.5)
        ops.append(A.RandomRotate90(p=p))
    
    # Affine
    if cfg.get("affine", {}).get("enable", False):
        spec = cfg.affine
        ops.append(A.Affine(
            scale=spec.get("scale", (0.9, 1.1)),
            rotate=spec.get("rotate", (-15, 15)),
            p=spec.get("p", 0.5)
        ))
    
    # ShiftScaleRotate
    if cfg.get("shift_scale_rotate", {}).get("enable", False):
        spec = cfg.shift_scale_rotate
        ops.append(A.ShiftScaleRotate(
            shift_limit=spec.get("shift_limit", 0.1),
            scale_limit=spec.get("scale_limit", 0.1),
            rotate_limit=spec.get("rotate_limit", 15),
            p=spec.get("p", 0.5)
        ))
    
    return ops

def _build_pixel_transforms(cfg) -> List[A.BasicTransform]:
    """Build pixel-level augmentations (image only)."""
    ops = []
    
    # Brightness/Contrast
    if cfg.get("random_brightness_contrast", {}).get("enable", False):
        spec = cfg.random_brightness_contrast
        ops.append(A.RandomBrightnessContrast(
            brightness_limit=spec.get("brightness_limit", 0.2),
            contrast_limit=spec.get("contrast_limit", 0.2),
            p=spec.get("p", 0.5)
        ))
    
    # Color jitter
    if cfg.get("color_jitter", {}).get("enable", False):
        spec = cfg.color_jitter
        ops.append(A.ColorJitter(
            brightness=spec.get("brightness", 0.2),
            contrast=spec.get("contrast", 0.2),
            saturation=spec.get("saturation", 0.2),
            hue=spec.get("hue", 0.1),
            p=spec.get("p", 0.5)
        ))
    
    # Blur
    if cfg.get("gaussian_blur", {}).get("enable", False):
        spec = cfg.gaussian_blur
        ops.append(A.GaussianBlur(
            blur_limit=spec.get("blur_limit", (3, 7)),
            p=spec.get("p", 0.3)
        ))
    
    # Noise
    if cfg.get("gauss_noise", {}).get("enable", False):
        spec = cfg.gauss_noise
        ops.append(A.GaussNoise(
            var_limit=spec.get("var_limit", (10, 50)),
            p=spec.get("p", 0.3)
        ))
    
    return ops

# ============================================================================
# BATCH-LEVEL AUGMENTATIONS (COLLATE FUNCTIONS)
# ============================================================================

def mixup_collate(
    batch: List[Tuple[torch.Tensor, torch.Tensor]],
    p: float,
    alpha: float
) -> Tuple[torch.Tensor, torch.Tensor]:
    """MixUp augmentation."""
    imgs, masks = zip(*batch)
    imgs = torch.stack(imgs, 0)
    masks = torch.stack(masks, 0)
    
    if random.random() < p:
        lam = np.random.beta(alpha, alpha)
        idx = torch.randperm(imgs.size(0))
        mixed_imgs = lam * imgs + (1 - lam) * imgs[idx]
        mixed_masks = lam * masks + (1 - lam) * masks[idx]
        return mixed_imgs, mixed_masks
    
    return imgs, masks

def cutmix_collate(
    batch: List[Tuple[torch.Tensor, torch.Tensor]],
    p: float,
    alpha: float
) -> Tuple[torch.Tensor, torch.Tensor]:
    """CutMix augmentation."""
    imgs, masks = zip(*batch)
    imgs = torch.stack(imgs, 0)
    masks = torch.stack(masks, 0)
    B, C_img, H, W = imgs.shape
    
    if B >= 2 and random.random() < p:
        out_idx = random.randrange(B)
        other_idx = random.choice([i for i in range(B) if i != out_idx])
        
        lam = np.random.beta(alpha, alpha)
        cut_rat = np.sqrt(1.0 - lam)
        cut_w = int(W * cut_rat)
        cut_h = int(H * cut_rat)
        cx = random.randrange(W)
        cy = random.randrange(H)
        x1 = max(0, cx - cut_w // 2)
        y1 = max(0, cy - cut_h // 2)
        x2 = min(W, cx + cut_w // 2)
        y2 = min(H, cy + cut_h // 2)
        
        new_img = imgs[out_idx].clone()
        new_mask = masks[out_idx].clone()
        new_img[:, y1:y2, x1:x2] = imgs[other_idx][:, y1:y2, x1:x2]
        new_mask[:, y1:y2, x1:x2] = masks[other_idx][:, y1:y2, x1:x2]
        
        imgs[out_idx] = new_img
        masks[out_idx] = new_mask
    
    return imgs, masks

def mosaic_collate(
    batch: List[Tuple[torch.Tensor, torch.Tensor]],
    p: float
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Mosaic augmentation."""
    imgs, masks = zip(*batch)
    imgs = torch.stack(imgs, 0)
    masks = torch.stack(masks, 0)
    B, C_img, H, W = imgs.shape
    
    if random.random() < p and B >= 4:
        src_idxs = random.sample(range(B), 4)
        q_imgs = imgs[src_idxs]
        q_masks = masks[src_idxs]
        
        canvas_img = torch.zeros((C_img, 2*H, 2*W), device=imgs.device, dtype=imgs.dtype)
        canvas_mask = torch.zeros((1, 2*H, 2*W), device=masks.device, dtype=masks.dtype)
        
        canvas_img[:, :H, :W] = q_imgs[0]
        canvas_img[:, :H, W:2*W] = q_imgs[1]
        canvas_img[:, H:2*H, :W] = q_imgs[2]
        canvas_img[:, H:2*H, W:2*W] = q_imgs[3]
        
        canvas_mask[:, :H, :W] = q_masks[0]
        canvas_mask[:, :H, W:2*W] = q_masks[1]
        canvas_mask[:, H:2*H, :W] = q_masks[2]
        canvas_mask[:, H:2*H, W:2*W] = q_masks[3]
        
        mos_img = F.interpolate(
            canvas_img.unsqueeze(0),
            size=(H, W),
            mode="bilinear",
            align_corners=False
        ).squeeze(0)
        mos_mask = F.interpolate(
            canvas_mask.unsqueeze(0),
            size=(H, W),
            mode="nearest"
        ).squeeze(0)
        
        out_idx = random.randrange(B)
        imgs[out_idx] = mos_img
        masks[out_idx] = mos_mask
    
    return imgs, masks

def get_batch_collate_fn(batch_cfg: Any) -> Callable:
    """Build collate function with batch-level augmentations."""
    if not batch_cfg or not batch_cfg.get("enable", False):
        return default_collate
    
    def collate(batch):
        imgs, masks = default_collate(batch)
        
        if batch_cfg.get("mosaic", {}).get("enable", False):
            imgs, masks = mosaic_collate(
                list(zip(imgs, masks)),
                p=batch_cfg.mosaic.get("p", 0.5)
            )
        
        if batch_cfg.get("cutmix", {}).get("enable", False):
            imgs, masks = cutmix_collate(
                list(zip(imgs, masks)),
                p=batch_cfg.cutmix.get("p", 0.5),
                alpha=batch_cfg.cutmix.get("alpha", 1.0)
            )
        
        if batch_cfg.get("mixup", {}).get("enable", False):
            imgs, masks = mixup_collate(
                list(zip(imgs, masks)),
                p=batch_cfg.mixup.get("p", 0.5),
                alpha=batch_cfg.mixup.get("alpha", 0.2)
            )
        
        return imgs, masks
    
    return collate

# ============================================================================
# LIGHTNING MODULE
# ============================================================================

class LitSegmentation(LightningModule):
    """PyTorch Lightning module for semantic segmentation."""
    
    def __init__(self, cfg: DictConfig) -> None:
        super().__init__()
        self.save_hyperparameters(cfg)
        self.cfg = cfg
        
        if smp is None:
            raise ImportError("segmentation_models_pytorch required for training")
        
        # Build model
        model_kwargs = {
            "arch": cfg.model.arch_name,
            "encoder_name": cfg.model.encoder_name,
            "encoder_weights": cfg.model.get("encoder_weights", "imagenet"),
            "in_channels": cfg.model.in_channels,
            "classes": cfg.model.classes,
        }
        
        if cfg.model.get("decoder_attention_type"):
            model_kwargs["decoder_attention_type"] = cfg.model.decoder_attention_type
        
        self.model = smp.create_model(**model_kwargs)
        
        # Loss
        self.loss_fn = nn.BCEWithLogitsLoss()
        
        # Metrics
        self.train_iou = IoU()
        self.val_iou = IoU()
        self.train_dice = Dice()
        self.val_dice = Dice()
        
        # Learning rate
        self.lr = cfg.train.optimizer.lr
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)
    
    def training_step(self, batch, batch_idx):
        imgs, masks = batch
        logits = self(imgs)
        loss = self.loss_fn(logits, masks)
        
        preds = (torch.sigmoid(logits) > 0.5).long()
        self.train_iou.update(preds, masks.long())
        self.train_dice.update(preds, masks.long())
        
        self.log("train/loss", loss, on_step=False, on_epoch=True)
        self.log("train/iou", self.train_iou, on_step=False, on_epoch=True)
        self.log("train/dice", self.train_dice, on_step=False, on_epoch=True)
        
        return loss
    
    def validation_step(self, batch, batch_idx):
        imgs, masks = batch
        logits = self(imgs)
        loss = self.loss_fn(logits, masks)
        
        preds = (torch.sigmoid(logits) > 0.5).long()
        self.val_iou.update(preds, masks.long())
        self.val_dice.update(preds, masks.long())
        
        self.log("val/loss", loss, on_step=False, on_epoch=True)
        self.log("val/iou", self.val_iou, on_step=False, on_epoch=True)
        self.log("val/dice", self.val_dice, on_step=False, on_epoch=True)
        
        return loss
    
    def configure_optimizers(self):
        import hydra
        optimizer = hydra.utils.instantiate(
            self.cfg.train.optimizer,
            params=self.parameters()
        )
        scheduler = hydra.utils.instantiate(
            self.cfg.train.scheduler,
            optimizer=optimizer
        )
        
        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "interval": "epoch",
                "frequency": 1
            }
        }

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def vis_dataloader_batch(cfg, train_loader, loggers, num_samples=4):
    """Visualize a batch from the dataloader."""
    log.info("Generating dataloader visualization...")
    
    # Get one batch
    imgs, masks = next(iter(train_loader))
    B = imgs.size(0)
    nrow = min(4, B) if B <= 8 else math.ceil(math.sqrt(B))
    
    # Save directory
    out_dir = Path(cfg.paths.run_root) / "image_logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Images grid
    img_grid = torchvision.utils.make_grid(imgs, nrow=nrow, padding=4)
    img_path = out_dir / "batch_visualization_image.png"
    plt.figure(figsize=(8, 8))
    plt.imshow(img_grid.permute(1, 2, 0).clamp(0, 1))
    plt.title("Batch Images")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(img_path)
    plt.close()
    
    # Masks grid
    if masks.ndim == 4 and masks.size(1) == 1:
        masks_vis = masks.expand(-1, 3, -1, -1)
    else:
        masks_vis = masks
    mask_grid = torchvision.utils.make_grid(masks_vis, nrow=nrow, padding=4)
    mask_path = out_dir / "batch_visualization_mask.png"
    plt.figure(figsize=(8, 8))
    plt.imshow(mask_grid.permute(1, 2, 0))
    plt.title("Batch Masks")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(mask_path)
    plt.close()
    
    log.info(f"Saved visualization to: {out_dir}")

def vis_augmentation_batch(train_loader, loggers, num_samples=4):
    """Visualize augmentation pipeline."""
    log.info("Generating augmentation visualization...")
    
    dataset = train_loader.dataset
    total = len(dataset)
    if total == 0:
        return
    
    cells = []
    for idx in torch.randperm(total)[:min(num_samples, total)].tolist():
        img_np = np.array(Image.open(dataset.images[idx]).convert("RGB"))
        mask_np = np.array(Image.open(dataset.masks[idx]).convert("L"))
        
        # Apply augmentation
        out = dataset.transform(image=img_np, mask=mask_np)
        aug_img = out["image"].float() / 255.0
        aug_mask = out["mask"].float() / 255.0
        
        if aug_mask.ndim == 2:
            aug_mask = aug_mask.unsqueeze(0)
        aug_mask = aug_mask.repeat(3, 1, 1)
        
        cells.extend([aug_img, aug_mask])
    
    # Create grid
    grid = make_grid(cells, nrow=2, padding=4)
    out_dir = Path(train_loader.dataset.cfg_aug).parent.parent / "image_logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "aug_visualization.png"
    save_image(grid, str(out_file))
    
    log.info(f"Saved augmentation visualization to: {out_file}")