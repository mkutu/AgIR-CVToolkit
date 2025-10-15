# src/agir_cvtoolkit/pipelines/utils/image_resolver.py

"""
Utility for resolving image locations from masks and creating training manifests.

Handles images from multiple sources:
- CVAT downloads (masks only)
- Inference results
- Database queries
"""

import logging
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

log = logging.getLogger(__name__)


class ImageResolver:
    """Resolves image locations for masks and creates training manifests."""
    
    def __init__(
        self,
        run_root: Path,
        cvat_downloads_dir: Optional[Path] = None,
        db_client = None,
    ):
        """
        Initialize the image resolver.
        
        Args:
            run_root: Root directory for the run (contains images/, masks/, etc.)
            cvat_downloads_dir: Directory containing CVAT task downloads
            db_client: AgirDB client for querying missing images
        """
        self.run_root = Path(run_root)
        self.cvat_downloads_dir = Path(cvat_downloads_dir) if cvat_downloads_dir else None
        self.db_client = db_client
        
        # Standard locations
        self.run_images_dir = self.run_root / "images"
        self.resolved_images_dir = self.run_root / "resolved_images"
        
        # Statistics
        self.stats = {
            "total_masks": 0,
            "found_in_run_images": 0,
            "found_in_cvat": 0,
            "found_in_db": 0,
            "not_found": 0,
            "copied_from_db": 0,
        }
    
    def extract_cutout_id(self, mask_path: Path) -> Optional[str]:
        """
        Extract cutout_id from mask filename.
        
        Handles various naming patterns:
        - <task_name>_<cutout_id>.png
        - <cutout_id>_mask.png
        - <cutout_id>.png
        
        Returns:
            Cutout ID string or None if not found
        """
        stem = mask_path.stem
        
        # Remove _mask suffix if present
        if stem.endswith("_mask"):
            stem = stem[:-5]
        
        # Pattern 1: task_name_cutout_id (from aggregated tasks)
        # Look for pattern like "barley_task_IMG_20240101_123456"
        match = re.search(r'[a-z_]+_([A-Z0-9_]+)$', stem)
        if match:
            return match.group(1)
        
        # Pattern 2: Just the cutout_id
        # Format: IMG_YYYYMMDD_HHMMSS or similar
        if re.match(r'^[A-Z0-9_]+$', stem):
            return stem
        
        # Pattern 3: Extract any uppercase alphanumeric segment
        match = re.search(r'([A-Z0-9_]{10,})', stem)
        if match:
            return match.group(1)
        
        log.warning(f"Could not extract cutout_id from: {mask_path.name}")
        return None
    
    def find_image_in_run(self, cutout_id: str) -> Optional[Path]:
        """
        Look for image in run_root/images directory.
        
        Tries common extensions: .jpg, .JPG, .png, .PNG
        """
        if not self.run_images_dir.exists():
            return None
        
        for ext in [".jpg", ".JPG", ".png", ".PNG"]:
            img_path = self.run_images_dir / f"{cutout_id}{ext}"
            if img_path.exists():
                return img_path
        
        return None
    
    def find_image_in_cvat(
        self,
        mask_path: Path,
        task_name: Optional[str] = None
    ) -> Optional[Path]:
        """
        Look for image in CVAT downloads directory.
        
        Args:
            mask_path: Path to the mask file
            task_name: Optional task name to search in specific task folder
        """
        if not self.cvat_downloads_dir or not self.cvat_downloads_dir.exists():
            return None
        
        # Extract original filename from mask
        # Mask format: <task_name>_<original_name>.png or <original_name>_mask.png
        stem = mask_path.stem
        
        # Remove task prefix if present
        if task_name:
            prefix = f"{task_name}_"
            if stem.startswith(prefix):
                stem = stem[len(prefix):]
        
        # Remove _mask suffix
        if stem.endswith("_mask"):
            stem = stem[:-5]
        
        # Search in specific task folder if provided
        if task_name:
            task_dir = self.cvat_downloads_dir / task_name / "images"
            if task_dir.exists():
                for ext in [".jpg", ".JPG", ".png", ".PNG"]:
                    img_path = task_dir / f"{stem}{ext}"
                    if img_path.exists():
                        return img_path
        
        # Search all task folders
        for task_dir in self.cvat_downloads_dir.iterdir():
            if not task_dir.is_dir():
                continue
            
            images_dir = task_dir / "images"
            if not images_dir.exists():
                continue
            
            for ext in [".jpg", ".JPG", ".png", ".PNG"]:
                img_path = images_dir / f"{stem}{ext}"
                if img_path.exists():
                    return img_path
        
        return None
    
    def read_image_and_crop(self, img_path: Path, bbox: Tuple[int, int, int, int]) -> Optional[Image.Image]:
        """
        Read image and crop to bounding box in xywh format.
        """
        try:
            img = Image.open(img_path).convert("RGB")
            x, y, w, h = bbox
            x, y = max(0, x), max(0, y)
            return img.crop((x, y, x + w, y + h))
        except Exception as e:
            log.error(f"Failed to read/crop image {img_path}: {e}")
            return None

    def find_image_in_db(self, cutout_id: str, mask_path: Path) -> Optional[Path]:
        """
        Query database for image path using cutout_id.
        
        Returns:
            Path to image in original location (on NFS/LTS)
        """
        is_cropout = None
        if not self.db_client:
            log.error("No database client provided for image resolution")
            return None
        
        try:
            # Query database for this cutout_id
            record = self.db_client.get(cutout_id)
            if not record:
                # Use image_id field if available
                record = self.db_client.get_by_image_id(cutout_id)
                if record:
                    if record.cutout_id == mask_path.stem:
                        is_cropout = True
                    else:
                        is_cropout = False
                else:
                    log.warning(f"No database record found for image_id: {cutout_id}")
                    record = None

            else:
                is_cropout = True  # Assume cutout_id matches
            
            
            # Try different path fields based on database type
            if self.db_client.db_type == "semif":
                # Try cropout first (already cropped)
                cropout_path = record.aux_paths.get("cropout_path", None)
                if cropout_path and cropout_path != "None" and is_cropout:
                    cutout_ncsu_nfs = record.extras.get("cutout_ncsu_nfs", None)
                    lts_root = Path("/mnt/research-projects/s/screberg")
                    crop_path_suffix = str(cropout_path).lstrip("/")
                    crop_path = lts_root / cutout_ncsu_nfs / crop_path_suffix
                    if crop_path.exists():
                        return crop_path
                
                # Fall back to full image + bbox
                else:
                    image_path_suffix = record.image_path
                    ncsu_nfs = record.extras.get("ncsu_nfs", None)
                    lts_root = Path("/mnt/research-projects/s/screberg")
                    full_image_path = lts_root / ncsu_nfs / image_path_suffix
                    if full_image_path.exists():
                        # Save to self.resolved_images_dir
                        self.resolved_images_dir.mkdir(parents=True, exist_ok=True)
                        dest_path = self.resolved_images_dir / f"{cutout_id}.jpg"
                        if dest_path.exists():
                            return dest_path
                        if is_cropout:
                            bbox_xywh = record.extras.get("bbox_xywh", None)
                            cropped_image = self.read_image_and_crop(img_path, bbox_xywh)
                            if cropped_image:
                                cropped_image.save(dest_path, format="JPEG", quality=100)
                                return dest_path
                        else:
                            return full_image_path
                    else:
                        return None
            
            elif self.db_client.db_type == "field":
                # Try different path options
                for path_key in ["developed_image_path", "image_path"]:
                    if record.aux_paths.get(path_key):
                        img_path = record.aux_paths[path_key]
                        if img_path.exists():
                            
                                    return dest_path
            return None
            
        except Exception as e:
            log.exception(f"Error querying database for {cutout_id}: {e}")
            return None
    
    def copy_image_to_resolved(
        self,
        src_path: Path,
        cutout_id: str,
        record = None
    ) -> Path:
        """
        Copy image to resolved_images directory.
        
        If src_path points to a full image and record has bbox, crop it.
        
        Args:
            src_path: Source image path
            cutout_id: Cutout ID for naming
            record: Optional database record with bbox info
        
        Returns:
            Path to copied/cropped image in resolved_images
        """
        self.resolved_images_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine output filename
        dest_path = self.resolved_images_dir / f"{cutout_id}.jpg"
        
        # Check if we need to crop
        needs_crop = False
        if record and hasattr(record, 'extras'):
            bbox = record.extras.get('bbox_xywh')
            if bbox and 'cropout_path' not in record.aux_paths:
                needs_crop = True
        
        if needs_crop:
            # Load and crop image
            try:
                img = Image.open(src_path).convert("RGB")
                
                # Parse bbox
                if isinstance(bbox, str):
                    import ast
                    bbox = ast.literal_eval(bbox)
                
                x, y, w, h = [int(v) for v in bbox]
                x, y = max(0, x), max(0, y)
                
                # Crop
                img_cropped = img.crop((x, y, x + w, y + h))
                
                # Save
                img_cropped.save(dest_path, format="JPEG", quality=95)
                log.debug(f"Cropped and saved: {dest_path.name}")
                
            except Exception as e:
                log.error(f"Failed to crop image {src_path}: {e}")
                # Fall back to regular copy
                shutil.copy2(src_path, dest_path)
        else:
            # Just copy
            shutil.copy2(src_path, dest_path)
        
        return dest_path
    
    def resolve_image(
        self,
        mask_path: Path,
        task_name: Optional[str] = None
    ) -> Optional[Path]:
        """
        Resolve image location for a given mask.
        
        Search order:
        1. run_root/images/<cutout_id>.jpg
        2. cvat_downloads/<task>/images/<name>.jpg
        3. Database query + copy to resolved_images
        
        Args:
            mask_path: Path to mask file
            task_name: Optional task name for CVAT search
        
        Returns:
            Path to resolved image or None if not found
        """
        # Extract cutout_id
        cutout_id = self.extract_cutout_id(mask_path)
        if not cutout_id:
            self.stats["not_found"] += 1
            return None
        
        # 1. Check run_images
        img_path = self.find_image_in_run(cutout_id)
        if img_path:
            self.stats["found_in_run_images"] += 1
            return img_path
        
        # 2. Check CVAT downloads
        img_path = self.find_image_in_cvat(mask_path, task_name)
        if img_path:
            self.stats["found_in_cvat"] += 1
            return img_path
        
        # 3. Query database
        if self.db_client:
            img_path = self.find_image_in_db(cutout_id, mask_path)
            if img_path:
                self.stats["found_in_db"] += 1
                
                # Copy to resolved_images
                record = self.db_client.get(cutout_id)
                resolved_path = self.copy_image_to_resolved(
                    img_path,
                    cutout_id,
                    record
                )
                self.stats["copied_from_db"] += 1
                return resolved_path
        
        # Not found anywhere
        log.warning(f"Could not resolve image for mask: {mask_path.name}")
        self.stats["not_found"] += 1
        return None
    
    def create_manifest(
        self,
        masks_dir: Path,
        output_path: Path,
        task_names: Optional[List[str]] = None
    ) -> int:
        """
        Create a manifest file mapping masks to images.
        
        Args:
            masks_dir: Directory containing mask files
            output_path: Path to output manifest file
            task_names: Optional list of task names for CVAT search
        
        Returns:
            Number of successfully resolved image/mask pairs
        """
        log.info("Creating image/mask manifest...")
        
        # Find all masks
        mask_files = sorted(masks_dir.glob("*.png"))
        self.stats["total_masks"] = len(mask_files)
        
        log.info(f"Found {len(mask_files)} masks to resolve")
        
        # Resolve images
        manifest_lines = []
        
        for mask_path in mask_files:
            # Determine task name if from aggregated source
            task_name = None
            if task_names:
                for tn in task_names:
                    if mask_path.stem.startswith(tn):
                        task_name = tn
                        break
            
            # Resolve image
            img_path = self.resolve_image(mask_path, task_name)
            
            if img_path:
                manifest_lines.append(f"{img_path},{mask_path}\n")
        
        # Write manifest
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.writelines(manifest_lines)
        
        log.info(f"Manifest created: {output_path}")
        log.info(f"  Total pairs: {len(manifest_lines)}")
        log.info(f"  Found in run_images: {self.stats['found_in_run_images']}")
        log.info(f"  Found in CVAT: {self.stats['found_in_cvat']}")
        log.info(f"  Found in DB: {self.stats['found_in_db']}")
        log.info(f"  Copied from DB: {self.stats['copied_from_db']}")
        log.info(f"  Not found: {self.stats['not_found']}")
        
        return len(manifest_lines)