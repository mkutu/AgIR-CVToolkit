# src/agir_cvtoolkit/pipelines/stages/preprocess.py

"""
Preprocessing stage for training data preparation.

Workflow:
1. Aggregate tasks from multiple sources (if needed)
2. Resolve images for masks (check local, CVAT, database)
3. Create image/mask manifest
4. Standardize sizes via pad/grid-crop/resize
5. Split into train/val/test sets
6. Compute dataset statistics for normalization
"""

import json
import logging
from pathlib import Path

from omegaconf import DictConfig

from agir_cvtoolkit.core.db import AgirDB
from agir_cvtoolkit.pipelines.utils.preprocess_utils import (
    pad_gridcrop_resize_preprocess,
    train_val_test_split,
    compute_rgb_mean_std,
)
from agir_cvtoolkit.pipelines.utils.image_resolver import ImageResolver

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
            "resolved_images": 0,
            "preprocessed_images": 0,
            "train_samples": 0,
            "val_samples": 0,
            "test_samples": 0,
            "rgb_mean": None,
            "rgb_std": None,
            "aggregated_tasks": [],
            "total_tasks": 0,
            "resolution_stats": {},
        }
    
    def _find_source_data(self) -> tuple[Path, Path]:
        """
        Find source images and masks based on config.
        
        For CVAT downloads, may aggregate multiple tasks into one directory.
        
        Returns:
            Tuple of (images_dir, masks_dir)
        """
        source_cfg = self.preprocess_cfg.source
        
        if source_cfg.type == "cvat_download":
            # Find CVAT downloads
            cvat_downloads = Path(self.paths.cvat_downloads)
            
            if not cvat_downloads.exists():
                raise FileNotFoundError(
                    f"CVAT downloads directory not found: {cvat_downloads}\n"
                    f"Run 'agir-cvtoolkit download-cvat' first"
                )
            
            # Find task directories
            all_task_dirs = [d for d in cvat_downloads.iterdir() if d.is_dir()]
            if not all_task_dirs:
                raise FileNotFoundError(
                    f"No CVAT task directories found in: {cvat_downloads}"
                )
            
            # Filter tasks based on config
            task_filter = source_cfg.get("tasks")
            if task_filter is None:
                # Use all tasks
                selected_tasks = all_task_dirs
                log.info(f"Combining ALL {len(selected_tasks)} CVAT tasks")
            else:
                # Use specified tasks only
                task_filter = [t.lower() for t in task_filter]
                selected_tasks = [d for d in all_task_dirs if d.name.lower() in task_filter]
                
                if not selected_tasks:
                    available = [d.name for d in all_task_dirs]
                    raise ValueError(
                        f"None of the specified tasks found.\n"
                        f"Requested: {task_filter}\n"
                        f"Available: {available}"
                    )
                
                log.info(f"Combining {len(selected_tasks)} specified CVAT tasks:")
                for task in selected_tasks:
                    log.info(f"  - {task.name}")
            
            # If single task, use it directly
            if len(selected_tasks) == 1:
                task_dir = selected_tasks[0]
                log.info(f"Using single CVAT task: {task_dir.name}")
                
                images_dir = task_dir / "images"
                annotations_dir = task_dir / "annotations"
                
                # For CVAT, we often only have masks
                masks_dir = annotations_dir if annotations_dir.exists() else images_dir
                
                # Images directory might not exist or be empty
                if not images_dir.exists() or not any(images_dir.iterdir()):
                    log.warning(f"No images found in {images_dir}, will resolve from database")
                    images_dir = self.run_root / "images"
                
                self.metrics["total_tasks"] = 1
                return images_dir, masks_dir
            
            # Multiple tasks: aggregate into combined directory
            return self._aggregate_tasks(selected_tasks)
        
        elif source_cfg.type == "custom":
            images_dir = Path(source_cfg.custom_images_dir)
            masks_dir = Path(source_cfg.custom_masks_dir)
            
            if not images_dir.exists():
                raise FileNotFoundError(f"Custom images directory not found: {images_dir}")
            if not masks_dir.exists():
                raise FileNotFoundError(f"Custom masks directory not found: {masks_dir}")
            self.metrics["total_tasks"] = 1
            return images_dir, masks_dir
        
        elif source_cfg.type == "inference_results":
            images_dir = Path(self.paths.images)
            masks_dir = Path(self.paths.masks)

            if not images_dir.exists():
                raise FileNotFoundError(f"Inference images directory not found: {images_dir}")
            if not masks_dir.exists():
                raise FileNotFoundError(f"Inference masks directory not found: {masks_dir}")
            self.metrics["total_tasks"] = 1
            return images_dir, masks_dir
        
        else:
            raise ValueError(f"Unknown source type: {source_cfg.type}")
    
    def _aggregate_tasks(self, task_dirs: list[Path]) -> tuple[Path, Path]:
        """
        Aggregate images and masks from multiple CVAT tasks into one directory.
        
        Args:
            task_dirs: List of task directories to aggregate
        
        Returns:
            Tuple of (combined_images_dir, combined_masks_dir)
        """
        log.info("=" * 80)
        log.info(f"Aggregating {len(task_dirs)} CVAT tasks...")
        log.info("=" * 80)
        
        # Create combined directories
        combined_images = Path(self.paths.preprocessed) / "images"
        combined_masks = Path(self.paths.preprocessed) / "masks"
        combined_images.mkdir(parents=True, exist_ok=True)
        combined_masks.mkdir(parents=True, exist_ok=True)
        
        import shutil
        
        total_images = 0
        total_masks = 0
        task_stats = []
        
        for task_dir in task_dirs:
            log.info(f"Processing task: {task_dir.name}")
            
            # Find images directory
            images_dir = task_dir / "images"
            
            # Find masks directory (try annotations first, then images)
            masks_dir = task_dir / "defaultannot"
            if not masks_dir.exists():
                masks_dir = images_dir
            
            # Copy images if they exist
            copied_images = 0
            if images_dir.exists():
                task_images = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.JPG"))
                for img_path in task_images:
                    # Create unique filename: taskname_originalname
                    new_name = f"{img_path.name}"
                    dest_path = combined_images / new_name
                    
                    # Skip if already exists (avoid duplicates)
                    if dest_path.exists():
                        log.warning(f"  Skipping duplicate: {new_name}")
                        continue
                    
                    shutil.copy2(img_path, dest_path)
                    copied_images += 1
            
            # Copy masks
            if not masks_dir.exists():
                log.warning(f"  No masks directory found, skipping masks")
                continue
            
            task_masks = list(masks_dir.glob("*_mask.png")) + list(masks_dir.glob("*.png"))
            copied_masks = 0
            for mask_path in task_masks:
                # Match the renamed image
                new_name = f"{mask_path.name}"
                dest_path = combined_masks / new_name
                
                if dest_path.exists():
                    log.warning(f"  Skipping duplicate mask: {new_name}")
                    continue
                
                shutil.copy2(mask_path, dest_path)
                copied_masks += 1
            
            log.info(f"  Copied {copied_images} images, {copied_masks} masks")
            
            total_images += copied_images
            total_masks += copied_masks
            
            task_stats.append({
                "task_name": task_dir.name,
                "images": copied_images,
                "masks": copied_masks,
            })
        
        log.info("")
        log.info(f"Aggregation complete:")
        log.info(f"  Total images: {total_images}")
        log.info(f"  Total masks: {total_masks}")
        log.info(f"  Output: {combined_images}")
        log.info("=" * 80)
        log.info("")
        
        # Store task stats in metrics
        self.metrics["aggregated_tasks"] = task_stats
        self.metrics["total_tasks"] = len(task_dirs)
        
        return combined_images, combined_masks
    
    def _resolve_images(
        self,
        masks_dir: Path,
        task_names: list[str] = None
    ) -> Path:
        """
        Resolve image locations for all masks and create manifest.
        
        This handles cases where CVAT downloads only include masks,
        resolving images from:
        1. run_root/images (from inference)
        2. CVAT task folders
        3. Database query + download
        
        Args:
            masks_dir: Directory containing mask files
            task_names: List of task names (for aggregated tasks)
        
        Returns:
            Path to manifest file
        """
        log.info("")
        log.info("=" * 80)
        log.info("Resolving images for masks...")
        log.info("=" * 80)
        
        # Setup database connection if configured
        db_client = None
        source_cfg = self.preprocess_cfg.source
        
        if source_cfg.get("db"):
            db_name = source_cfg.db
            db_cfg = self.cfg.db[db_name]
            
            log.info(f"Connecting to {db_name} database for image resolution...")
            db_client = AgirDB.connect(
                db_type=db_name,
                db_path=db_cfg.db_path,
                table=db_cfg.get("table")
            )
            # Check if connection was successful
            if not db_client:
                log.error(f"Failed to connect to {db_name} database, proceeding without DB resolution")
            else:
                log.info(f"Connected to {db_name} database")
        
        # Create resolver
        resolver = ImageResolver(
            run_root=self.run_root,
            cvat_downloads_dir=Path(self.paths.cvat_downloads),
            db_client=db_client
        )
        
        # Create manifest
        manifest_path = self.run_root / "image_mask_manifest.txt"
        num_pairs = resolver.create_manifest(
            masks_dir=masks_dir,
            output_path=manifest_path,
            task_names=task_names
        )
        
        # Store stats
        self.metrics["resolved_images"] = num_pairs
        self.metrics["resolution_stats"] = resolver.stats
        
        # Close database
        if db_client:
            db_client.close()
        
        log.info("=" * 80)
        log.info("")
        
        return manifest_path
    
    def run(self) -> None:
        """Run the preprocessing pipeline."""
        log.info("=" * 80)
        log.info("Starting Preprocessing Pipeline")
        log.info("=" * 80)
        
        # Find source data
        source_images, source_masks = self._find_source_data()
        
        # Count source masks
        source_mask_files = list(source_masks.glob("*.png")) + list(source_masks.glob("*_mask.png"))
        self.metrics["source_images"] = len(source_mask_files)
        log.info(f"Found {len(source_mask_files)} source masks")
        
        # Get task names if aggregated
        task_names = None
        if self.metrics["total_tasks"] > 1:
            task_names = [t["task_name"] for t in self.metrics["aggregated_tasks"]]
        
        # Step 0: Resolve images for masks (NEW STEP)
        if self.preprocess_cfg.get("resolve_images", {}).get("enabled", True):
            manifest_path = self._resolve_images(source_masks, task_names)
            log.info(f"Image/mask manifest created: {manifest_path}")
            log.info(f"Resolved {self.metrics['resolved_images']} image/mask pairs")
        
        # Create output directories
        preprocessed_images = Path(self.paths.preprocessed) / "images"
        preprocessed_masks = Path(self.paths.preprocessed) / "masks"
        preprocessed_images.mkdir(parents=True, exist_ok=True)
        preprocessed_masks.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Pad/Grid-Crop/Resize
        if self.preprocess_cfg.pad_gridcrop_resize.enabled:
            log.info("")
            log.info("Step 1: Standardizing image sizes (pad/grid-crop/resize)...")
            log.info("-" * 80)
            
            # Use resolved images if we created them
            if self.metrics.get("resolved_images", 0) > 0:
                resolved_images_dir = self.run_root / "resolved_images"
                if resolved_images_dir.exists() and any(resolved_images_dir.iterdir()):
                    source_images = resolved_images_dir
                    log.info(f"Using resolved images from: {source_images}")
            
            pad_gridcrop_resize_preprocess(
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
            source_image_files = list(source_images.glob("*.jpg")) + list(source_images.glob("*.JPG"))
            for img_path in source_image_files:
                shutil.copy2(img_path, preprocessed_images / img_path.name)
                mask_path = source_masks / f"{img_path.stem}_mask.png"
                if mask_path.exists():
                    shutil.copy2(mask_path, preprocessed_masks / mask_path.name)
            self.metrics["preprocessed_images"] = len(source_image_files)
        
        # Step 2: Train/Val/Test Split
        if self.preprocess_cfg.split.enabled:
            log.info("")
            log.info("Step 2: Splitting into train/val/test sets...")
            log.info("-" * 80)
            
            # Output directories
            train_images = self.run_root / "train_val_test" / "train" / "images"
            train_masks = self.run_root / "train_val_test" / "train" / "masks"
            val_images = self.run_root / "train_val_test" / "val" / "images"
            val_masks = self.run_root / "train_val_test" / "val" / "masks"
            test_images = self.run_root / "train_val_test" / "test" / "images"
            test_masks = self.run_root / "train_val_test" / "test" / "masks"
            
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
        
        # Task aggregation info
        if self.metrics['total_tasks'] > 1:
            log.info(f"Combined {self.metrics['total_tasks']} CVAT tasks:")
            for task_stat in self.metrics['aggregated_tasks']:
                log.info(f"  - {task_stat['task_name']}: {task_stat['images']} images, {task_stat['masks']} masks")
            log.info("")
        
        # Image resolution info
        if self.metrics.get('resolved_images', 0) > 0:
            res_stats = self.metrics['resolution_stats']
            log.info(f"Image Resolution:")
            log.info(f"  Found in run_images: {res_stats['found_in_run_images']}")
            log.info(f"  Found in CVAT: {res_stats['found_in_cvat']}")
            log.info(f"  Found in DB: {res_stats['found_in_db']}")
            log.info(f"  Not found: {res_stats['not_found']}")
            log.info("")
        
        log.info(f"Source masks: {self.metrics['source_images']}")
        log.info(f"Resolved pairs: {self.metrics.get('resolved_images', 0)}")
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