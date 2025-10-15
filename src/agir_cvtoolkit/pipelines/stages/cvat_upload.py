"""
CVAT upload pipeline stage using CVAT SDK.

Production-ready implementation with guaranteed order alignment.

Installation:
    pip install cvat-sdk

Usage:
    agir-cvtoolkit upload-cvat -o cvat_upload.source.type=segmentations
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from cvat_sdk import Client, models
from cvat_sdk.masks import encode_mask
from cvat_sdk.core.proxies.tasks import ResourceType
from omegaconf import DictConfig
from PIL import Image
from tqdm import tqdm

from agir_cvtoolkit.pipelines.utils.hydra_utils import read_yaml
from agir_cvtoolkit.pipelines.utils.species import SpeciesInfo

log = logging.getLogger(__name__)


@dataclass
class UploadBatch:
    """
    Container for aligned upload data.
    
    CRITICAL: All lists must be in the same order!
    - records[i] corresponds to images[i] corresponds to masks[i] (if present)
    - Frame index in CVAT = index in these lists
    """
    records: List[Dict]
    image_paths: List[Path]
    mask_paths: Optional[List[Optional[Path]]] = None  # None for detections
    
    def __len__(self) -> int:
        return len(self.records)
    
    def validate(self) -> None:
        """Validate that all lists are aligned."""
        if len(self.records) != len(self.image_paths):
            raise ValueError(
                f"Misaligned data: {len(self.records)} records but "
                f"{len(self.image_paths)} images"
            )
        if self.mask_paths is not None:
            if len(self.mask_paths) != len(self.records):
                raise ValueError(
                    f"Misaligned data: {len(self.records)} records but "
                    f"{len(self.mask_paths)} masks"
                )


class CVATUploadStage:
    """Upload annotations to CVAT using official SDK."""
    
    def __init__(self, cfg: DictConfig):
        self.cfg = cfg
        self.cvat_cfg = cfg.cvat_upload
        self.paths = cfg.paths
        self.run_root = Path(cfg.paths.run_root)
        
        # Load credentials
        self.keys = read_yaml(cfg.io.keys_file)['cvat']
        self.cvat_host = self.keys['url']
        self.username = self.keys['username']
        self.password = self.keys['password']
        
        # Species info for label mapping
        self.species_info = SpeciesInfo(Path(cfg.io.lts_species_info))
        self.species_info.load()
        
        # CVAT organization/project
        self.organization_slug = self.cvat_cfg.get("organization_slug")
        self.project_id = self.cvat_cfg.get("project_id")

        # Create task name
        self.task_name = f"{self.cfg.project.name}_{self.cfg.project.subname}"
        
        # Upload strategy
        self.mask_strategy = self.cvat_cfg.get("mask_strategy", "mask")
        
        # SDK client (initialized on connect)
        self.client: Optional[Client] = None
        
        # Metrics
        self.metrics = {
            "total_records": 0,
            "uploaded_annotations": 0,
            "skipped": 0,
            "failed": 0,
            "task_id": None,
            "task_url": None,
            "organization_slug": self.organization_slug,
            "project_id": self.project_id,
        }
    
    # ==================== Connection & Setup ====================
    
    def connect(self) -> None:
        """Connect to CVAT and verify configuration."""
        log.info(f"Connecting to CVAT at {self.cvat_host}...")
        
        self.client = Client(url=self.cvat_host)
        self.client.login((self.username, self.password))
        
        # Set organization context
        if self.organization_slug:
            self.client.organization_slug = self.organization_slug
            log.info(f"Using organization: {self.organization_slug}")
        else:
            self.client.organization_slug = None
            log.info("Using personal workspace")
        
        # Verify project if specified
        if self.project_id:
            self._verify_project()
        
        log.info("Successfully connected to CVAT")
    
    def _verify_project(self) -> None:
        """Verify project exists and log its labels."""
        try:
            project = self.client.projects.retrieve(self.project_id)
            log.info(f"Project: {project.name} (ID: {self.project_id})")
            
            # Log project labels
            labels = project.get_labels()
            label_names = [label.name for label in labels]
            log.info(f"Project labels: {label_names}")
            
        except Exception as e:
            log.warning(f"Could not verify project {self.project_id}: {e}")
    
    # ==================== Data Loading & Alignment ====================
    
    def prepare_upload_batch(self, source_type: str) -> UploadBatch:
        """
        Prepare aligned batch of records, images, and masks.
        
        This is the CRITICAL method that ensures order alignment!
        
        Args:
            source_type: "detections" or "segmentations"
        
        Returns:
            UploadBatch with guaranteed aligned data
        """
        log.info(f"Preparing upload batch for {source_type}...")
        
        # Load query records
        records = self._load_records()
        if not records:
            log.warning("No records to upload.")
            return UploadBatch(records=[], image_paths=[], mask_paths=None)
        log.info(f"Loaded {len(records)} records from query")
        
        if source_type == "detections":
            return self._prepare_detection_batch(records)
        elif source_type == "segmentations":
            return self._prepare_segmentation_batch(records)
        else:
            raise ValueError(f"Unknown source type: {source_type}")
    
    def _prepare_detection_batch(self, records: List[Dict]) -> UploadBatch:
        """
        Prepare batch for detection upload.
        
        Order: Determined by records list from query.
        """
        aligned_records = []
        aligned_images = []
        
        for rec in tqdm(records, desc="Resolving image paths"):
            img_path = self._resolve_image_path(rec)
            if img_path and img_path.exists():
                aligned_records.append(rec)
                aligned_images.append(img_path)
            else:
                log.warning(f"Image not found for {rec.get('cutout_id')}, skipping")
                self.metrics["skipped"] += 1
        
        batch = UploadBatch(
            records=aligned_records,
            image_paths=aligned_images,
            mask_paths=None,  # No masks for detections
        )
        
        log.info(f"Prepared {len(batch)} detection samples")
        return batch
    
    def _prepare_segmentation_batch(self, records: List[Dict]) -> UploadBatch:
        """
        Prepare batch for segmentation upload.
        
        Order: SORTED by record_id to ensure consistent alignment with CVAT!
        """
        # Load manifest (already has aligned image_path and mask_path)
        manifest = self._load_manifest()
        log.info(f"Loaded {len(manifest)} entries from manifest")
        
        # Build lookup: record_id -> record
        record_lookup = {
            rec.get("cutout_id", rec.get("id")): rec 
            for rec in records
        }
        
        # Collect valid entries
        valid_entries = []
        
        for entry in tqdm(manifest, desc="Validating data"):
            record_id = entry["record_id"]
            image_path = Path(entry["image_path"])
            mask_path = Path(entry["mask_path"]) if entry.get("mask_path") else None
            
            # Skip if image doesn't exist
            if not image_path.exists():
                log.warning(f"Image not found for {record_id}, skipping")
                self.metrics["skipped"] += 1
                continue
            
            # Skip if mask doesn't exist
            if mask_path and not mask_path.exists():
                log.warning(f"Mask not found for {record_id}, skipping")
                self.metrics["skipped"] += 1
                continue
            
            # Get corresponding record
            record = record_lookup.get(record_id)
            if not record:
                log.warning(f"Record not found for {record_id}, skipping")
                self.metrics["skipped"] += 1
                continue
            
            # Add to valid entries list
            valid_entries.append({
                "record": record,
                "image_path": image_path,
                "mask_path": mask_path,
                "record_id": record_id,
            })
        
        # ⭐ CRITICAL: Sort by record_id to ensure consistent order!
        # This matches test_upload.py behavior (alphabetical sorting)
        log.info("Sorting entries by record_id for consistent frame order...")
        valid_entries.sort(key=lambda x: x["record_id"])
        
        # Build aligned lists in sorted order
        aligned_records = [e["record"] for e in valid_entries]
        aligned_images = [e["image_path"] for e in valid_entries]
        aligned_masks = [e["mask_path"] for e in valid_entries]
        
        batch = UploadBatch(
            records=aligned_records,
            image_paths=aligned_images,
            mask_paths=aligned_masks,
        )
        
        batch.validate()  # Safety check
        log.info(f"Prepared {len(batch)} segmentation samples (sorted by record_id)")
        return batch
    
    # ==================== Task Creation ====================

    def create_task(self, image_paths: List[Path]) -> int:
        """
        Create CVAT task with images.
        
        Args:
            image_paths: Ordered list of image paths
        
        Returns:
            task_id: Created task ID
        """
        if not self.client:
            self.connect()

        log.info(f"Creating CVAT task: {self.task_name}")
        log.info(f"Uploading {len(image_paths)} images...")
        
        # Build task spec
        if self.project_id:
            # Task in project - inherits labels
            task_spec = {
                "name": self.task_name,
                "project_id": self.project_id,
            }
            log.info("Task will inherit labels from project")
        else:
            # Standalone task - define labels
            labels = self.cvat_cfg.labels
            task_spec = {
                "name": self.task_name,
                "labels": [models.PatchedLabelRequest(name=name) for name in labels],
            }
            log.info(f"Task will use labels: {labels}")
        
        # Create task and upload images
        task = self.client.tasks.create_from_data(
            spec=task_spec,
            resource_type=ResourceType.LOCAL,
            data_params={"image_quality": 100},
            resources=[str(p) for p in image_paths],
        )
        
        task_id = task.id
        log.info(f"Created task {task_id}")
        
        # Log labels being used
        self._log_task_labels(task_id)
        
        return task_id
    
    def _log_task_labels(self, task_id: int) -> None:
        """Log the labels available for this task."""
        try:
            task = self.client.tasks.retrieve(task_id)
            labels = task.get_labels()
            label_names = [label.name for label in labels]
            log.info(f"Task labels: {label_names}")
        except Exception as e:
            log.debug(f"Could not log task labels: {e}")
    
    # ==================== Annotation Upload ====================
    
    def upload_detections(self, task_id: int, batch: UploadBatch) -> None:
        """
        Upload detection bounding boxes.
        
        Args:
            task_id: CVAT task ID
            batch: Aligned upload batch
        """
        log.info("Creating detection annotations...")
        
        # Get label mapping
        label_name_to_id = self._get_task_labels(task_id)
        label_map = self.cvat_cfg.label_map
        
        # Build shapes (frame_idx matches batch index!)
        shapes = []
        for frame_idx, record in enumerate(tqdm(batch.records, desc="Building annotations")):
            # Get label for this record
            label_name = self._get_label_name(record, label_map)
            if label_name not in label_name_to_id:
                log.warning(f"Label '{label_name}' not in task, skipping")
                self.metrics["failed"] += 1
                continue
            
            # Parse bbox
            bbox_xywh = record.get("bbox_xywh")
            if not bbox_xywh:
                continue
            
            try:
                if isinstance(bbox_xywh, str):
                    import ast
                    bbox_xywh = ast.literal_eval(bbox_xywh)
                
                x, y, w, h = [float(v) for v in bbox_xywh]
                
                shapes.append(
                    models.LabeledShapeRequest(
                        type="rectangle",
                        frame=frame_idx,  # CRITICAL: Must match image order!
                        label_id=label_name_to_id[label_name],
                        points=[x, y, x + w, y + h],
                    )
                )
            except Exception as e:
                log.warning(f"Failed to parse bbox for frame {frame_idx}: {e}")
                self.metrics["failed"] += 1
                continue
        
        # Upload
        if shapes:
            log.info(f"Uploading {len(shapes)} detection annotations...")
            self.client.tasks.create_annotations(
                task_id,
                models.LabeledDataRequest(shapes=shapes)
            )
            self.metrics["uploaded_annotations"] = len(shapes)
            log.info(f"Successfully uploaded {len(shapes)} detections")
        else:
            log.warning("No valid detection annotations to upload")
    
    def upload_segmentations(self, task_id: int, batch: UploadBatch) -> None:
        """
        Upload segmentation masks.
        
        Args:
            task_id: CVAT task ID
            batch: Aligned upload batch (must have mask_paths)
        """
        if batch.mask_paths is None:
            raise ValueError("Batch must have mask_paths for segmentation upload")
        
        log.info("Creating segmentation annotations...")
        
        # Get label mapping
        label_name_to_id = self._get_task_labels(task_id)
        label_map = self.cvat_cfg.label_map
        
        # Build shapes (frame_idx matches batch index!)
        shapes = []
        for frame_idx, (record, mask_path) in enumerate(
            tqdm(
                zip(batch.records, batch.mask_paths),
                desc="Building annotations",
                total=len(batch)
            )
        ):
            # Get label for this record
            label_name = self._get_label_name(record, label_map)
            if label_name not in label_name_to_id:
                log.warning(f"Label '{label_name}' not in task, skipping")
                self.metrics["failed"] += 1
                continue
            
            # Skip if no mask
            if not mask_path or not mask_path.exists():
                log.warning(f"Mask not found for frame {frame_idx}, skipping")
                self.metrics["failed"] += 1
                continue
            
            try:
                # Load and process mask
                mask = np.array(Image.open(mask_path).convert("L"))
                binary_mask = (mask > 0).astype(np.uint8)
                # Create CVAT mask annotation
                shape = self._create_mask_annotation(
                    binary_mask,
                    frame_idx,  # CRITICAL: Must match image order!
                    label_name_to_id[label_name]
                )
                if shape:
                    shapes.append(shape)
                
            except Exception as e:
                log.exception(f"Failed to process mask for frame {frame_idx}: {e}")
                self.metrics["failed"] += 1
                continue
        
        # Upload
        if shapes:
            log.info(f"Uploading {len(shapes)} segmentation annotations...")
            task = self.client.tasks.retrieve(task_id)
            task.update_annotations({
                "shapes": shapes,
                "tracks": [],
                "tags": [],
                "version": 0
            })
            self.metrics["uploaded_annotations"] = len(shapes)
            log.info(f"Successfully uploaded {len(shapes)} segmentations")
        else:
            log.warning("No valid segmentation annotations to upload")
    
    def _create_mask_annotation(
        self,
        mask: np.ndarray,
        frame_id: int,
        label_id: int,
    ) -> Optional[Dict]:
        """
        Create CVAT mask annotation with proper encoding.
        
        Args:
            mask: Binary mask (uint8, 0 or 1)
            frame_id: Frame index
            label_id: Label ID
        
        Returns:
            Annotation dict or None if mask is invalid
        """

        # Find bounding box
        if np.sum(mask) == 0:
            # Empty mask - create minimal bbox
            bbox = [0, 0, mask.shape[1] - 1, mask.shape[0] - 1]
            bool_mask = mask.astype(bool)
        else:
            y_indices, x_indices = np.where(mask)
            x1, x2 = int(np.min(x_indices)), int(np.max(x_indices))
            y1, y2 = int(np.min(y_indices)), int(np.max(y_indices))
            
            # Expand bbox to include right/bottom pixels
            x2 = x2 + 1 if x1 == x2 else x2
            y2 = y2 + 1 if y1 == y2 else y2
            
            bbox = [x1, y1, x2, y2]
            bool_mask = mask.astype(bool)
        
        # Encode mask using CVAT SDK
        try:
            encoded_mask = encode_mask(bool_mask, bbox)
        except Exception as e:
            log.warning(f"Failed to encode mask for frame {frame_id}: {e}")
            return None
        
        return {
            "type": "mask",
            "frame": frame_id,
            "label_id": label_id,
            "points": encoded_mask,
            "occluded": False,
            "attributes": []
        }
    
    # ==================== Helper Methods ====================
    
    def _get_task_labels(self, task_id: int) -> Dict[str, int]:
        """Get label name -> ID mapping for task."""
        task = self.client.tasks.retrieve(task_id)
        labels = task.get_labels()
        return {label.name: label.id for label in labels}
    
    def _get_label_name(self, record: Dict, label_map: Dict[str, str]) -> str:
        """Extract label name from record using label map."""
        for source_field, cvat_label in label_map.items():
            value = record.get(source_field)
            if value:
                if cvat_label == "{value}":
                    return str(value)
                else:
                    return cvat_label
        return label_map.get("_default", "unknown")
    
    def _resolve_image_path(self, record: Dict) -> Optional[Path]:
        """Resolve image path from record."""
        record_id = record.get("cutout_id", record.get("id"))
        
        # Check saved images first
        saved_img = Path(self.paths.images) / f"{record_id}.jpg"
        if saved_img.exists():
            return saved_img
        
        # SemiF cropout
        if "cropout_path" in record and record.get("cropout_path"):
            if record["cropout_path"].lower() not in ("none", "null", ""):
                root = Path("/mnt/research-projects/s/screberg")
                cutout_root = record.get("cutout_ncsu_nfs", "")
                img_path = root / cutout_root / record["cropout_path"]
                if img_path.exists():
                    return img_path
        
        # SemiF image_path
        if "image_path" in record and record.get("image_path"):
            if record["image_path"].lower() not in ("none", "null", ""):
                root = Path("/mnt/research-projects/s/screberg")
                img_root = record.get("ncsu_nfs", "")
                img_path = root / img_root / record["image_path"]
                if img_path.exists():
                    return img_path
        
        # Field database
        if "developed_image_path" in record and record.get("developed_image_path"):
            root = Path("/mnt/research-projects/r/raatwell/longterm_images3")
            img_path = root / record["developed_image_path"]
            if img_path.exists():
                return img_path
        
        return None
    
    def _load_records(self) -> List[Dict]:
        """Load records from query stage."""
        query_path_json = self.run_root / "query" / "query.json"
        query_path_csv = self.run_root / "query" / "query.csv"
        
        if query_path_json.exists():
            log.info(f"Loading records from: {query_path_json}")
            with open(query_path_json) as f:
                data = json.load(f)
        
        elif query_path_csv.exists():
            log.info(f"Loading records from: {query_path_csv}")
            import pandas as pd
            df = pd.read_csv(query_path_csv)
            df = df.where(pd.notnull(df), None)
            data = df.to_dict(orient="records")
        
        else:
            raise FileNotFoundError("No query results found (query.json or query.csv)")
        
        if not data:
            log.warning("No records found in query results")
            return []
        return data
    
    def _load_manifest(self) -> List[Dict]:
        """Load manifest from seg-infer stage."""
        manifest_path = Path(self.paths.manifest_path)
        
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        
        log.info(f"Loading manifest from: {manifest_path}")
        manifest = []
        with open(manifest_path) as f:
            for line in f:
                if line.strip():
                    manifest.append(json.loads(line))
        
        return manifest
    
    # ==================== Main Pipeline ====================
    
    def run(self) -> None:
        """Run CVAT upload pipeline."""
        log.info("=" * 80)
        log.info("Starting CVAT Upload Pipeline")
        log.info("=" * 80)
        
        # Connect to CVAT
        self.connect()
        
        # Determine source type
        source_type = self.cvat_cfg.source.type
        log.info(f"Upload type: {source_type}")
        
        # Prepare aligned batch
        batch = self.prepare_upload_batch(source_type)
        if len(batch) == 0:
            log.warning("No data to upload, exiting")
            return
        self.metrics["total_records"] = len(batch)
        
        # Create CVAT task
        task_id = self.create_task(batch.image_paths)
        self.metrics["task_id"] = task_id
        self.metrics["task_url"] = f"{self.cvat_host}/tasks/{task_id}"
        
        # Upload annotations
        if source_type == "detections":
            self.upload_detections(task_id, batch)
        elif source_type == "segmentations":
            self.upload_segmentations(task_id, batch)
        
        # Save metrics
        metrics_path = Path(self.paths.metrics_path)
        with open(metrics_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
        
        # Summary
        log.info("=" * 80)
        log.info("CVAT Upload Complete")
        log.info("=" * 80)
        log.info(f"Task URL: {self.metrics['task_url']}")
        log.info(f"Uploaded: {self.metrics['uploaded_annotations']} annotations")
        log.info(f"Skipped: {self.metrics['skipped']} items")
        log.info(f"Failed: {self.metrics['failed']} items")
        log.info("=" * 80)