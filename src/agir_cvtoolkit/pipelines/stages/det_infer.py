#!/usr/bin/env python3
"""
Detection Inference Stage with Multiscale Inferencing
Adapted for AgIR-CVToolkit pipeline
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import cv2
import numpy as np
import pandas as pd
import torch
from omegaconf import DictConfig
from ultralytics import YOLO
from ultralytics.engine.results import Results
from ultralytics.data.build import check_source
from ultralytics.data.loaders import LoadImagesAndVideos, SourceTypes
from torchvision.ops import batched_nms

from agir_cvtoolkit.pipelines.utils.query_utils import load_query_spec

log = logging.getLogger(__name__)

# ============================= Geometry Helpers ==============================

def iou_xyxy(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """Calculate IoU between two sets of boxes in xyxy format."""
    tl = torch.max(a[:, None, :2], b[None, :, :2])
    br = torch.min(a[:, None, 2:], b[None, :, 2:])
    wh = (br - tl).clamp(min=0)
    inter = wh[:, :, 0] * wh[:, :, 1]
    area_a = ((a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]))[:, None]
    area_b = ((b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1]))[None, :]
    union = area_a + area_b - inter + 1e-9
    return inter / union

def edge_aware_filter(
    boxes_xyxy: np.ndarray,   # [N,4] absolute pixels
    scores: np.ndarray,       # [N]
    img_wh: tuple[int, int],  # (W, H)
    *,
    base_conf: float = 0.70,      # normal final conf
    edge_band_rel: float = 0.08,  # within 8% of the nearest edge = edge zone
    min_factor: float = 0.60,     # allow down to 60% of base_conf at the edge
    taper_rel: float = 0.20       # linearly ramp back to base_conf by 20% distance
) -> tuple[np.ndarray, np.ndarray]:
    """
    Per-box dynamic threshold:
        thr_i = base_conf * f(d_edge_rel)
      where d_edge_rel in [0, inf) is the center's normalized distance to the closest edge.
      If d_edge_rel <= edge_band_rel:
          thr_i = base_conf * min_factor
      If d_edge_rel >= taper_rel:
          thr_i = base_conf
      Else linearly interpolate between those.

    Returns:
      keep_mask: [N] bool
      dyn_thr:   [N] per-box thresholds used (float32)
    """
    if len(boxes_xyxy) == 0:
        return np.zeros((0,), dtype=bool), np.zeros((0,), dtype=np.float32)

    W, H = map(float, img_wh)
    cx = (boxes_xyxy[:, 0] + boxes_xyxy[:, 2]) * 0.5
    cy = (boxes_xyxy[:, 1] + boxes_xyxy[:, 3]) * 0.5

    # distance (in pixels) from box center to the nearest frame edge
    d_left   = cx
    d_right  = W - cx
    d_top    = cy
    d_bottom = H - cy
    d_edge_px = np.minimum.reduce([d_left, d_right, d_top, d_bottom])

    # normalize by the smaller image dimension so it’s scale-invariant
    min_side = min(W, H)
    d_edge_rel = d_edge_px / (min_side + 1e-9)  # in [0, ~0.5]

    # piecewise-linear threshold factor
    #   close to edge → min_factor
    #   far from edge → 1.0
    #   between edge_band_rel and taper_rel → linear ramp
    f = np.ones_like(d_edge_rel, dtype=np.float32)
    near = d_edge_rel <= edge_band_rel
    far  = d_edge_rel >= taper_rel
    mid  = ~(near | far)

    f[near] = float(min_factor)
    if np.any(mid):
        # linear interpolation from (edge_band_rel -> min_factor) to (taper_rel -> 1.0)
        t = (d_edge_rel[mid] - edge_band_rel) / max(taper_rel - edge_band_rel, 1e-6)
        f[mid] = min_factor + t * (1.0 - min_factor)

    dyn_thr = (base_conf * f).astype(np.float32)
    keep_mask = scores >= dyn_thr
    return keep_mask, dyn_thr

@torch.no_grad()
def weighted_boxes_fusion(
    boxes_xyxy: torch.Tensor,
    scores: torch.Tensor,
    labels: torch.Tensor,
    iou_thr: float = 0.55,
    score_power: float = 1.0,
    conf_type: str = "avg",
    skip_box_thr: float = 0.0,
) -> torch.Tensor:
    """
    Weighted boxes fusion for merging detections across scales.
    
    Returns:
        torch.Tensor: [M, 6] tensor (xyxy, conf, cls) after fusing duplicates per class
    """
    device = boxes_xyxy.device
    boxes_xyxy = boxes_xyxy.detach().float()
    scores = scores.detach().float()
    labels = labels.detach().float()

    keep = scores >= skip_box_thr
    boxes_xyxy, scores, labels = boxes_xyxy[keep], scores[keep], labels[keep]

    out_boxes, out_scores, out_labels = [], [], []

    for cls in labels.unique():
        m = labels == cls
        if m.sum() == 0:
            continue
        b = boxes_xyxy[m]
        s = scores[m]

        order = torch.argsort(s, descending=True)
        b = b[order]
        s = s[order]

        clusters: list[list[int]] = []
        for i in range(b.size(0)):
            if not clusters:
                clusters.append([i])
                continue
            reps = b[torch.tensor([c[0] for c in clusters], device=b.device)]
            ious = iou_xyxy(b[i : i + 1], reps).squeeze(0)
            j = torch.argmax(ious)
            if ious[j] >= iou_thr:
                clusters[j].append(i)
            else:
                clusters.append([i])

        for idxs in clusters:
            idxs_t = torch.tensor(idxs, device=b.device)
            bb = b[idxs_t]
            ss = s[idxs_t]
            w = ss ** score_power
            w = w / (w.sum() + 1e-9)
            fused = (bb * w[:, None]).sum(dim=0)

            conf = ss.max() if conf_type == "max" else ss.mean()
            out_boxes.append(fused)
            out_scores.append(conf)
            out_labels.append(cls)

    if not out_boxes:
        return torch.zeros((0, 6), device=device, dtype=torch.float32)

    out_boxes = torch.stack(out_boxes).to(device)
    out_scores = torch.stack(out_scores).to(device)
    out_labels = torch.stack(out_labels).to(device)
    return torch.cat([out_boxes, out_scores[:, None], out_labels[:, None]], dim=1)


# ========================= Device Selection ==================================

def pick_best_device(min_free_gb: float = 8.0, exclude: list[int] | None = None) -> str:
    """
    Choose among logical CUDA devices exposed by CUDA_VISIBLE_DEVICES.
    Avoids GPUtil physical IDs to prevent invalid device ordinal errors.
    """
    if not torch.cuda.is_available():
        log.info("CUDA not available; using CPU")
        return "cpu"

    exclude = set(exclude or [])
    n = torch.cuda.device_count()
    if n == 0:
        log.info("No logical CUDA devices; using CPU")
        return "cpu"

    # Gather free memory for each logical device id
    candidates = []
    for i in range(n):
        if i in exclude:
            continue
        try:
            free_bytes, total_bytes = torch.cuda.mem_get_info(i)
            free_gb = free_bytes / (1024 ** 3)
            candidates.append((i, free_gb))
        except Exception as e:
            log.warning(f"Skipping device {i} due to mem_get_info error: {e}")

    if not candidates:
        # if everything excluded or errored, retry without exclude
        for i in range(n):
            try:
                free_bytes, _ = torch.cuda.mem_get_info(i)
                free_gb = free_bytes / (1024 ** 3)
                candidates.append((i, free_gb))
            except Exception:
                pass

    if not candidates:
        log.info("Could not query device memory; defaulting to cuda:0")
        return "cuda:0"

    # Prefer those meeting threshold; else take max free anyway
    meeting = [c for c in candidates if c[1] >= min_free_gb]
    chosen = max(meeting or candidates, key=lambda x: x[1])[0]

    # Extra sanity: ensure chosen < device_count
    if chosen >= torch.cuda.device_count():
        log.warning(f"Chosen device {chosen} >= logical count; falling back to 0")
        chosen = 0

    log.info(f"Picked cuda:{chosen}")
    return f"cuda:{chosen}"


# =================== Multiscale Detection Predictor ==========================

class YOLOMultiscaleDetector:
    """
    YOLO detector with multiscale inference and weighted boxes fusion.
    """
    
    def __init__(self, cfg: DictConfig):
        self.cfg = cfg
        det_cfg = cfg.get("det_inference", {})

        # Query specification
        self.query_spec = load_query_spec(Path(cfg.paths.query) / "query_spec.json")
        # DB type
        self.db_type = self.query_spec.get("database", {}).get("type", "semif")
        
        # Model configuration
        model_cfg = det_cfg.get("model", {})
        self.model_path = Path(model_cfg.get("weights", "last.pt"))
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model weights not found: {self.model_path}")
        
        # Multiscale settings
        ms_cfg = det_cfg.get("multiscale", {})
        self.scales = ms_cfg.get("scales", [0.5, 0.75, 1.0, 1.25, 1.5])
        self.base_imgsz = ms_cfg.get("base_imgsz", 640)
        
        # Per-scale inference parameters
        self.per_scale_conf = ms_cfg.get("per_scale_conf", 0.001)
        self.per_scale_iou = ms_cfg.get("per_scale_iou", 0.7)
        self.per_scale_max_det = ms_cfg.get("per_scale_max_det", 300)
        
        # Weighted boxes fusion parameters
        fs_cfg = det_cfg.get("fusion", {})
        self.weighted_fusion_iou = fs_cfg.get("iou_thr", 0.65)
        self.weighted_fusion_skip_box_thr = fs_cfg.get("skip_box_thr", 0.0)
        self.weighted_fusion_conf_type = fs_cfg.get("conf_type", "max")
        self.weighted_fusion_score_power = fs_cfg.get("score_power", 1.0)

        # Post Fusion NMS parameters
        pf = det_cfg.get("post_fusion_nms", {})
        self.post_fusion_nms_enabled = bool(pf.get("enabled", False))
        self.post_fusion_nms_iou = pf.get("iou", 0.60)
        
        # Final NMS parameters
        final_cfg = det_cfg.get("final_nms", {})
        self.final_conf = final_cfg.get("conf", 0.25)
        self.final_iou = final_cfg.get("iou", 0.45)
        self.final_max_det = final_cfg.get("max_det", 300)

        # Edge aware filtering parameters
        self.edge_cfg = det_cfg.get("edge_aware_filter", {})
        self.edge_base_conf = self.final_conf
        self.edge_band_rel = self.edge_cfg.get("edge_band_rel", 0.08)
        self.edge_min_factor = self.edge_cfg.get("min_factor", 0.50)
        self.edge_taper_rel = self.edge_cfg.get("taper_rel", 0.20)
        
        # Output settings
        output_cfg = det_cfg.get("output", {})
        self.save_visualizations = output_cfg.get("save_visualizations", True)
        self.save_txt = output_cfg.get("save_txt", False)
        self.save_json = output_cfg.get("save_json", True)
        self.draw_labels = output_cfg.get("draw_labels", True)
        self.draw_boxes = output_cfg.get("draw_boxes", True)
        self.draw_conf = output_cfg.get("draw_conf", True)
        self.line_width = output_cfg.get("line_width", 2)
        self.font_size = output_cfg.get("font_size", 0.5)
        
        # Paths
        self.save_dir = Path(cfg.paths.get("plots", "./outputs/plots"))
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        # Device
        gpu_cfg = det_cfg.get("gpu", {})
        exclude_ids = gpu_cfg.get("exclude_ids", [])
        min_free_gb = gpu_cfg.get("min_free_gb", 8.0)
        self.device = pick_best_device(min_free_gb=min_free_gb, exclude=exclude_ids)
        
        # Load model
        log.info(f"Loading YOLO model from {self.model_path}")
        self.model = YOLO(str(self.model_path))
        self.model.to(self.device)
        self.names = self.model.names
        
        log.info(f"Multiscale detection initialized:")
        log.info(f"  Scales: {self.scales}")
        log.info(f"  Base image size: {self.base_imgsz}")
        log.info(f"  Device: {self.device}")
        log.info(f"  Model: {self.model_path.name}")
    
    def run(self):
        """Run multiscale detection on queried images."""
        # Get image paths from query results
        query_csv = Path(self.cfg.paths.query) / "query.csv"
        if not query_csv.exists():
            raise FileNotFoundError(
                f"Query results not found: {query_csv}. Run 'agir-cvtoolkit query' first."
            )
        
        df = pd.read_csv(query_csv)
        
        if "image_path" not in df.columns:
            raise ValueError("Query results must contain 'image_path' column")
        
        image_src = self._resolve_image_src(self.cfg)
        log.info(f"Resolved image source directory: {image_src}")
        df['full_image_path'] = image_src / (df['ncsu_nfs'] + "/" + df['image_path'])
        image_paths = df["full_image_path"].tolist()
        image_paths = [str(p) for p in image_paths]
        log.info(f"Processing {len(image_paths)} images with multiscale detection")
        source, stream, screenshot, from_img, in_memory, tensor = check_source(image_paths)
        source_type = source.source_type if in_memory else SourceTypes(stream, screenshot, from_img, tensor)
        log.info(f"Loading dataset from image paths")
        dataset = LoadImagesAndVideos(path=image_paths, batch=1, channels=3)
        setattr(dataset, "source_type", source_type)
        log.info(f"Dataset initialized with {len(dataset)} images.")
        
        results_list = []
        i = 0
        for batch in dataset:
            log.info(f"Processing batch {i+1}/{len(image_paths)}")
            paths, im0s_list, _info = batch
            path = Path(paths[0])
            im0 = im0s_list[0]

            # get df row from image path stem
            df_row = df[df['image_path'].str.contains(path.stem)].iloc[0]
            log.info(f"Processing image: {path}")
            if not path.exists():
                log.warning(f"Image not found: {path}")
                continue

            log.info(f"[{i+1}/{len(image_paths)}] Processing: {path.name}")
            i += 1

            # Run multiscale inference
            # first tier - multi-scale raw predictions
            merged = self._multiscale_raw_preds(im0)

            # second tier - edge aware conf filter
            H, W = im0.shape[:2]
            if merged.numel():
                m_np = merged.detach().cpu().numpy()
                boxes_xyxy = m_np[:, :4].astype(np.float32)
                scores     = m_np[:, 4].astype(np.float32)

                # Using edge-aware thresholds; base on final_conf
                log.info("Applying edge-aware confidence filtering")
                keep_mask, dyn_thr = edge_aware_filter(
                    boxes_xyxy, scores, img_wh=(W, H),
                    base_conf=self.edge_base_conf,
                    edge_band_rel=self.edge_band_rel,
                    min_factor=self.edge_min_factor,
                    taper_rel=self.edge_taper_rel
                )
                # log the number of masks kept
                log.info(f"Kept {keep_mask.sum()} / {len(keep_mask)} boxes after edge-aware filtering")
                if keep_mask.any():
                    merged = merged[torch.from_numpy(keep_mask).to(merged.device)]
                else:
                    merged = torch.zeros((0, 6), device=merged.device, dtype=merged.dtype)
            
            _raw = merged
            log.info(f"{_raw.shape[0]} boxes before WBF")
            if _raw.numel():
                _raw = weighted_boxes_fusion(
                    _raw[:, :4], _raw[:, 4], _raw[:, 5],
                    iou_thr=self.weighted_fusion_iou,
                    score_power=self.weighted_fusion_score_power,
                    conf_type=self.weighted_fusion_conf_type,
                    skip_box_thr=self.weighted_fusion_skip_box_thr,
                )
            log.info(f"{_raw.shape[0]} boxes after WBF")

            # Optional third-tier NMS
            if self.post_fusion_nms_enabled and _raw.numel():
                # torchvision expects integer group indices for class labels
                keep = batched_nms(
                    _raw[:, :4],                  # boxes [N,4]
                    _raw[:, 4],                   # scores [N]
                    _raw[:, 5].to(torch.int64),   # class indices [N] as int64
                    iou_threshold=self.post_fusion_nms_iou,
                )
                _raw = _raw[keep]

                if _raw.shape[0] > self.final_max_det:
                    order = torch.argsort(_raw[:, 4], descending=True)
                    _raw = _raw[order[: self.final_max_det]]
                log.info(f"{_raw.shape[0]} boxes after final NMS")

            final_results = [Results(
                boxes=_raw.detach().cpu() if _raw.numel() else _raw,  # [N,6]: xyxy, conf, cls
                orig_img=im0,
                path=str(path),
                names=self.names
            )]

            # Save visualizations if enabled
            if self.save_visualizations and final_results:
                self._save_visualizations(final_results, path, df_row)
            
            # Collect results
            if final_results[0].boxes.shape[0] > 0:
                xywh = final_results[0].boxes.xywh.detach().cpu().numpy().tolist()
                xywhn = final_results[0].boxes.xywhn.detach().cpu().numpy().tolist()
                conf = final_results[0].boxes.conf.detach().cpu().numpy().tolist()
                results_list.append({
                    "image_id": path.stem,
                    "image_path": str(path),
                    "xywh_detections": [list(x) for x in xywh],
                    "xywhn_detections": [list(x) for x in xywhn],
                    "confidences": conf,
                    "num_detections": final_results[0].boxes.shape[0],
                })
                self._save_results(results_list)
        
        # Save results
        self._save_results(results_list)
        
        log.info(f"Multiscale detection complete. Results saved to {self.save_dir}")
    
    def _resolve_image_src(self, cfg) -> Path:
        if self.db_type == "semif":
            return Path(cfg.io.get("semif_storage_dir", None))
        elif self.db_type == "field":
            return Path(cfg.io.get("field_storage_dir", None))
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

    def _multiscale_raw_preds(self, im0: np.ndarray) -> torch.Tensor:
        """
        Run inference at multiple scales and merge detections.
        
        Returns:
            torch.Tensor: [N, 6] merged detections (xyxy, conf, cls)
        """
        outs: List[torch.Tensor] = []
        
        for s in self.scales:
            imgsz = max(32, int(round(self.base_imgsz * float(s))))
            r = self.model.predict(
                source=im0,
                imgsz=imgsz,
                conf=self.per_scale_conf,
                iou=self.per_scale_iou,
                max_det=self.per_scale_max_det,
                verbose=False,
                device=self.device,
            )[0]
            
            if r.boxes is None or len(r.boxes) == 0:
                continue
            
            outs.append(
                torch.cat(
                    [
                        r.boxes.xyxy.detach().cpu(),
                        r.boxes.conf[:, None].detach().cpu(),
                        r.boxes.cls[:, None].detach().cpu(),
                    ],
                    dim=1,
                )
            )
        
        if not outs:
            return torch.zeros((0, 6), dtype=torch.float32)
        return torch.cat(outs, dim=0)

    def _save_visualizations(self, results: list[Results], path: Path, df_row: pd.Series) -> None:
        """Save detection visualizations."""
        out_path = self.save_dir / path.name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        for res in results:
            plot_img = res.plot(
                labels=self.draw_labels,
                boxes=self.draw_boxes,
                conf=self.draw_conf,
                line_width=self.line_width,
                font_size=self.font_size,
            )
            area_bin = df_row.get("estimated_area_bin", "unknown")
            common_name = df_row.get("category_common_name", "unknown")
            if pd.isna(common_name) or common_name.strip() == "":
                common_name = "unknown"
            if pd.isna(area_bin) or area_bin.strip() == "":
                area_bin = "unknown"
            # Add the area bin and common name as text on the top left corner of a 9000 x 6000 image
            text = f"{common_name} | Area Bin: {area_bin}"
            
            # dynamic sizing based on image height (works for very large images like 9000x6000)
            H_img, W_img = plot_img.shape[:2]
            font = cv2.FONT_HERSHEY_SIMPLEX
            
            # scale so that font_scale ≈ 10 for H=6000 (similar to previous hardcoded value)
            font_scale = max(0.5, H_img / 600.0)
            thickness = max(2, int(round(font_scale * 0.75)))

            # measure text size and compute padded background rectangle in top-left
            (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
            margin = int(max(10, round(0.005 * H_img)))   # small margin from borders
            padding = int(max(10, round(0.01 * H_img)))   # inner padding inside box
            x1 = margin
            y1 = margin
            x2 = min(W_img - margin, x1 + text_w + padding)
            y2 = min(H_img - margin, y1 + text_h + padding)

            # draw semi-transparent background box
            overlay = plot_img.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)
            alpha = 0.6
            cv2.addWeighted(overlay, alpha, plot_img, 1 - alpha, 0, plot_img)

            # compute text origin (bottom-left) inside the box
            text_org = (x1 + padding // 2, y1 + text_h + padding // 2 - baseline // 2)
            cv2.putText(plot_img, text, text_org, font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
            output_path_dir = out_path.parent
            output_new_name = f"{common_name.replace(' ', '_')}_{area_bin}_{path.stem}.jpg"
            out_path = output_path_dir / output_new_name
            # resize and make smaller
            plot_img = cv2.resize(plot_img, (0, 0), fx=0.25, fy=0.25)
            cv2.imwrite(str(out_path), plot_img)
            log.info(f"Saved visualization: {out_path}")
    
    def _save_results(self, results_list: list[dict]) -> None:
        """Save detection results to JSON."""
        import json
        
        results_file = self.save_dir / "detections.json"
        with open(results_file, "w") as f:
            json.dump(results_list, f, indent=2)
        
        log.info(f"Saved detection results: {results_file}")
        
        # Save summary
        total_images = len(results_list)
        total_dets = sum(r["num_detections"] for r in results_list)
        avg_dets = total_dets / total_images if total_images > 0 else 0
        
        summary = {
            "total_images": total_images,
            "total_detections": total_dets,
            "avg_detections_per_image": avg_dets,
        }
        
        summary_file = self.save_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        log.info(f"Detection summary: {total_images} images, {total_dets} detections")


# ========================= Stage Entry Point =================================

class DetectionInferenceStage:
    """Detection inference stage for AgIR-CVToolkit pipeline."""
    
    def __init__(self, cfg: DictConfig):
        self.cfg = cfg
    
    def run(self):
        """Run the detection inference stage."""
        log.info("Starting detection inference with multiscale processing")
        predictor = YOLOMultiscaleDetector(self.cfg)
        predictor.run()
        log.info("Detection inference complete")
