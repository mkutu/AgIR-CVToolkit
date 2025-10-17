"""
Segmentation inference pipeline stage.

Usage:
    agir-cvtoolkit infer-seg --override model.ckpt_path=/path/to/model.ckpt
"""
from __future__ import annotations

import json
import ast
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import torch
from omegaconf import DictConfig
from PIL import Image, ImageEnhance
from tqdm import tqdm

from agir_cvtoolkit.core.db import AgirDB
from agir_cvtoolkit.pipelines.utils.seg_utils import (
    SegModel,
    TiledInference,
    SegPostProcessor,
    SegVisualizer,
    load_image_from_record,
    select_available_gpus,
)

import logging
log = logging.getLogger(__name__)


class SegmentationInferenceStage:
    """
    Segmentation inference pipeline stage.
    
    Reads records from AgirDB query results, runs tiled inference,
    and outputs masks, visualizations, and cutouts.
    """
    
    def __init__(self, cfg: DictConfig):
        self.cfg = cfg
        self.seg_cfg = cfg.seg_inference
        self.paths = cfg.paths
        self.run_root = Path(cfg.paths.run_root)
        
        # Setup device
        self.device = self._setup_device()

        # Load model
        self.model = self._load_model()
        
        # Setup inference components
        self.tiled_inference = TiledInference(
            tile_h=self.seg_cfg.tile.height,
            tile_w=self.seg_cfg.tile.width,
            overlap=self.seg_cfg.tile.overlap,
            pad_mode=self.seg_cfg.tile.pad_mode,
            pad_divisor=self.seg_cfg.model.pad_divisor,
        )
        
        self.post_processor = SegPostProcessor(
            threshold=self.seg_cfg.post_process.threshold,
            min_area=self.seg_cfg.post_process.get("min_area", 0),
            edge_occupancy_threshold=self.seg_cfg.post_process.get("edge_occupancy_threshold"),
        )
        
        self.visualizer = SegVisualizer(
            overlay_alpha=self.seg_cfg.visualization.overlay_alpha,
        ) if self.seg_cfg.visualization.enabled else None
        
        # Track metrics
        self.metrics = {
            "total_records": 0,
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "total_inference_time_ms": 0,
        }
    
    def _setup_device(self) -> torch.device:
        """Setup GPU device."""
        gpu_cfg = self.seg_cfg.get("gpu", {})
        max_gpus = gpu_cfg.get("max_gpus", 1)
        exclude_ids = gpu_cfg.get("exclude_ids", [0])
        
        try:
            device_ids = select_available_gpus(max_gpus, exclude_ids, verbose=True)
            import os
            os.environ["CUDA_VISIBLE_DEVICES"] = ",".join(map(str, device_ids))
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            log.info(f"Using device: {device}")
            return device
        except Exception as e:
            log.warning(f"GPU setup failed: {e}, falling back to CPU")
            return torch.device("cpu")
    
    def _load_model(self) -> SegModel:
        """Load segmentation model from checkpoint."""
        model_cfg = self.seg_cfg.model
        
        log.info(f"Loading model from: {model_cfg.ckpt_path}")
        
        model = SegModel(
            arch=model_cfg.arch,
            encoder_name=model_cfg.encoder_name,
            in_channels=model_cfg.in_channels,
            num_classes=model_cfg.num_classes,
            encoder_weights=model_cfg.get("encoder_weights", "imagenet"),
            mean=model_cfg.normalization.mean,
            std=model_cfg.normalization.std,
        )
        
        model.load_checkpoint(
            Path(model_cfg.ckpt_path),
            device=self.device,
            strict=model_cfg.get("strict_load", True),
        )
        
        return model
    
    def _get_db_records(self) -> List:
        """Get records from database query or reuse previous query results."""
        source_cfg = self.seg_cfg.source
        
        if source_cfg.type == "query_result":
            # Read from previous query stage
            query_path_json = self.run_root / "query" / "query.json"
            query_path_csv = self.run_root / "query" / "query.csv"
            if query_path_json.exists():
                log.info(f"Loading records from previous query: {query_path_json}")
                with open(query_path_json) as f:
                    records = json.load(f)
                return records
            elif query_path_csv.exists():
                log.info(f"Loading records from previous query: {query_path_csv}")
                df = pd.read_csv(query_path_csv)
                if df.empty:
                    return []
                log.info(f"Loaded {len(df)} records from CSV")
                # Convert float NaNs to None for JSON serialization
                df = df.where(pd.notnull(df), None)
                # remove rows where bbox_xywh is NaN or empty
                df = df[df['bbox_xywh'].notna() & (df['bbox_xywh'] != '')]
                log.info(f"Filtered down to {len(df)} records")
                return df.to_dict(orient="records")
            else:
                raise FileNotFoundError("No previous query results found (query.json or query.csv)")
        
        elif source_cfg.type == "db_query":
            # Run fresh query
            log.info("Running fresh database query...")
            db_cfg = self.cfg.db[source_cfg.db]
            
            with AgirDB.connect(
                db_type=source_cfg.db,
                db_path=db_cfg.db_path,
                table=db_cfg.get("table"),
            ) as db:
                query = db.builder()
                
                
                # Apply filters
                if source_cfg.get("filters"):
                    for key, value in source_cfg.filters.items():
                        query = query.filter(**{key: value})
                
                
                # Apply sampling
                if source_cfg.get("sample"):
                    sample = source_cfg.sample
                    if sample.strategy == "stratified":
                        query = query.sample_stratified(
                            by=sample.by,
                            per_group=sample.per_group,
                            seed=sample.get("seed"),
                        )
                    elif sample.strategy == "random":
                        query = query.sample_random(sample.n)
                    elif sample.strategy == "seeded":
                        query = query.sample_seeded(sample.n, sample.get("seed", 42))
                
                # Apply limit
                if source_cfg.get("limit"):
                    query = query.limit(source_cfg.limit)
                
                records = query.all()
                
                # Convert to dict format
                from agir_cvtoolkit.pipelines.utils.serializers import _rec_to_dict
                records = [_rec_to_dict(r) for r in records]
            
            return records
        
        else:
            raise ValueError(f"Unknown source type: {source_cfg.type}")
    
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
                log.warning(f"Invalid RGB value format: {rgb_value}, using fallback")
                rgb = tuple(self.seg_cfg.output.get("colorize_fallback_rgb", [0, 255, 0]))
        
        except Exception as e:
            log.warning(f"Error parsing RGB value: {e}, using fallback")
            rgb = tuple(self.seg_cfg.output.get("colorize_fallback_rgb", [0, 255, 0]))
        
        # Create colored and black images
        color_img = Image.new("RGB", mask_img.size, rgb)
        black_img = Image.new("RGB", mask_img.size, (0, 0, 0))
        
        # Where mask_img > 0, take color_img; else black_img
        colorized = Image.composite(color_img, black_img, mask_img)
        
        # Brighten the result for better visualization
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(colorized)
            colorized = enhancer.enhance(brightness)
        
        # Save colorized mask
        out_path.parent.mkdir(parents=True, exist_ok=True)
        colorized.save(out_path)
        log.debug(f"Saved colorized mask to: {out_path}")


    def _get_rgb_from_record(self, record: Dict) -> Any:
        """
        Extract RGB value from database record.
        
        Args:
            record: Database record
        
        Returns:
            RGB value (string, list, or tuple), or None if not found
        """
        rgb_field = self.seg_cfg.output.get("colorize_rgb_field", "category_rgb")
        
        # Try primary field
        rgb_value = record.get(rgb_field)
        if rgb_value:
            return rgb_value
        
        # Fallback fields
        fallback_fields = ["category_rgb", "rgb", "category_hex"]
        for field in fallback_fields:
            if field in record and record.get(field):
                rgb_value = record[field]
                log.debug(f"Using RGB from fallback field: {field}")
                return rgb_value
        
        # Use configured fallback
        log.warning(f"No RGB field found in record, using fallback color")
        return self.seg_cfg.output.get("colorize_fallback_rgb", [0, 255, 0])


    
    def _process_record(
        self,
        record: Dict,
        save_mask: bool,
        save_image: bool,
        save_cutout: bool,
        save_viz: bool,
        save_colorized: bool,
    ) -> Optional[Dict]:
        """Process a single database record through the inference pipeline.
        
        Args:
            record: Database record
            save_mask: Whether to save the predicted mask
            save_image: Whether to save the source image
            save_cutout: Whether to save the masked cutout
            save_viz: Whether to save visualization
            save_colorized: Whether to save colorized mask
        
        Returns:
            Manifest entry dict, or None if skipped/failed"""
        try:
            # Get image_mode from config
            image_mode = self.seg_cfg.source.get("image_mode", "cutout")
            # Load image
            img_rgb_u8 = load_image_from_record(record, self.cfg, image_mode=image_mode)

            if img_rgb_u8 is None:
                log.warning(f"Could not load image for record {record.get('cutout_id', 'unknown')}")
                self.metrics["skipped"] += 1
                return None
            
            # Run inference
            t0 = perf_counter()
            record_id = record.get("cutout_id", record.get("id", "unknown"))

            if image_mode == "full_image":
                record_id = record.get("image_id", record_id)
                log.debug(f"Running inference on FULL IMAGE for record {record_id}...")
            else:
                log.debug(f"Running inference on CUTOUT for record {record_id}...")

            pred_mask = self.tiled_inference.predict(
                img_rgb_u8=img_rgb_u8,
                model=self.model,
                device=self.device,
            )
            inference_time_ms = int((perf_counter() - t0) * 1000)
            
            # Post-process
            log.debug(f"Post-processing mask...")
            pred_mask, edge_occupancy = self.post_processor.process(pred_mask, class_id=record.get("category_class_id", 27))
            
            # Determine if we should skip based on edge occupancy
            log.debug(f"Edge occupancy: {edge_occupancy:.3f}")
            edge_thresh = self.seg_cfg.post_process.get("edge_occupancy_threshold")
            if edge_thresh is not None and edge_occupancy > edge_thresh:
                log.info(
                    f"Skipping {record.get('cutout_id', 'unknown')} - "
                    f"edge occupancy {edge_occupancy:.3f} > {edge_thresh}"
                )
                self.metrics["skipped"] += 1
                return None
            
            # Get output paths
            common_name = record.get("category_common_name", record.get("common_name", "unknown"))
            common_name = common_name.lower().replace(" ", "_")
            area_bin = record.get("area_bin", "")
            
            # Save outputs
            if save_mask:
                mask_path = Path(self.paths.masks) / f"{record_id}.png"
                mask_path.parent.mkdir(parents=True, exist_ok=True)
                log.debug(f"Saving mask to: {mask_path}")
                Image.fromarray(pred_mask, mode="L").save(mask_path)

            # Save colorized mask
            colorized_path = None
            if save_colorized and save_mask:
                mask_path = Path(self.paths.masks) / f"{record_id}.png"
                colorized_path = Path(self.paths.colorized_masks) / f"{record_id}.png"
                
                # Get RGB value from record
                rgb_value = self._get_rgb_from_record(record)
                
                # Get brightness factor
                brightness = self.seg_cfg.output.get("colorize_brightness", 6.5)
                
                # Colorize and save
                try:
                    self._colorize_mask(
                        mask_path=mask_path,
                        rgb_value=rgb_value,
                        out_path=colorized_path,
                        brightness=brightness
                    )
                    log.debug(f"Saved colorized mask: {colorized_path}")
                except Exception as e:
                    log.error(f"Failed to colorize mask: {e}")
                    colorized_path = None
            
            if save_image:
                img_path = Path(self.paths.images) / f"{record_id}.jpg"
                img_path.parent.mkdir(parents=True, exist_ok=True)
                log.debug(f"Saving image to: {img_path}")
                # Save the high-res jpg
                Image.fromarray(img_rgb_u8, mode="RGB").save(img_path, format="JPEG", quality=100, subsampling=0, optimize=False)

            if save_cutout:
                cutout_path = Path(self.paths.cutouts) / f"{record_id}.png"
                cutout_path.parent.mkdir(parents=True, exist_ok=True)
                log.debug(f"Saving cutout to: {cutout_path}")
                self._save_cutout(img_rgb_u8, pred_mask, cutout_path)
            
            if save_viz and self.visualizer:
                viz_path = Path(self.paths.plots) / f"area_{area_bin}_{record_id}_viz.png"
                viz_path.parent.mkdir(parents=True, exist_ok=True)
                log.debug(f"Saving visualization to: {viz_path}")
                self.visualizer.plot_quad(
                    record=record,
                    img_rgb_u8=img_rgb_u8,
                    pred_mask=pred_mask,
                    out_path=viz_path,
                    edge_occupancy=edge_occupancy,
                )
            
            self.metrics["processed"] += 1
            self.metrics["total_inference_time_ms"] += inference_time_ms
            
            # Build manifest entry
            manifest_entry = {
                "record_id": record_id,
                "image_mode": image_mode,  # Track which mode was used
                "common_name": common_name,
                "area_bin": area_bin,
                "image_path": str(Path(self.paths.images) / f"{record_id}.jpg") if save_image else None,
                "mask_path": str(Path(self.paths.masks) / f"{record_id}.png") if save_mask else None,
                "colorized_mask_path": str(colorized_path) if colorized_path else None,
                "cutout_path": str(Path(self.paths.cutouts) / f"{record_id}.png") if save_cutout else None,
                "viz_path": str(Path(self.paths.plots) / f"{record_id}_viz.png") if save_viz else None,
                "inference_time_ms": inference_time_ms,
                "edge_occupancy": float(edge_occupancy),
                "image_shape": list(img_rgb_u8.shape),
                "mask_shape": list(pred_mask.shape),
                "rgb_value": str(rgb_value) if save_colorized else None,
            }
            self.metrics["processed"] += 1
            self.metrics["total_inference_time_ms"] += inference_time_ms
            
            return manifest_entry
        
        except Exception as e:
            log.error(f"Failed to process record {record_id}: {e}")
            self.metrics["failed"] += 1
            return None
    
    def _save_cutout(
        self,
        img_rgb_u8: np.ndarray,
        pred_mask: np.ndarray,
        out_path: Path,
    ) -> None:
        """Save cutout with black background."""
        alpha = (pred_mask > 0).astype(np.uint8) * 255
        
        if alpha.max() == 0:
            return  # empty mask
        
        out = np.zeros_like(img_rgb_u8)
        out[alpha > 0] = img_rgb_u8[alpha > 0]
        Image.fromarray(out, "RGB").save(out_path)
    
    def run(self) -> None:
        """Run the segmentation inference pipeline."""
        log.info("=" * 80)
        log.info("Starting Segmentation Inference Pipeline")
        log.info("=" * 80)
        
        # Load records
        records = self._get_db_records()
        if not records:
            log.warning("No records to process.")
            return
        
        self.metrics["total_records"] = len(records)
        log.info(f"Processing {len(records)} records...")
        
        # Output configuration
        output_cfg = self.seg_cfg.output
        save_mask = output_cfg.get("save_masks", True)
        save_image = output_cfg.get("save_images", False)
        save_cutout = output_cfg.get("save_cutouts", True)
        save_viz = output_cfg.get("save_viz", False)
        save_colorized = output_cfg.get("save_colorized_masks", False)
        
        manifest_path = Path(self.paths.manifest_path)
        manifest_path = manifest_path.with_suffix('.csv')  # Ensure .csv extension
        
        # Initialize CSV with header
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=[
            'record_id',
            'common_name',
            'edge_occupancy',
            'inference_time_ms',
            'mask_path',
            'image_path',
            'plot_path',
        ]).to_csv(manifest_path, index=False)

        # Metrics update interval
        metrics_update_interval = 10
        metrics_path = Path(self.paths.metrics_path)

        # Process records and write to CSV in real-time
        for idx, record in enumerate(tqdm(records, desc="Inference"), 1):
            result = self._process_record(
                record=record,
                save_mask=save_mask,
                save_image=save_image,
                save_cutout=save_cutout,
                save_viz=save_viz,
                save_colorized=save_colorized,
            )
            
            if result:
                # Convert result to DataFrame and append to CSV
                df = pd.DataFrame([result])
                df.to_csv(manifest_path, mode='a', header=False, index=False)
            
            # Update metrics periodically
            if idx % metrics_update_interval == 0:
                self.metrics["avg_inference_time_ms"] = (
                    self.metrics["total_inference_time_ms"] / self.metrics["processed"]
                    if self.metrics["processed"] > 0 else 0
                )
                with open(metrics_path, "w") as f:
                    json.dump(self.metrics, f, indent=2)
        
        # Final metrics update
        self.metrics["avg_inference_time_ms"] = (
            self.metrics["total_inference_time_ms"] / self.metrics["processed"]
            if self.metrics["processed"] > 0 else 0
        )
        
        with open(metrics_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
        
        # Summary
        log.info("=" * 80)
        log.info("Segmentation Inference Complete")
        log.info("=" * 80)
        log.info(f"Total records: {self.metrics['total_records']}")
        log.info(f"Processed: {self.metrics['processed']}")
        log.info(f"Skipped: {self.metrics['skipped']}")
        log.info(f"Failed: {self.metrics['failed']}")
        log.info(f"Avg inference time: {self.metrics['avg_inference_time_ms']:.1f}ms")
        log.info(f"Results saved to: {self.paths.run_root}")
        log.info(f"Manifest: {manifest_path}")
        log.info(f"Metrics: {metrics_path}")
        # Get log path from logging object
        log_path = Path(self.paths.logs) / Path(logging.getLogger().handlers[1].baseFilename).name
        log.info(f"Log: {log_path}")
        log.info("=" * 80)