#!/usr/bin/env python3
"""
Export original image, bbox overlay for a single image, and (optionally) a cutout + mask,
pulling rows from your AgIR SQLite DB via AgirDB.

Example:
  python extract_visuals_from_db.py \
    --db-path /home/mkutuga/SemiF-DB/AgIR_DB_v1_0_202510.db \
    --table semif \
    --image-id MD_1667496966 \
    --cutout-id MD_1667496966_000001 \
    --base-name barley \
    --outdir ./exports \
    --root-map '{"longterm_images": "/mnt/research-projects/r/raatwell/longterm_images",
                 "longterm_images2": "/mnt/research-projects/r/raatwell/longterm_images2",
                 "GROW_DATA": "/mnt/GROW_DATA"}' \
    --state NC \
    --limit 100

If --base-name is omitted, the exporter will attempt to use category_common_name, else image_id.
"""

from __future__ import annotations

import argparse
import ast
from pprint import pprint
import json
import sqlite3
import pandas as pd

from dataclasses import dataclass
import random
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Any

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

# Import your DB API
from agir_cvtoolkit.core.db import AgirDB  # noqa: F401

# ----------------------------- Data Model ------------------------------------

@dataclass
class Record:
    image_id: str
    bbox_xywh: Tuple[int, int, int, int]
    image_path: Optional[str]
    ncsu_nfs: Optional[str]
    mask_path: Optional[str] = None

    cutout_id: Optional[str] = None
    cutout_path: Optional[str] = None
    cropout_path: Optional[str] = None
    cutout_mask_path: Optional[str] = None
    cutout_ncsu_nfs: Optional[str] = None

    category_common_name: Optional[str] = None


# ----------------------------- Core Extractor --------------------------------

class VisualExtractorDB:
    def __init__(self, root_map: Dict[str, Path]) -> None:
        self.root_map = root_map #{k: Path(v) for k, v in root_map.items()}

    # ---- Adapters ----
    @staticmethod
    def _parse_bbox(v: Any) -> Tuple[int, int, int, int]:
        """
        Accepts a list/tuple or a string like '[x, y, w, h]'.
        Returns a 4-tuple of ints; (0,0,0,0) if unparsable.
        """
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
        if not store or not rel:
            return None
        root = self.root_map.get(store)
        if not root:
            raise KeyError(f"Missing root for store '{store}'. Available: {list(self.root_map)}")
        return Path(root) / rel
    
    def _resize_max(self, im: Image.Image, max_side: int) -> Image.Image:
        """
        Downscale image in-place preserving aspect ratio so that
        max(width, height) == max_side (or smaller if already small).
        """
        if max(im.size) <= max_side:
            return im
        im = im.copy()
        # thumbnail() keeps aspect and is fast; uses antialiasing
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        return im

    def _save_jpeg_optimized(
        self,
        im: Image.Image,
        out_path: Path,
        quality: int = 82,
        subsampling: str | int = "4:2:0",
        progressive: bool = True,
        optimize: bool = True,
        strip_exif: bool = True,
        strip_icc: bool = True,
    ) -> None:
        im = im.convert("RGB")
        im = ImageOps.exif_transpose(im)  # apply orientation

        # Strip metadata from the in-memory image so save() won't try to reuse it
        if strip_exif:
            im.info.pop("exif", None)
        if strip_icc:
            im.info.pop("icc_profile", None)

        save_kwargs = {
            "format": "JPEG",
            "quality": quality,
            "subsampling": subsampling,   # e.g. "4:2:0" or 2
            "progressive": progressive,
            "optimize": optimize,
        }
        # DO NOT pass exif/icc_profile at all when stripping; Pillow chokes on None
        im.save(out_path, **save_kwargs)

    def _colorize_mask(self, mask_path: Path, rgb_value: Any, out_path: Path) -> None:
        """
        Colorize a grayscale mask using the provided RGB value and save as RGB.

        Args:
            mask_path: Path to the grayscale/binary mask image (nonzero = mask).
            rgb_value: list/tuple or string like "[0.3,0.5,0.2]" or "[76,142,34]".
                    Values in 0–1 will be scaled to 0–255.
            out_path:  Output path for the colorized mask.
        """
        if not mask_path.exists():
            raise FileNotFoundError(f"Mask not found: {mask_path}")

        mask_img = Image.open(mask_path).convert("L")  # ensure 8-bit grayscale

        # Parse color safely
        try:
            if isinstance(rgb_value, str):
                rgb_value = ast.literal_eval(rgb_value)
            if isinstance(rgb_value, (list, tuple)) and len(rgb_value) == 3:
                if all(0.0 <= float(v) <= 1.0 for v in rgb_value):
                    rgb = tuple(int(float(v) * 255) for v in rgb_value)
                else:
                    rgb = tuple(int(v) for v in rgb_value)
            else:
                rgb = (0, 255, 0)  # fallback
        except Exception:
            rgb = (0, 255, 0)

        color_img = Image.new("RGB", mask_img.size, rgb)
        black_img = Image.new("RGB", mask_img.size, (0, 0, 0))

        # Where mask_img > 0, take color_img; else black_img
        colorized = Image.composite(color_img, black_img, mask_img)

        # --- Brighten the result for better viz ---
        
        enhancer = ImageEnhance.Brightness(colorized)
        colorized = enhancer.enhance(6.5)  # tweak factor as needed

        colorized.save(out_path)

    def _make_cutout_transparent(self, cutout_path: Path, out_path: Path, threshold: int = 5) -> None:
        """
        Convert a cutout image with black background to RGBA and make black pixels transparent.

        Args:
            cutout_path:  Path to the RGB cutout image.
            out_path:     Path to save the RGBA image with transparency.
            threshold:    Intensity threshold for 'black' (0–255); below this = transparent.
        """
        if not cutout_path.exists():
            raise FileNotFoundError(f"Cutout not found: {cutout_path}")

        img = Image.open(cutout_path).convert("RGBA")
        datas = img.getdata()
        new_data = []

        for item in datas:
            # item = (R, G, B, A)
            if item[0] < threshold and item[1] < threshold and item[2] < threshold:
                # make black transparent
                new_data.append((0, 0, 0, 0))
            else:
                new_data.append(item)

        img.putdata(new_data)
        img.save(out_path)

    def _write_metadata_file(self, record: dict, outdir: Path, base_name: str) -> Path:
        """
        Write all metadata for a given record (e.g., cutout) to a text file.

        Args:
            record: dict of the row or record for the target cutout_id.
            outdir: directory where the images were saved.
            base_name: base filename prefix (e.g., 'barley').
        """
        out_path = outdir / f"{base_name}_metadata.txt"

        # Format each key/value pair
        lines = []
        for k, v in record.items():
            if isinstance(v, (list, dict)):
                v = json.dumps(v, indent=2)
            lines.append(f"{k}: {v}")

        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path

    # ---- Public API ----
    def export_assets(
        self,
        rows: Iterable[Any],
        outdir: Path,
        line_width: int = 4,
        save_image: bool = True,
        save_cutout: bool = True,
        save_mask: bool = True,
        save_bbox: bool = True,
        save_metadata: bool = True,
    ) -> Dict[str, Optional[Path]]:
        """
        For a given image_id across an iterable of DB rows, export:
          - <base>_original.jpg
          - <base>_bbox.jpg  (all bboxes for this image)
          - <base>_cutout.png (if a matching cutout_id was given and found)
          - <base>_mask.png   (per-cutout mask; fallback to full-image mask if present)
        """
        bbox_out: Optional[Path] = None
        original_out: Optional[Path] = None
        cutout_out: Optional[Path] = None
        mask_out: Optional[Path] = None
        if not rows:
            raise ValueError(f"No rows found for image_id='{image_id}' in provided record set")

        # Get a random row to extract image_id, cutout_id, base_name
        # Get the row with the largest estimated_bbox_area_cm2
        sample_row = max(rows, key=lambda r: r.get("estimated_bbox_area_cm2", 0))

        recs = [r for r in rows if r["image_id"] == sample_row["image_id"]]

        image_id = sample_row["image_id"]
        cutout_id = sample_row.get("cutout_id", None)
        base_name = sample_row.get("category_common_name", None)

        # Resolve the original image using the first record
        img_path = self._resolve(sample_row["ncsu_nfs"], sample_row["image_path"])

        if save_image:
            if img_path and img_path.exists():
                # Save original (downscale + optimized JPEG)
                original_out = outdir / f"{base_name}_original.jpg"
                orig_img = Image.open(img_path).convert("RGB")
                orig_img = self._resize_max(orig_img, max_side=2400)   # tweak: 1600–3000 is a good range
                self._save_jpeg_optimized(orig_img, original_out, quality=82, subsampling="4:2:0")

            else:
                raise FileNotFoundError(f"Original image not found: store={sample_row['ncsu_nfs']} path={sample_row['image_path']}")
            
        # Draw all bboxes
        if save_bbox:
            if img_path and img_path.exists():
                bbox_out = outdir / f"{base_name}_bbox.jpg"
                boxes = [self._parse_bbox(r.get("bbox_xywh")) for r in recs]
                self._draw_bboxes(img_path, boxes, bbox_out, line_width=line_width)



        if save_cutout:
            cut_nfs = sample_row['cutout_ncsu_nfs']
            # remove any leading/trailing slashes
            cutout_rel = sample_row["cutout_path"].lstrip("/").rstrip("/")
            cutout_path = Path(self.root_map[cut_nfs]) / cutout_rel
            if cutout_path and cutout_path.exists():
                cutout_out = outdir / f"{base_name}_cutout.png"
                self._make_cutout_transparent(cutout_path, cutout_out)
            else:
                print(f"[warn] Cutout not found for cutout_id={cutout_id} (store={cut_nfs}, path={cutout_rel})")
        
        if save_mask:
            # mask (prefer per-cutout)
            dev_nfs = sample_row["ncsu_nfs"]
            mask_rel = sample_row["mask_path"]
            mask_path = self._resolve(dev_nfs, mask_rel) if mask_rel else None
            if mask_path and mask_path.exists():
                mask_out = outdir / f"{base_name}_mask.png"
                rgb_value = sample_row.get("rgb") or sample_row.get("category_rgb") or (0, 255, 0)
                self._colorize_mask(mask_path, rgb_value, mask_out)
            else:
                print(f"[warn] Mask not found for cutout_id={cutout_id}")

        if save_metadata:
            self._write_metadata_file(sample_row, outdir, base_name)

        return {"original": original_out, "bbox": bbox_out, "cutout": cutout_out, "mask": mask_out}

    # ---- Helpers ----
    def _draw_bboxes(
        self,
        img_path: Path,
        boxes_xywh: List[Tuple[int, int, int, int]],
        out_path: Path,
        line_width: int = 4,
    ) -> None:
        im = Image.open(img_path).convert("RGB")
        draw = ImageDraw.Draw(im)
        for (x, y, w, h) in boxes_xywh:
            if w <= 0 or h <= 0:
                continue
            draw.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=line_width)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        
        bbox_img = self._resize_max(im, max_side=2400)
        self._save_jpeg_optimized(bbox_img, out_path, quality=82, subsampling="4:2:0")
        # im.save(out_path, quality=95)


def fetch_filtered_images(
        db_path: str, 
        table: str, 
        common_name: str = 'Palmer amaranth', 
        area_bin: str = '500-1000') -> List[Dict[str, Any]]:
    
    conn = sqlite3.connect(db_path)

    query = f"""
        SELECT t1.*
        FROM {table} t1
        WHERE t1.image_id IN (
            SELECT DISTINCT image_id
            FROM {table}
            WHERE category_common_name = ? 
            AND estimated_area_bin = ?
        )
        """

    # Execute query
    results = pd.read_sql_query(
        query, 
        conn, 
        params=(common_name, area_bin)  # Your filter values
    )

    print(f"Retrieved {len(results)} total records")
    return results.to_dict(orient='records')

# ----------------------------- Query + CLI -----------------------------------

def main() -> None:
    root_map = {
        "longterm_images": "/mnt/research-projects/s/screberg/longterm_images",
        "longterm_images2": "/mnt/research-projects/s/screberg/longterm_images2",
        "GROW_DATA": "/mnt/research-projects/s/screberg/GROW_DATA"
    }

    line_width = 16
    output_dir = Path("./scripts/exports")
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = fetch_filtered_images(
        db_path="/home/mkutuga/SemiF-DB/AgIR_DB_v1_0_202510.db", 
        table="semif", 
        common_name="barley", 
        area_bin="500-1000"
    )

    print(f"Extracting visuals for {len(rows)} records...")

    
    vx = VisualExtractorDB(root_map=root_map)
    outputs = vx.export_assets(
        rows=rows,
        outdir=output_dir,
        line_width=line_width,
        save_image=True,
        save_cutout=False,
        save_mask=False,
        save_bbox=True,
        save_metadata=True
    )

    print("Wrote:")
    for k, v in outputs.items():
        if v:
            print(f"  {k}: {v}")
        else:
            print(f"  {k}: (not written)")


if __name__ == "__main__":
    main()
