# src/agir_cvtoolkit/pipelines/utils/preprocess_utils.py

"""
Preprocessing utilities for training data preparation.

Includes:
- Pad/grid-crop/resize for standardizing image sizes
- Train/val/test splitting
- Dataset statistics computation
"""

import json
import logging
import random
import shutil
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image

log = logging.getLogger(__name__)


# ============================================================================
# SEED MANAGEMENT
# ============================================================================

def set_seed(seed: int) -> None:
    """Set random seed for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)


# ============================================================================
# PAD / GRID-CROP / RESIZE
# ============================================================================

def _process_one_image(
    img_path: Path,
    mask_path: Path,
    out_images: Path,
    out_masks: Path,
    cfg: dict,
) -> None:
    """
    Standardize one image/mask pair to fixed size.
    
    - Pads if smaller than target size
    - Grid-crops if > threshold × target size
    - Resizes (preserving aspect ratio) otherwise
    
    Args:
        img_path: Path to source image
        mask_path: Path to corresponding mask
        out_images: Output directory for processed images
        out_masks: Output directory for processed masks
        cfg: Config dict with processing parameters
    """
    # Extract config
    target_h = int(cfg['size']['height'])
    target_w = int(cfg['size']['width'])
    stride = int(cfg['grid_crop'].get('stride', target_h))
    threshold = float(cfg['grid_crop']['threshold'])
    img_interp = getattr(Image, cfg['resize']['interpolation']['image'].upper())
    mask_interp = getattr(Image, cfg['resize']['interpolation']['mask'].upper())
    remove_src = bool(cfg.get('remove_src', False))
    ignore_empty = bool(cfg.get('ignore_empty_data', False))
    pad_fill = int(cfg['pad']['fill'])
    
    # Load images
    img = Image.open(img_path).convert("RGB")
    mask = Image.open(mask_path).convert("L")
    w, h = img.size
    
    # CASE 1: PAD if smaller than target
    if cfg['pad']['enabled'] and (w < target_w or h < target_h):
        img_out = Image.new(img.mode, (target_w, target_h), color=pad_fill)
        mask_out = Image.new(mask.mode, (target_w, target_h), color=pad_fill)
        img_out.paste(img, ((target_w - w) // 2, (target_h - h) // 2))
        mask_out.paste(mask, ((target_w - w) // 2, (target_h - h) // 2))
        
        # Skip if mask is empty and we're ignoring empty data
        if ignore_empty and mask_out.getextrema() == (pad_fill, pad_fill):
            if remove_src:
                img_path.unlink()
                mask_path.unlink()
            return
        
        img_out.save(out_images / img_path.name)
        mask_out.save(out_masks / mask_path.name)
        
        if remove_src:
            img_path.unlink()
            mask_path.unlink()
        return
    
    # CASE 2: GRID-CROP if significantly larger
    if cfg['grid_crop']['enabled'] and ((w >= threshold * target_w) or (h >= threshold * target_h)):
        # First, create a resized+padded "full" version
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img_res = img.resize((new_w, new_h), resample=img_interp)
        mask_res = mask.resize((new_w, new_h), resample=mask_interp)
        full_img = Image.new(img.mode, (target_w, target_h), color=pad_fill)
        full_mask = Image.new(mask.mode, (target_w, target_h), color=pad_fill)
        full_img.paste(img_res, ((target_w - new_w) // 2, (target_h - new_h) // 2))
        full_mask.paste(mask_res, ((target_w - new_w) // 2, (target_h - new_h) // 2))
        
        # Save the full resized version
        full_img.save(out_images / img_path.name)
        full_mask.save(out_masks / mask_path.name)
        
        # Compute tile positions
        x_starts = list(range(0, max(w - target_w + 1, 1), stride))
        y_starts = list(range(0, max(h - target_h + 1, 1), stride))
        if x_starts[-1] != max(w - target_w, 0):
            x_starts.append(max(w - target_w, 0))
        if y_starts[-1] != max(h - target_h, 0):
            y_starts.append(max(h - target_h, 0))
        
        # Generate tiles
        for top in y_starts:
            for left in x_starts:
                box = (left, top, left + target_w, top + target_h)
                tile_img = img.crop(box)
                tile_mask = mask.crop(box)
                
                # Pad partial tiles
                if tile_img.size != (target_w, target_h):
                    padded_img = Image.new(tile_img.mode, (target_w, target_h), color=pad_fill)
                    padded_mask = Image.new(tile_mask.mode, (target_w, target_h), color=pad_fill)
                    padded_img.paste(tile_img, ((target_w - tile_img.width) // 2, (target_h - tile_img.height) // 2))
                    padded_mask.paste(tile_mask, ((target_w - tile_mask.width) // 2, (target_h - tile_mask.height) // 2))
                    tile_img, tile_mask = padded_img, padded_mask
                
                # Skip empty tiles
                if ignore_empty and tile_mask.getextrema() == (pad_fill, pad_fill):
                    continue
                
                stem = f"{img_path.stem}_{left}_{top}"
                tile_img.save(out_images / f"{stem}{img_path.suffix}")
                tile_mask.save(out_masks / f"{stem}.png")
        
        if remove_src:
            img_path.unlink()
            mask_path.unlink()
        return
    
    # CASE 3: RESIZE if between target and threshold
    if cfg['resize']['enabled']:
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img_res = img.resize((new_w, new_h), resample=img_interp)
        mask_res = mask.resize((new_w, new_h), resample=mask_interp)
        img_out = Image.new(img.mode, (target_w, target_h), color=pad_fill)
        mask_out = Image.new(mask.mode, (target_w, target_h), color=pad_fill)
        img_out.paste(img_res, ((target_w - new_w) // 2, (target_h - new_h) // 2))
        mask_out.paste(mask_res, ((target_w - new_w) // 2, (target_h - new_h) // 2))
        
        # Skip if empty
        if ignore_empty and mask_out.getextrema() == (pad_fill, pad_fill):
            if remove_src:
                img_path.unlink()
                mask_path.unlink()
            return
        
        img_out.save(out_images / img_path.name)
        mask_out.save(out_masks / mask_path.name)
        
        if remove_src:
            img_path.unlink()
            mask_path.unlink()
        return
    
    # Should never reach here
    raise RuntimeError(
        f"Unexpected image size for {img_path.name}: {w}x{h} px "
        f"(target {target_w}x{target_h})"
    )


def pad_gridcrop_resize_preprocess(
    images_dir: Path,
    masks_dir: Path,
    out_images: Path,
    out_masks: Path,
    cfg: dict,
) -> None:
    """
    Standardize all images to fixed size using pad/grid-crop/resize.
    
    Args:
        images_dir: Input images directory
        masks_dir: Input masks directory
        out_images: Output images directory
        out_masks: Output masks directory
        cfg: Preprocessing config
    """
    log.info("Starting pad/grid-crop/resize preprocessing...")
    
    out_images.mkdir(parents=True, exist_ok=True)
    out_masks.mkdir(parents=True, exist_ok=True)
    
    # Find all image files
    img_paths = sorted(images_dir.glob("*.jpg")) + sorted(images_dir.glob("*.JPG"))
    
    use_cc = bool(cfg.get('use_concurrency', False))
    workers = int(cfg.get('num_workers', 1)) if use_cc else 1
    
    log.info(f"Processing {len(img_paths)} images...")
    log.info(f"Target size: {cfg['size']['height']}x{cfg['size']['width']}")
    log.info(f"Using {workers} workers" if use_cc else "Sequential processing")
    
    if use_cc and workers > 1:
        # Parallel processing
        with ProcessPoolExecutor(max_workers=workers) as exe:
            futures = {}
            for img_path in img_paths:
                # Find corresponding mask
                mask_path = masks_dir / f"{img_path.stem}.png"
                if not mask_path.exists():
                    log.warning(f"No mask found for {img_path.name}, skipping")
                    continue
                
                fut = exe.submit(_process_one_image, img_path, mask_path, out_images, out_masks, cfg)
                futures[fut] = img_path
            
            for fut in as_completed(futures):
                img_path = futures[fut]
                try:
                    fut.result()
                except Exception as e:
                    log.error(f"Failed to process {img_path.name}: {e}")
    else:
        # Sequential processing
        for img_path in img_paths:
            mask_path = masks_dir / f"{img_path.stem}.png"
            if not mask_path.exists():
                log.warning(f"No mask found for {img_path.name}, skipping")
                continue
            
            try:
                _process_one_image(img_path, mask_path, out_images, out_masks, cfg)
            except Exception as e:
                log.error(f"Failed to process {img_path.name}: {e}")
    
    log.info("Pad/grid-crop/resize complete")


# ============================================================================
# TRAIN/VAL/TEST SPLIT
# ============================================================================

def _copy_one_file(
    img_path: Path,
    mask_path: Path,
    img_dest: Path,
    mask_dest: Path,
    remove_src: bool,
) -> None:
    """Copy one image/mask pair to destination, optionally removing source."""
    shutil.copy2(img_path, img_dest / img_path.name)
    shutil.copy2(mask_path, mask_dest / mask_path.name)
    
    if remove_src:
        img_path.unlink()
        mask_path.unlink()


def train_val_test_split(
    images_dir: Path,
    masks_dir: Path,
    train_images: Path,
    train_masks: Path,
    val_images: Path,
    val_masks: Path,
    test_images: Path,
    test_masks: Path,
    cfg: dict,
    seed: int,
) -> Tuple[int, int, int]:
    """
    Split preprocessed data into train/val/test sets.
    
    Args:
        images_dir: Input preprocessed images
        masks_dir: Input preprocessed masks
        train_images: Output train images directory
        train_masks: Output train masks directory
        val_images: Output val images directory
        val_masks: Output val masks directory
        test_images: Output test images directory
        test_masks: Output test masks directory
        cfg: Split config
        seed: Random seed for reproducibility
    
    Returns:
        Tuple of (n_train, n_val, n_test)
    """
    log.info("Starting train/val/test split...")
    
    # Set seed for reproducible splits
    set_seed(seed)
    
    # Get all images
    all_imgs = sorted([p for p in images_dir.iterdir() if p.is_file()])
    random.shuffle(all_imgs)
    
    # Compute split counts
    total = len(all_imgs)
    n_train = int(cfg['train'] * total)
    n_val = int(cfg['val'] * total)
    # Rest goes to test
    
    splits = {
        'train': all_imgs[:n_train],
        'val': all_imgs[n_train:n_train + n_val],
        'test': all_imgs[n_train + n_val:],
    }
    
    log.info(f"Total images: {total}")
    log.info(f"Train: {len(splits['train'])} ({cfg['train']*100:.1f}%)")
    log.info(f"Val: {len(splits['val'])} ({cfg['val']*100:.1f}%)")
    log.info(f"Test: {len(splits['test'])} ({cfg['test']*100:.1f}%)")
    
    # Create output directories
    outs = {
        'train': (train_images, train_masks),
        'val': (val_images, val_masks),
        'test': (test_images, test_masks),
    }
    
    for img_d, mask_d in outs.values():
        img_d.mkdir(parents=True, exist_ok=True)
        mask_d.mkdir(parents=True, exist_ok=True)
    
    # Copy files
    remove_src = bool(cfg.get('remove_src', False))
    use_cc = bool(cfg.get('use_concurrency', False))
    workers = int(cfg.get('num_workers', 1)) if use_cc else 1
    
    if use_cc and workers > 1:
        # Multithreaded copy
        with ThreadPoolExecutor(max_workers=workers) as exe:
            for split_name, imgs in splits.items():
                img_dest, mask_dest = outs[split_name]
                for img_path in imgs:
                    mask_path = masks_dir / f"{img_path.stem}.png"
                    if not mask_path.exists():
                        log.warning(f"No mask for {img_path.stem}, skipping")
                        continue
                    exe.submit(_copy_one_file, img_path, mask_path, img_dest, mask_dest, remove_src)
    else:
        # Sequential copy
        for split_name, imgs in splits.items():
            img_dest, mask_dest = outs[split_name]
            for img_path in imgs:
                mask_path = masks_dir / f"{img_path.stem}.png"
                if not mask_path.exists():
                    log.warning(f"No mask for {img_path.stem}, skipping")
                    continue
                _copy_one_file(img_path, mask_path, img_dest, mask_dest, remove_src)
    
    log.info("Train/val/test split complete")
    
    return len(splits['train']), len(splits['val']), len(splits['test'])


# ============================================================================
# DATASET STATISTICS
# ============================================================================

def _stats_for_one_image(img_path: Path) -> Tuple[np.ndarray, np.ndarray, int]:
    """
    Compute per-image channel statistics.
    
    Args:
        img_path: Path to RGB image
    
    Returns:
        sum_c: Sum of pixel values per channel (3,)
        sum_sq: Sum of squared pixel values per channel (3,)
        pixels: Total number of pixels
    """
    img = Image.open(img_path).convert("RGB")
    arr = np.asarray(img, dtype=np.float64) / 255.0  # Normalize to [0, 1]
    
    h, w, _ = arr.shape
    pixels = h * w
    
    flat = arr.reshape(pixels, 3)
    sum_c = flat.sum(axis=0)
    sum_sq = (flat ** 2).sum(axis=0)
    
    return sum_c, sum_sq, pixels


def compute_rgb_mean_std(
    images_dir: Path,
    out_file: Path,
    cfg: dict,
) -> dict:
    """
    Compute dataset-wide RGB mean and standard deviation.
    
    Args:
        images_dir: Directory containing training images
        out_file: Output JSON file path
        cfg: Config for concurrency settings
    
    Returns:
        Dict with 'mean' and 'std' keys (lists of 3 floats each)
    """
    log.info("Computing RGB mean and std...")
    
    img_paths = sorted(images_dir.glob("*"))
    log.info(f"Processing {len(img_paths)} images for statistics...")
    
    use_cc = bool(cfg.get('use_concurrency', False))
    workers = int(cfg.get('num_workers', 1)) if use_cc else 1
    
    sum_c = np.zeros(3, dtype=np.float64)
    sum_sq = np.zeros(3, dtype=np.float64)
    total_pixels = 0
    
    if use_cc and workers > 1:
        # Parallel processing
        with ProcessPoolExecutor(max_workers=workers) as exe:
            futures = {exe.submit(_stats_for_one_image, p): p for p in img_paths}
            for fut in as_completed(futures):
                img_path = futures[fut]
                try:
                    sc, ssq, pix = fut.result()
                    sum_c += sc
                    sum_sq += ssq
                    total_pixels += pix
                except Exception as e:
                    log.error(f"Failed to compute stats for {img_path.name}: {e}")
    else:
        # Sequential processing
        for img_path in img_paths:
            try:
                sc, ssq, pix = _stats_for_one_image(img_path)
                sum_c += sc
                sum_sq += ssq
                total_pixels += pix
            except Exception as e:
                log.error(f"Failed to compute stats for {img_path.name}: {e}")
    
    # Compute mean and std
    mean = (sum_c / total_pixels).tolist()
    var = (sum_sq / total_pixels) - np.square(mean)
    std = np.sqrt(var).tolist()
    
    stats = {"mean": mean, "std": std}
    
    # Save to file
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, 'w') as f:
        json.dump(stats, f, indent=4)
    
    log.info(f"RGB statistics saved to: {out_file}")
    log.info(f"Mean: [{mean[0]:.6f}, {mean[1]:.6f}, {mean[2]:.6f}]")
    log.info(f"Std:  [{std[0]:.6f}, {std[1]:.6f}, {std[2]:.6f}]")
    
    return stats