#!/usr/bin/env python3
"""
Export resized originals and bbox overlays from a CSV.

Required CSV columns:
  - image_id
  - image_path            (relative path under a logical store)
  - ncsu_nfs              (logical store key; resolved via --root-map)
  - bbox_xywh             (string like "[x,y,w,h]" or list/tuple)

Outputs per image_id:
  <image_id>_original.jpg   (downscaled + optimized)
  <image_id>_bbox.jpg       (downscaled + optimized, red rectangles)

Example:
  python export_bbox_from_csv.py \
    --csv /path/to/rows.csv \
    --outdir ./exports \
    --root-map '{
      "longterm_images": "/mnt/research-projects/s/screberg/longterm_images",
      "longterm_images2": "/mnt/research-projects/s/screberg/longterm_images2",
      "GROW_DATA": "/mnt/research-projects/s/screberg/GROW_DATA"
    }' \
    --max-side 2200 \
    --line-width 8
"""

from __future__ import annotations

import argparse
import ast
import json
import numpy as np
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from PIL import Image, ImageDraw, ImageOps, ImageEnhance


class BBoxOverlayExporter:
    def __init__(self) -> None:
        """
        root_map: mapping from logical store (e.g., 'longterm_images')
                  to absolute filesystem root.
        """

    # ---------- utils ----------

    @staticmethod
    def _parse_bbox(v: Any) -> Tuple[int, int, int, int]:
        """Accept list/tuple or string '[x,y,w,h]'; return ints; (0,0,0,0) if bad."""
        try:
            if isinstance(v, (list, tuple)):
                x, y, w, h = v
            elif isinstance(v, str):
                x, y, w, h = ast.literal_eval(v)
            else:
                return (0, 0, 0, 0)
            return tuple(int(round(float(z))) for z in (x, y, w, h))
        except Exception:
            return (0, 0, 0, 0)

    def _resolve(self, store: Optional[str], rel: Optional[str]) -> Optional[Path]:
        """Resolve <store>/<relative> to an absolute path using root_map."""
        if not store or not rel:
            return None
        root = Path("/mnt/research-projects/s/screberg") / store
        if not root:
            raise ValueError(f"Unknown store: {store}")
        rel_norm = str(rel).lstrip("/").rstrip("/")
        return Path(root) / rel_norm

    @staticmethod
    def _resize_max(im: Image.Image, max_side: int) -> Image.Image:
        """Downscale preserving aspect ratio so max(width,height) <= max_side."""
        if max_side is None or max_side <= 0 or max(im.size) <= max_side:
            return im
        im = im.copy()
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        return im

    @staticmethod
    def _save_jpeg_optimized(
        im: Image.Image,
        out_path: Path,
        quality: int = 82,
        subsampling: str | int = "4:2:0",
        progressive: bool = True,
        optimize: bool = True,
        strip_exif: bool = True,
        strip_icc: bool = True,
    ) -> None:
        """
        Compact, good-looking JPEG save. Avoid passing None for exif/icc (Pillow quirk).
        """
        im = im.convert("RGB")
        im = ImageOps.exif_transpose(im)
        if strip_exif:
            im.info.pop("exif", None)
        if strip_icc:
            im.info.pop("icc_profile", None)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        im.save(
            out_path,
            format="JPEG",
            quality=quality,
            subsampling=subsampling,
            progressive=progressive,
            optimize=optimize,
        )

    def _colorize_mask(
        self, 
        mask_path: Path, 
        rgb_value: Any, 
        out_path: Path,
        brightness: float = 6.5
    ) -> None:
        """
        Colorize a grayscale mask using the provided RGB value and save as RGB.
        
        Args:
            mask_path: Path to the grayscale/binary mask image (nonzero = mask).
            rgb_value: list/tuple or string like "[0.3,0.5,0.2]" or "[76,142,34]".
                    Values in 0–1 will be scaled to 0–255.
            out_path: Output path for the colorized mask.
            brightness: Brightness enhancement factor (1.0 = no change, >1.0 = brighter)
        """
        if not mask_path.exists():
            raise FileNotFoundError(f"Mask not found: {mask_path}")
        
        # Load grayscale mask
        mask_img = Image.open(mask_path).convert("L")  # ensure 8-bit grayscale
        
        # Parse color safely
        try:
            if isinstance(rgb_value, str):
                rgb_value = ast.literal_eval(rgb_value)
            
            if isinstance(rgb_value, (list, tuple)) and len(rgb_value) == 3:
                # Check if values are normalized (0-1) or absolute (0-255)
                if all(0.0 <= float(v) <= 1.0 for v in rgb_value):
                    rgb = tuple(int(float(v) * 255) for v in rgb_value)
                else:
                    rgb = tuple(int(v) for v in rgb_value)
            else:
                print(f"Invalid RGB value format: {rgb_value}, using fallback")
                rgb = tuple(self.seg_cfg.output.get("colorize_fallback_rgb", [0, 255, 0]))
        
        except Exception as e:
            print(f"Error parsing RGB value: {e}, using fallback")
            rgb = tuple(self.seg_cfg.output.get("colorize_fallback_rgb", [0, 255, 0]))
        
        # Create colored and black images
        color_img = Image.new("RGB", mask_img.size, rgb)
        black_img = Image.new("RGB", mask_img.size, (0, 0, 0))
        
        # Where mask_img > 0, take color_img; else black_img
        mask_np = np.array(mask_img)
        mask_np = np.where(mask_np > 0, 255, 0).astype(np.uint8)
        mask_img = Image.fromarray(mask_np, mode="L")
        colorized = Image.composite(color_img, black_img, mask_img)
        
        # Brighten the result for better visualization
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(colorized)
            colorized = enhancer.enhance(brightness)
        
        # Save colorized mask
        out_path.parent.mkdir(parents=True, exist_ok=True)
        colorized.save(out_path)
        print(f"Saved colorized mask to: {out_path}")
    # ---------- core ----------


    def _draw_and_save(
        self,
        img_path: Path,
        mask_path: Optional[Path],
        boxes_xywh: List[Tuple[int, int, int, int]],
        out_original: Path,
        out_mask: Path,
        out_bbox: Path,
        max_side: int,
        line_width: int,
        rgb_value: Tuple[int, int, int],
        brightness: float = 6.5,

    ) -> None:
        # resized original
        im = Image.open(img_path).convert("RGB")
        im_small = self._resize_max(im, max_side=max_side)
        self._save_jpeg_optimized(im_small, out_original, quality=82, subsampling="4:2:0")

        # resized original mask (if provided)
        if mask_path and mask_path.exists():
            self._colorize_mask(mask_path, rgb_value, out_mask, brightness=brightness)
            
        # bbox overlay (draw at native res, then resize)
        im2 = Image.open(img_path).convert("RGB")
        draw = ImageDraw.Draw(im2)
        for (x, y, w, h) in boxes_xywh:
            if w > 0 and h > 0:
                draw.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=line_width)
        im2_small = self._resize_max(im2, max_side=max_side)
        self._save_jpeg_optimized(im2_small, out_bbox, quality=82, subsampling="4:2:0")

    def export_from_csv_rows(
        self,
        rows: Iterable[Dict[str, Any]],
        outdir: Path,
        max_side: int = 2200,
        line_width: int = 8,
        use_original_mask: bool = False,
        brightness: float = 6.5,
    ) -> None:
        """
        Groups rows by image_id, resolves original path, aggregates all bboxes,
        and writes exactly two files per image_id:
          <image_id>_original.jpg
          <image_id>_bbox.jpg
        """
        outdir.mkdir(parents=True, exist_ok=True)

        # group rows by image_id
        by_image: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            iid = str(r.get("image_id"))
            rgb_value_str = r.get("category_rgb", "[255, 0, 0]")
            by_image.setdefault(iid, []).append(r)

        mask_path: Optional[Path] = None
        rgb_value: Tuple[int, int, int] = (255, 0, 0)
        for image_id, group in by_image.items():
            sample = group[0]
            img_path = self._resolve(sample.get("ncsu_nfs"), sample.get("image_path"))
            if use_original_mask:
                mask_path = self._resolve(sample.get("ncsu_nfs"), sample.get("mask_path"))
                rgb_value = ast.literal_eval(rgb_value_str)
            if not img_path or not img_path.exists():
                print(f"[warn] missing image for image_id={image_id}: store={sample.get('ncsu_nfs')} path={sample.get('image_path')}")
                continue

            boxes = [self._parse_bbox(r.get("bbox_xywh")) for r in group]
            out_original = outdir / "images" / f"{image_id}_original.jpg"
            out_mask     = outdir / "colorized_masks" / f"{image_id}_original_mask.png"
            out_bbox     = outdir / "plots" / f"{image_id}_bbox.jpg"

            try:
                self._draw_and_save(
                    img_path=img_path,
                    mask_path=mask_path,
                    boxes_xywh=boxes,
                    out_original=out_original,
                    out_mask=out_mask,
                    out_bbox=out_bbox,
                    max_side=max_side,
                    line_width=line_width,
                    rgb_value=rgb_value,
                    brightness=brightness
                )
                out_meta = outdir / "plots" / f"{image_id}_metadata.txt"
                self._write_row_metadata(rows=group, out_meta=out_meta)
                self._write_row_to_csv(rows=group, out_csv=outdir / "plots" / f"{image_id}_metadata.csv")
                print(f"[ok] {image_id} -> {out_original.name}, {out_bbox.name} {', ' + out_mask.name if use_original_mask else ''}")
            except Exception as e:
                print(f"[err] failed on {image_id}: {e}")

    def _write_row_metadata(self, rows: List[Dict[str, Any]], out_meta: Path) -> None:
        """
        Write each column and its values for the provided rows to a text file.
        Each CSV row for the image_id is written as a separate section.
        """
        out_meta.parent.mkdir(parents=True, exist_ok=True)
        with out_meta.open("w", encoding="utf-8") as fh:
            for idx, r in enumerate(rows):
                fh.write(f"Row {idx}\n")
                for k, v in sorted(r.items()):
                    fh.write(f"{k}: {v}\n")
                fh.write("\n")
    def _write_row_to_csv(self, rows: List[Dict[str, Any]], out_csv: Path) -> None:
        """
        Write each column and its values for the provided rows to a csv file.
        Each CSV row for the image_id is written as a separate row.
        """
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        df.to_csv(out_csv, index=False)

# ---------- CLI ----------

def parse_args() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Resize originals and write bbox overlays from CSV.")
    p.add_argument("--csv", type=Path, required=True, help="Path to CSV (must contain image_id, image_path, ncsu_nfs, bbox_xywh)")
    p.add_argument("--outdir", type=Path, required=True, help="Output directory")
    p.add_argument("--max-side", type=int, default=2200, help="Downscale so longer side <= this (0 to disable)")
    p.add_argument("--line-width", type=int, default=8, help="BBox line width in pixels")
    # option to use original full mask if it exists
    p.add_argument("--use-original-mask", action="store_true", help="Use original full mask if it exists")
    p.add_argument("--brightness", type=float, default=6.5, help="Brightness factor for colorized masks (1.0 = no change)")
    # Optional: quick filter via pandas query
    p.add_argument("--query", type=str, default=None, help="Optional pandas query string to filter rows")
    return p


def main() -> None:
    args = parse_args().parse_args()
    df = pd.read_csv(args.csv)
    if args.query:
        try:
            df = df.query(args.query)
        except Exception as e:
            raise SystemExit(f"Bad --query expression: {e}")

    required = {"image_id", "image_path", "ncsu_nfs", "bbox_xywh"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"CSV missing required columns: {', '.join(sorted(missing))}")

    rows = df.to_dict(orient="records")
    exporter = BBoxOverlayExporter()
    exporter.export_from_csv_rows(
        rows=rows,
        outdir=args.outdir,
        max_side=args.max_side,
        line_width=args.line_width,
        use_original_mask=args.use_original_mask,
        brightness=args.brightness,
    )


if __name__ == "__main__":
    main()
