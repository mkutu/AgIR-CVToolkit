"""
Segmentation inference utilities.

Modular components for model loading, tiled inference, post-processing, and visualization.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import matplotlib.pyplot as plt
import numpy as np
import torch
from PIL import Image
from omegaconf import DictConfig

import GPUtil    
import segmentation_models_pytorch as smp


# ======================= GPU Utilities =======================

def select_available_gpus(
    max_gpus: int = 1,
    exclude_ids: List[int] = None,
    verbose: bool = True,
) -> List[int]:
    """Select available GPU IDs, excluding specified ones."""
    
    exclude_ids = exclude_ids or []
    available = GPUtil.getAvailable(
        order="memory",
        limit=8,
        maxLoad=0.5,
        maxMemory=0.5,
    )
    filtered = [gpu for gpu in available if gpu not in exclude_ids]
    
    if not filtered:
        raise RuntimeError(f"No suitable GPUs available after excluding: {exclude_ids}")
    
    chosen = filtered[:max_gpus]
    if verbose:
        print(f"Selected GPU IDs: {chosen}")
    return chosen


# ======================= Model Components =======================

class SegModel:
    """
    Wrapper for segmentation models with preprocessing.
    
    Supports SMP models (Unet, DeepLabV3+, Segformer).
    """
    
    def __init__(
        self,
        arch: str,
        encoder_name: str,
        in_channels: int,
        num_classes: int,
        encoder_weights: Optional[str] = "imagenet",
        mean: Optional[List[float]] = None,
        std: Optional[List[float]] = None,
    ):
        
        self.arch = arch.lower()
        self.encoder_name = encoder_name
        self.in_channels = in_channels
        self.num_classes = num_classes
        self.encoder_weights = encoder_weights
        
        # Normalization params
        self.mean = np.array(mean or [0.485, 0.456, 0.406], dtype=np.float32)
        self.std = np.array(std or [0.229, 0.224, 0.225], dtype=np.float32)
        
        # Build model
        self.model = self._build_model()
        self.model.eval()
    
    def _build_model(self) -> torch.nn.Module:
        """Build SMP model."""
        if self.arch == "unet":
            return smp.Unet(
                encoder_name=self.encoder_name,
                in_channels=self.in_channels,
                classes=self.num_classes,
                encoder_weights=self.encoder_weights,
            )
        elif self.arch == "deeplabv3plus":
            return smp.DeepLabV3Plus(
                encoder_name=self.encoder_name,
                in_channels=self.in_channels,
                classes=self.num_classes,
                encoder_weights=self.encoder_weights,
            )
        elif self.arch == "segformer":
            return smp.Segformer(
                encoder_name=self.encoder_name,
                in_channels=self.in_channels,
                classes=self.num_classes,
            )
        else:
            raise ValueError(f"Unsupported architecture: {self.arch}")
    
    def load_checkpoint(
        self,
        ckpt_path: Path,
        device: torch.device,
        strict: bool = True,
    ) -> None:
        """Load weights from Lightning checkpoint."""
        ckpt = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
        state = ckpt.get("state_dict", ckpt)
        
        # Strip "model." prefix if present
        new_state = {}
        for k, v in state.items():
            new_k = k.replace("model.", "") if k.startswith("model.") else k
            new_state[new_k] = v
        
        self.model.load_state_dict(new_state, strict=strict)
        self.model.to(device)
        self.model.eval()
    
    def preprocess(self, img_rgb_u8: np.ndarray) -> np.ndarray:
        """
        Convert RGB uint8 -> normalized float32 for model input.
        
        Returns: HxWx3 float32 array
        """
        x = img_rgb_u8.astype(np.float32) / 255.0  # to [0,1]
        x = (x - self.mean) / self.std
        return x
    
    @torch.no_grad()
    def predict(
        self,
        img_rgb_u8: np.ndarray,
        device: torch.device,
        pad_divisor: int = 32,
    ) -> np.ndarray:
        """
        Run inference on a single image.
        
        Args:
            img_rgb_u8: HxWx3 uint8 RGB image
            device: torch device
            pad_divisor: pad to multiple of this (for encoder stride)
        
        Returns:
            - Binary: HxW uint8 mask (0 or 255)
            - Multi-class: HxW int32 class indices
        """
        # Preprocess
        x = self.preprocess(img_rgb_u8)
        
        # Pad to divisor
        x, pad_hw = pad_to_divisible(x, pad_divisor)
        
        # Convert to tensor
        x_t = torch.from_numpy(x.transpose(2, 0, 1)).unsqueeze(0).float().to(device)
        
        # Forward pass
        logits = self.model(x_t)
        if isinstance(logits, (list, tuple)):
            logits = logits[0]
        logits = logits.float()
        
        # Convert to predictions
        if self.num_classes == 1:
            # Binary segmentation
            prob = torch.sigmoid(logits)[0, 0].cpu().numpy()
            prob = unpad(prob, pad_hw)
            return prob.astype(np.float32)
        else:
            # Multi-class segmentation
            prob = torch.softmax(logits, dim=1)[0].cpu().numpy()  # CxHxW
            prob = prob.transpose(1, 2, 0)  # HxWxC
            prob = unpad(prob, pad_hw)
            return prob.astype(np.float32)


# ======================= Tiled Inference =======================

class TiledInference:
    """
    Tiled inference with weighted stitching for large images.
    """
    
    def __init__(
        self,
        tile_h: int = 1024,
        tile_w: int = 1024,
        overlap: float = 0.5,
        pad_mode: str = "reflect",
        pad_divisor: int = 32,
    ):
        self.tile_h = tile_h
        self.tile_w = tile_w
        self.overlap = overlap
        self.pad_mode = pad_mode
        self.pad_divisor = pad_divisor
        
        # Precompute Hann window for blending
        self.window = self._hann_window(tile_h, tile_w)
    
    def _hann_window(self, h: int, w: int, eps: float = 1e-6) -> np.ndarray:
        """Create 2D Hann window for weighted blending."""
        wy = np.hanning(h).astype(np.float32)
        wx = np.hanning(w).astype(np.float32)
        win = wy[:, None] * wx[None, :]
        return win + eps  # avoid zeros at edges
    
    def make_tiles(
        self,
        img_rgb_u8: np.ndarray,
    ) -> Tuple[List[np.ndarray], List[Tuple[int, int, int, int]], Tuple[int, int]]:
        """
        Create overlapping tiles from image.
        
        Returns:
            tiles: list of HxWx3 uint8 tiles
            coords: list of (y0, y1, x0, x1) in padded coordinates
            padded_hw: (H_padded, W_padded)
        """
        H, W = img_rgb_u8.shape[:2]
        
        # Compute stride
        sy = max(1, int(self.tile_h * (1.0 - self.overlap)))
        sx = max(1, int(self.tile_w * (1.0 - self.overlap)))
        
        # Compute padding
        pad_bottom = (-(H - self.tile_h) % sy) if H > self.tile_h else (self.tile_h - H)
        pad_right = (-(W - self.tile_w) % sx) if W > self.tile_w else (self.tile_w - W)
        
        # Apply padding
        border = cv2.BORDER_REFLECT_101 if self.pad_mode == "reflect" else cv2.BORDER_CONSTANT
        padded = cv2.copyMakeBorder(img_rgb_u8, 0, pad_bottom, 0, pad_right, border, value=[0, 0, 0])
        Hp, Wp = padded.shape[:2]
        
        # Extract tiles
        tiles, coords = [], []
        for y0 in range(0, Hp - self.tile_h + 1, sy):
            for x0 in range(0, Wp - self.tile_w + 1, sx):
                y1, x1 = y0 + self.tile_h, x0 + self.tile_w
                tiles.append(padded[y0:y1, x0:x1])
                coords.append((y0, y1, x0, x1))
        
        return tiles, coords, (Hp, Wp)
    
    def stitch_binary(
        self,
        prob_tiles: List[np.ndarray],
        coords: List[Tuple[int, int, int, int]],
        padded_hw: Tuple[int, int],
        threshold: float = 0.5,
    ) -> np.ndarray:
        """
        Stitch probability tiles with weighted blending.
        
        Returns: HxW uint8 binary mask (0 or 255)
        """
        Hp, Wp = padded_hw
        acc = np.zeros((Hp, Wp), np.float32)
        wacc = np.zeros((Hp, Wp), np.float32)
        
        for prob, (y0, y1, x0, x1) in zip(prob_tiles, coords):
            # Handle NaNs
            if np.isnan(prob).any():
                prob = np.nan_to_num(prob, nan=0.0)
            
            # Ensure shape match
            if prob.shape[:2] != (y1 - y0, x1 - x0):
                prob = cv2.resize(prob, (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR)
            
            # Weighted accumulation
            acc[y0:y1, x0:x1] += prob * self.window
            wacc[y0:y1, x0:x1] += self.window
        
        # Average and threshold
        wacc[wacc == 0] = 1.0
        avg = acc / wacc
        return ((avg >= threshold) * 255).astype(np.uint8)
    
    def predict(
        self,
        img_rgb_u8: np.ndarray,
        model: SegModel,
        device: torch.device,
        threshold: float = 0.5,
    ) -> np.ndarray:
        """
        Run tiled inference on large image.
        
        Returns: HxW uint8 binary mask (0 or 255)
        """
        # Create tiles
        tiles, coords, padded_hw = self.make_tiles(img_rgb_u8)
        
        # Predict on each tile
        prob_tiles = []
        for tile in tiles:
            prob = model.predict(tile, device, self.pad_divisor)
            prob_tiles.append(prob)
        
        # Stitch
        full_padded = self.stitch_binary(prob_tiles, coords, padded_hw, threshold)
        
        # Crop to original size
        H, W = img_rgb_u8.shape[:2]
        return full_padded[:H, :W]


# ======================= Post-Processing =======================

class SegPostProcessor:
    """Post-processing for segmentation masks."""
    
    def __init__(
        self,
        threshold: float = 0.5,
        min_area: int = 0,
        edge_occupancy_threshold: Optional[float] = None,
    ):
        self.threshold = threshold
        self.min_area = min_area
        self.edge_occupancy_threshold = edge_occupancy_threshold
    
    def compute_edge_occupancy(self, mask_u8: np.ndarray) -> float:
        """
        Fraction of the image's 1-pixel border occupied by the mask (0..1).
        """
        m = mask_u8 > 0
        if m.size == 0 or not m.any():
            return 0.0
        
        h, w = m.shape[:2]
        
        # Border sums
        top = m[0, :].sum(dtype=np.int64)
        bottom = m[-1, :].sum(dtype=np.int64) if h > 1 else 0
        left = m[:, 0].sum(dtype=np.int64)
        right = m[:, -1].sum(dtype=np.int64) if w > 1 else 0
        
        contact = top + bottom + left + right
        
        # Remove corners counted twice
        if h > 1 and w > 1:
            contact -= (int(m[0, 0]) + int(m[0, -1]) + int(m[-1, 0]) + int(m[-1, -1]))
        
        # Border length
        if h > 1 and w > 1:
            border_len = 2 * (h + w) - 4
        else:
            border_len = h * w
        
        if border_len <= 0:
            return 0.0
        
        return float(contact / border_len)
    
    def remove_small_components(self, mask_u8: np.ndarray) -> np.ndarray:
        """Remove connected components smaller than min_area."""
        if self.min_area <= 0:
            return mask_u8
        
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask_u8, connectivity=8)
        
        # Keep only large components
        mask_clean = np.zeros_like(mask_u8)
        for i in range(1, num_labels):  # skip background (0)
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= self.min_area:
                mask_clean[labels == i] = 255
        
        return mask_clean
    
    def remap_classes(self, mask_u8: np.ndarray, class_id: int) -> np.ndarray:
        """Remap binary mask to class_id."""
        if class_id <= 0:
            return mask_u8
        remapped = np.zeros_like(mask_u8, dtype=np.uint8)
        remapped[mask_u8 > 0] = class_id
        return remapped

    def process(self, mask_u8: np.ndarray, class_id: int) -> Tuple[np.ndarray, float]:
        """
        Apply post-processing to mask.
        
        Returns:
            processed_mask: HxW uint8 (0 or 255)
            edge_occupancy: float in [0, 1]
        """
        # Remove small components
        # mask_u8 = self.remove_small_components(mask_u8)
        
        # Compute edge occupancy
        edge_occupancy = self.compute_edge_occupancy(mask_u8)

        # Remap classes if needed
        mask_u8 = self.remap_classes(mask_u8, class_id)
        
        return mask_u8, edge_occupancy


# ======================= Visualization =======================

class SegVisualizer:
    """Visualization utilities for segmentation results."""
    
    def __init__(self, overlay_alpha: float = 0.5):
        self.overlay_alpha = overlay_alpha
    
    def make_overlay(
        self,
        img_rgb_u8: np.ndarray,
        mask_u8: np.ndarray,
        color: Tuple[int, int, int] = (255, 0, 0),
    ) -> np.ndarray:
        """Create overlay of mask on image."""
        overlay = img_rgb_u8.copy()
        fg = mask_u8 > 0
        
        color_arr = np.zeros_like(img_rgb_u8)
        color_arr[..., 0] = color[0]
        color_arr[..., 1] = color[1]
        color_arr[..., 2] = color[2]
        
        overlay[fg] = (
            self.overlay_alpha * color_arr[fg] + 
            (1 - self.overlay_alpha) * img_rgb_u8[fg]
        ).astype(np.uint8)
        
        return overlay
    
    def plot_quad(
        self,
        record: Dict,
        img_rgb_u8: np.ndarray,
        pred_mask: np.ndarray,
        out_path: Path,
        gt_mask: Optional[np.ndarray] = None,
        edge_occupancy: Optional[float] = None,
    ) -> None:
        """Create 4-panel visualization plot."""
        overlay = self.make_overlay(img_rgb_u8, pred_mask)
        
        n_panels = 3 if gt_mask is None else 4
        fig, axes = plt.subplots(1, n_panels, figsize=(4 * n_panels, 4))
        
        if n_panels == 3:
            axes = [axes[0], axes[1], axes[2]]
        
        for ax in axes:
            ax.axis("off")
        
        # Panel 1: Original image
        axes[0].imshow(img_rgb_u8)
        axes[0].set_title("Original Image")
        
        # Panel 2: GT mask (if available)
        if gt_mask is not None:
            axes[1].imshow(gt_mask, cmap="gray", vmin=0, vmax=255)
            axes[1].set_title("Ground Truth")
            panel_idx = 2
        else:
            panel_idx = 1
        
        # Panel: Predicted mask
        axes[panel_idx].imshow(pred_mask, cmap="gray", vmin=0, vmax=255)
        axes[panel_idx].set_title("Predicted Mask")
        
        # Panel: Overlay
        axes[panel_idx + 1].imshow(overlay)
        axes[panel_idx + 1].set_title("Overlay")
        
        # Build title
        title_parts = []
        
        if record.get("category_common_name") or record.get("common_name"):
            name = record.get("category_common_name") or record.get("common_name")
            title_parts.append(f"Species: {name}")
        
        if record.get("image_id"):
            title_parts.append(f"Image ID: {record['image_id']}")
        
        if record.get("cutout_id"):
            title_parts.append(f"Cutout ID: {record['cutout_id']}\n")
        
        if record.get("area_bin"):
            title_parts.append(f"Area Bin: {record['area_bin']} cm²")
        
        if edge_occupancy is not None:
            title_parts.append(f"Edge Occupancy: {edge_occupancy:.4f}")
        
        if title_parts:
            fig.suptitle(" | ".join(title_parts), fontsize=10)
        
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(out_path, bbox_inches="tight", dpi=150)
        plt.close(fig)


# ======================= Image Loading =======================


def load_image_from_record(
    record: Dict, 
    cfg: DictConfig,
    image_mode: str = "cutout"
) -> Optional[np.ndarray]:
    """
    Load RGB image from a database record.
    
    Handles both SemiF and Field database records with two modes:
    - cutout: Load cropout or apply bbox cropping (default behavior)
    - full_image: Always load the full image, ignore bbox and cropout
    
    Args:
        record: Database record with image paths
        cfg: Hydra config
        image_mode: "cutout" or "full_image"
    
    Returns:
        RGB numpy array (H, W, 3) as uint8, or None on failure
    """
    img_path = None
    use_cropout = False
    
    # For full_image mode, skip cropout/bbox logic entirely
    if image_mode == "full_image":
        # SemiF: use image_path
        if "image_path" in record and record.get("image_path"):
            if record["image_path"].lower() not in ("none", "null", ""):
                root = Path(cfg.io.semif_storage_dir)
                img_root = record.get("ncsu_nfs", "")
                img_path = root / img_root / record["image_path"]
        
        # Field: use developed_image_path
        elif "developed_image_path" in record and record.get("developed_image_path"):
            root = Path(cfg.io.field_storage_dir)
            img_path = root / record["developed_image_path"]
        
        if img_path is None or not img_path.exists():
            return None
        
        # Load full image without any cropping
        img = Image.open(img_path).convert("RGB")
        img_rgb_u8 = np.array(img, dtype=np.uint8)
        return img_rgb_u8
    
    # Original cutout mode behavior
    # SemiF paths - try cropout first
    if "cropout_path" in record and record.get("cropout_path"):
        if record["cropout_path"].lower() not in ("none", "null", ""):
            root = Path(cfg.io.semif_storage_dir)
            cutout_root = record.get("cutout_ncsu_nfs", "")
            img_path = root / cutout_root / record["cropout_path"]
            use_cropout = True

    elif "image_path" in record and record.get("image_path"):
        if record["image_path"].lower() not in ("none", "null", ""):
            root = Path(cfg.io.semif_storage_dir)
            img_root = record.get("ncsu_nfs", "")
            img_path = root / img_root / record["image_path"]
            use_cropout = False
    
    # Field paths
    elif "developed_image_path" in record and record.get("developed_image_path"):
        root = Path(cfg.io.field_storage_dir)
        img_path = root / record["developed_image_path"]
        use_cropout = False
    
    if img_path is None or not img_path.exists():
        return None
    
    # Load image
    img = Image.open(img_path).convert("RGB")
    img_rgb_u8 = np.array(img, dtype=np.uint8)
    
    # Apply bbox crop if needed (only in cutout mode)
    if not use_cropout:
        if "bbox_xywh" in record and record.get("bbox_xywh"):
            try:
                bbox = ast.literal_eval(str(record["bbox_xywh"]))
                x, y, w, h = [int(v) for v in bbox]
                x, y = max(0, x), max(0, y)
                img_rgb_u8 = img_rgb_u8[y:y+h, x:x+w]
            except:
                pass  # Skip cropping on error
        else:
            return None
    
    return img_rgb_u8

# ======================= Array Utilities =======================

def pad_to_divisible(
    img: np.ndarray,
    div: int,
) -> Tuple[np.ndarray, Tuple[int, int]]:
    """
    Pad image to be divisible by div.
    
    Returns:
        padded_img: padded array
        pad_hw: (pad_height, pad_width)
    """
    h, w = img.shape[:2]
    nh = ((h + div - 1) // div) * div
    nw = ((w + div - 1) // div) * div
    ph, pw = nh - h, nw - w
    
    if ph == 0 and pw == 0:
        return img, (0, 0)
    
    if img.ndim == 3:
        pad_spec = ((0, ph), (0, pw), (0, 0))
    else:
        pad_spec = ((0, ph), (0, pw))
    
    padded = np.pad(img, pad_spec, mode="constant", constant_values=0)
    return padded, (ph, pw)


def unpad(arr: np.ndarray, pad_hw: Tuple[int, int]) -> np.ndarray:
    """Remove padding from array."""
    ph, pw = pad_hw
    if ph == 0 and pw == 0:
        return arr
    
    if arr.ndim == 3:
        return arr[:-ph or None, :-pw or None, :]
    return arr[:-ph or None, :-pw or None]