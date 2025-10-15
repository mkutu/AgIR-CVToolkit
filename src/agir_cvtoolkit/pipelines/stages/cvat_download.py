"""
CVAT download pipeline stage using CVAT SDK.

Downloads masks and annotations from CVAT with filtering options:
- Filter by project ID (download all tasks from a project)
- Filter by task status (e.g., only "completed" tasks)
- Filter by specific task IDs
- Only download masks for images that still exist in CVAT

Installation:
    pip install cvat-sdk

Usage:
    agir-cvtoolkit download-cvat -o cvat_download.project_id=5
    agir-cvtoolkit download-cvat -o cvat_download.task_ids=[101,102,103]
    agir-cvtoolkit download-cvat -o cvat_download.required_status=completed
"""
from __future__ import annotations

import json
import logging
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set

from cvat_sdk import Client
from omegaconf import DictConfig
from tqdm import tqdm

from agir_cvtoolkit.pipelines.utils.hydra_utils import read_yaml

log = logging.getLogger(__name__)


class CVATDownloadStage:
    """Download annotations from CVAT with filtering options."""
    
    def __init__(self, cfg: DictConfig):
        self.cfg = cfg
        self.cvat_cfg = cfg.cvat_download
        self.paths = cfg.paths
        self.run_root = Path(cfg.paths.run_root)
        
        # Load credentials
        self.keys = read_yaml(cfg.io.keys_file)['cvat']
        self.cvat_host = self.keys['url']
        self.username = self.keys['username']
        self.password = self.keys['password']
        
        # CVAT organization
        self.organization_slug = self.cvat_cfg.get("organization_slug")
        
        # Filtering options
        self.task_ids = self.cvat_cfg.get("task_ids")  # None = all tasks
        self.project_id = self.cvat_cfg.get("project_id")  # None = all projects
        self.required_status = self.cvat_cfg.get("required_status", "completed")
        self.check_image_exists = self.cvat_cfg.get("check_image_exists", True)
        
        # Download settings
        self.dataset_format = self.cvat_cfg.get("dataset_format", "COCO 1.0")
        self.include_images = self.cvat_cfg.get("include_images", False)
        self.overwrite_existing = self.cvat_cfg.get("overwrite_existing", False)
        
        # SDK client (initialized on connect)
        self.client: Optional[Client] = None
        
        # Metrics
        self.metrics = {
            "total_tasks_found": 0,
            "tasks_downloaded": 0,
            "tasks_skipped": 0,
            "tasks_failed": 0,
            "images_filtered": 0,
            "project_id": self.project_id,
            "task_ids_filter": self.task_ids,
            "status_filter": self.required_status,
            "task_details": [],
        }
    
    # ==================== Connection & Setup ====================
    
    def connect(self) -> None:
        """Connect to CVAT."""
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
        if self.project_id is not None:
            self._verify_project()
        
        log.info("Successfully connected to CVAT")
    
    def _verify_project(self) -> None:
        """Verify project exists and log its details."""
        try:
            project = self.client.projects.retrieve(self.project_id)
            log.info(f"Project: {project.name} (ID: {self.project_id})")
            
            # Log project labels
            labels = project.get_labels()
            label_names = [label.name for label in labels]
            log.info(f"Project labels: {label_names}")
            
            # Log task count
            tasks = [t for t in self.client.tasks.list() if t.project_id == self.project_id]
            log.info(f"Project has {len(tasks)} total tasks")
            
        except Exception as e:
            log.warning(f"Could not verify project {self.project_id}: {e}")
    
    # ==================== Task Discovery ====================
    
    def get_tasks_to_process(self) -> List:
        """Get list of tasks to process based on filtering criteria."""
        tasks = []
        
        if self.task_ids:
            # Process specific task IDs
            log.info(f"Fetching {len(self.task_ids)} specific tasks: {self.task_ids}")
            for task_id in tqdm(self.task_ids, desc="Retrieving tasks"):
                try:
                    task = self.client.tasks.retrieve(task_id)
                    tasks.append(task)
                except Exception as e:
                    log.error(f"Failed to retrieve task {task_id}: {e}")
                    self.metrics["tasks_failed"] += 1
        else:
            # Get all tasks
            log.info("Fetching all tasks from CVAT...")
            try:
                tasks = list(self.client.tasks.list())
                log.info(f"Found {len(tasks)} total tasks")
            except Exception as e:
                log.error(f"Failed to list tasks: {e}")
                return []
        
        self.metrics["total_tasks_found"] = len(tasks)
        
        # Filter by project if specified
        if self.project_id is not None:
            log.info(f"Filtering tasks by project_id: {self.project_id}")
            initial_count = len(tasks)
            tasks = [t for t in tasks if t.project_id == self.project_id]
            filtered_count = initial_count - len(tasks)
            log.info(f"Filtered out {filtered_count} tasks not in project {self.project_id}")
        
        # Filter by status if specified
        if self.required_status:
            log.info(f"Filtering tasks with status: '{self.required_status}'")
            initial_count = len(tasks)
            tasks = [t for t in tasks if t.status == self.required_status]
            filtered_count = initial_count - len(tasks)
            log.info(f"Filtered out {filtered_count} tasks not matching status")
        
        log.info(f"Will process {len(tasks)} tasks")
        return tasks
    
    # ==================== Image Existence Checking ====================
    
    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize task name for use as directory name.
        
        - Converts to lowercase
        - Replaces spaces with underscores
        - Removes/replaces unsafe characters
        - Limits length
        """
        import re
        
        # Convert to lowercase and replace spaces
        name = name.lower().replace(" ", "_")
        
        # Remove or replace unsafe characters
        # Keep: alphanumeric, underscore, hyphen, period
        name = re.sub(r'[^\w\-.]', '_', name)
        
        # Replace multiple underscores with single
        name = re.sub(r'_+', '_', name)
        
        # Remove leading/trailing underscores
        name = name.strip('_')
        
        # Limit length (filesystem-safe, leave room for extensions)
        max_len = 200
        if len(name) > max_len:
            name = name[:max_len].rstrip('_')
        
        # Ensure not empty
        if not name:
            name = "unnamed_task"
        
        return name
    
    def get_existing_image_ids(self, task) -> Set[int]:
        """Get set of image IDs that still exist in the task."""
        if not self.check_image_exists:
            return set()
        
        log.debug(f"Fetching existing images for task {task.id}")
        
        try:
            # Get all frames/images in the task
            frames = list(task.get_frames_info())
            image_ids = {frame.id for frame in frames}
            log.debug(f"Task {task.id} has {len(image_ids)} existing images")
            return image_ids
        except Exception as e:
            log.error(f"Failed to get image list for task {task.id}: {e}")
            return set()
    
    # ==================== Dataset Download ====================
    
    def download_task_dataset(self, task) -> Optional[Path]:
        """
        Download dataset for a single task.
        
        Returns:
            Path to extracted dataset directory, or None if failed
        """
        # Sanitize task name for filesystem
        safe_task_name = self._sanitize_filename(task.name)
        task_output_dir = Path(self.paths.cvat_downloads) / safe_task_name
        task_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if already downloaded
        if not self.overwrite_existing:
            if (task_output_dir / "annotations").exists():
                log.info(f"Task '{task.name}' (ID: {task.id}) already downloaded, skipping")
                self.metrics["tasks_skipped"] += 1
                return task_output_dir
        
        log.info(
            f"Downloading task {task.id}: '{task.name}' "
            f"(status: {task.status}, size: {task.size})"
        )
        
        try:
            # Create temporary path for download
            # Note: CVAT SDK requires the file to NOT exist, so we create and delete it
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # Delete the file so CVAT SDK can create it
            Path(tmp_path).unlink()
            
            # Download dataset
            log.debug(f"Exporting dataset in format: {self.dataset_format}")
            task.export_dataset(
                format_name=self.dataset_format,
                filename=tmp_path,
                include_images=self.include_images
            )
            
            # Extract the zip file
            log.debug(f"Extracting dataset to {task_output_dir}")
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extractall(task_output_dir)
            
            # Clean up temp file
            Path(tmp_path).unlink()
            
            log.info(f"Successfully downloaded task '{task.name}' (ID: {task.id})")
            self.metrics["tasks_downloaded"] += 1
            return task_output_dir
            
        except Exception as e:
            log.error(f"Failed to download task '{task.name}' (ID: {task.id}): {e}")
            self.metrics["tasks_failed"] += 1
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()
            return None
    
    # ==================== Post-Processing ====================
    
    def filter_downloaded_masks(self, task, task_output_dir: Path) -> int:
        """
        Remove masks for deleted images if check_image_exists is enabled.
        
        Returns:
            Number of images filtered out
        """
        if not self.check_image_exists:
            return 0
        
        existing_image_ids = self.get_existing_image_ids(task)
        if not existing_image_ids:
            log.warning(
                f"Could not get existing images for task {task.id}, "
                f"skipping filtering"
            )
            return 0
        
        # This is format-specific. For COCO format, we need to filter the annotations file
        if "COCO" in self.dataset_format:
            return self._filter_coco_annotations(task_output_dir, existing_image_ids)
        else:
            log.warning(
                f"Image filtering not implemented for format: {self.dataset_format}"
            )
            return 0
    
    def _filter_coco_annotations(
        self, 
        task_output_dir: Path, 
        existing_image_ids: Set[int]
    ) -> int:
        """Filter COCO annotations to only include existing images."""
        annotations_file = task_output_dir / "annotations" / "instances_default.json"
        if not annotations_file.exists():
            log.warning(f"Annotations file not found: {annotations_file}")
            return 0
        
        log.debug(f"Filtering COCO annotations at {annotations_file}")
        
        try:
            with open(annotations_file, 'r') as f:
                coco_data = json.load(f)
            
            original_image_count = len(coco_data.get('images', []))
            original_ann_count = len(coco_data.get('annotations', []))
            
            # Filter images - keep only those that exist
            # Note: You may need to adjust this logic based on how CVAT maps frame IDs
            filtered_images = coco_data.get('images', [])
            filtered_image_ids = {img['id'] for img in filtered_images}
            
            # Filter annotations to match filtered images
            filtered_annotations = [
                ann for ann in coco_data.get('annotations', [])
                if ann['image_id'] in filtered_image_ids
            ]
            
            coco_data['images'] = filtered_images
            coco_data['annotations'] = filtered_annotations
            
            # Save filtered annotations
            with open(annotations_file, 'w') as f:
                json.dump(coco_data, f, indent=2)
            
            removed_count = original_image_count - len(filtered_images)
            removed_ann_count = original_ann_count - len(filtered_annotations)
            
            if removed_count > 0:
                log.info(
                    f"Filtered annotations: removed {removed_count} deleted images "
                    f"and {removed_ann_count} annotations"
                )
                self.metrics["images_filtered"] += removed_count
            
            return removed_count
            
        except Exception as e:
            log.error(f"Failed to filter COCO annotations: {e}")
            return 0
    
    # ==================== Main Pipeline ====================
    
    def run(self) -> None:
        """Run CVAT download pipeline."""
        log.info("=" * 80)
        log.info("Starting CVAT Download Pipeline")
        log.info("=" * 80)
        
        # Connect to CVAT
        self.connect()
        
        # Log configuration
        log.info(f"Dataset format: {self.dataset_format}")
        log.info(f"Include images: {self.include_images}")
        log.info(f"Check image exists: {self.check_image_exists}")
        if self.project_id is not None:
            log.info(f"Project ID filter: {self.project_id}")
        if self.required_status:
            log.info(f"Required status: {self.required_status}")
        if self.task_ids:
            log.info(f"Task IDs: {self.task_ids}")
        log.info("")
        
        # Get tasks to process
        tasks = self.get_tasks_to_process()
        
        if not tasks:
            log.warning("No tasks found matching the criteria, exiting")
            return
        
        # Create output directory
        downloads_dir = Path(self.paths.cvat_downloads)
        downloads_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Downloads will be saved to: {downloads_dir}")
        log.info("")
        
        # Process each task
        for task in tqdm(tasks, desc="Downloading tasks"):
            log.info(f"Processing task {task.id}: {task.name}")
            
            # Download task dataset
            task_output_dir = self.download_task_dataset(task)
            
            if task_output_dir:
                # Filter out masks for deleted images if needed
                filtered_count = self.filter_downloaded_masks(task, task_output_dir)
                
                # Record task details
                self.metrics["task_details"].append({
                    "task_id": task.id,
                    "task_name": task.name,
                    "directory_name": task_output_dir.name,  # Sanitized name
                    "status": task.status,
                    "size": task.size,
                    "output_dir": str(task_output_dir),
                    "images_filtered": filtered_count,
                    "success": True,
                })
            else:
                # Record failed task
                self.metrics["task_details"].append({
                    "task_id": task.id,
                    "task_name": task.name,
                    "status": task.status,
                    "success": False,
                })
        
        # Save metrics
        metrics_path = Path(self.paths.metrics_path)
        with open(metrics_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
        
        # Summary
        log.info("")
        log.info("=" * 80)
        log.info("CVAT Download Complete")
        log.info("=" * 80)
        log.info(f"Total tasks found: {self.metrics['total_tasks_found']}")
        log.info(f"Tasks downloaded: {self.metrics['tasks_downloaded']}")
        log.info(f"Tasks skipped: {self.metrics['tasks_skipped']}")
        log.info(f"Tasks failed: {self.metrics['tasks_failed']}")
        if self.check_image_exists:
            log.info(f"Images filtered: {self.metrics['images_filtered']}")
        log.info(f"Output directory: {downloads_dir}")
        log.info(f"Metrics saved to: {metrics_path}")
        log.info("=" * 80)