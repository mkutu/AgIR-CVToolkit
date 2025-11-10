# Detection Inference with Multiscale - Usage Guide

## Overview

The `infer-det` command performs object detection using YOLO models with multiscale inference. It processes images at multiple scales and fuses the results using weighted boxes fusion for improved detection accuracy.

## Basic Usage

```bash
# Run detection on queried images (default settings)
agir-cvtoolkit infer-det

# With custom model
agir-cvtoolkit infer-det \
  -o det_inference.model.weights=models/my_yolo_model.pt

# Adjust multiscale settings
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.scales=[0.5,1.0,1.5] \
  -o det_inference.multiscale.base_imgsz=1024
```

## Complete Workflow

### Step 1: Query Images

First, query the database to select images for detection:

```bash
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --sample "random:n=100"
```

### Step 2: Run Detection

Run multiscale detection on queried images:

```bash
agir-cvtoolkit infer-det
```

This will automatically:
1. Read images from the query results
2. Run detection at multiple scales (default: 0.5x, 0.75x, 1.0x, 1.25x, 1.5x)
3. Fuse detections using weighted boxes fusion
4. Apply final NMS
5. Save visualizations and results

## Configuration

### Multiscale Settings

Control the scales used for inference:

```bash
# Use fewer scales for faster inference
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.scales=[0.75,1.0,1.25]

# Use more scales for better accuracy
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.scales=[0.5,0.67,0.83,1.0,1.2,1.4,1.6]

# Adjust base image size
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.base_imgsz=1280
```

### Confidence and NMS Thresholds

```bash
# Adjust per-scale thresholds (before fusion)
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.per_scale_conf=0.01 \
  -o det_inference.multiscale.per_scale_iou=0.65

# Adjust final NMS thresholds (after fusion)
agir-cvtoolkit infer-det \
  -o det_inference.final_nms.conf=0.5 \
  -o det_inference.final_nms.iou=0.4
```

### Fusion Parameters

Control how detections are fused across scales:

```bash
# Adjust fusion IoU threshold
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.fusion.iou_thr=0.6

# Use max confidence instead of average
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.fusion.conf_type=max

# Skip low-confidence boxes during fusion
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.fusion.skip_box_thr=0.01
```

### Output Options

```bash
# Disable visualizations for faster processing
agir-cvtoolkit infer-det \
  -o det_inference.output.save_visualizations=false

# Save results in YOLO txt format
agir-cvtoolkit infer-det \
  -o det_inference.output.save_txt=true

# Adjust visualization appearance
agir-cvtoolkit infer-det \
  -o det_inference.output.line_width=3 \
  -o det_inference.output.font_size=1.0
```

### GPU Configuration

```bash
# Exclude specific GPUs
agir-cvtoolkit infer-det \
  -o det_inference.gpu.exclude_ids=[0,1]

# Adjust minimum free memory requirement
agir-cvtoolkit infer-det \
  -o det_inference.gpu.min_free_gb=12.0
```

## Examples

### Example 1: Fast Detection (Fewer Scales)

For quick processing with acceptable accuracy:

```bash
agir-cvtoolkit query --db semif --filters "state=NC" --limit 50

agir-cvtoolkit infer-det \
  -o det_inference.multiscale.scales=[0.75,1.0,1.25] \
  -o det_inference.multiscale.base_imgsz=640
```

### Example 2: High-Accuracy Detection (More Scales)

For maximum detection accuracy:

```bash
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley" \
  --sample "random:n=100"

agir-cvtoolkit infer-det \
  -o det_inference.multiscale.scales=[0.5,0.67,0.83,1.0,1.2,1.4,1.6] \
  -o det_inference.multiscale.base_imgsz=1280 \
  -o det_inference.multiscale.per_scale_conf=0.001 \
  -o det_inference.final_nms.conf=0.3
```

### Example 3: Large Image Detection

For high-resolution images:

```bash
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.base_imgsz=1920 \
  -o det_inference.multiscale.scales=[0.5,0.75,1.0] \
  -o det_inference.multiscale.per_scale_max_det=500 \
  -o det_inference.final_nms.max_det=500
```

### Example 4: Batch Processing with Custom Model

Process a large batch with a trained model:

```bash
# Query large dataset
agir-cvtoolkit query --db semif \
  --filters "state=NC,TX,CA" \
  --sample "random:n=1000"

# Run detection with custom model
agir-cvtoolkit infer-det \
  -o det_inference.model.weights=models/my_trained_model.pt \
  -o det_inference.multiscale.scales=[0.75,1.0,1.25] \
  -o det_inference.output.save_visualizations=false \
  -o det_inference.output.save_json=true
```

### Example 5: Small Object Detection

Optimized for detecting small objects:

```bash
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.scales=[1.0,1.25,1.5,1.75,2.0] \
  -o det_inference.multiscale.base_imgsz=1280 \
  -o det_inference.multiscale.per_scale_conf=0.0005 \
  -o det_inference.final_nms.conf=0.2 \
  -o det_inference.final_nms.iou=0.3
```

## Output Structure

After running detection, outputs are saved to:

```
outputs/runs/{run_id}/
├── plots/
│   ├── image1.jpg           # Detection visualizations
│   ├── image2.jpg
│   └── ...
├── detections.json          # All detection results
├── summary.json             # Detection summary statistics
└── cfg.yaml                 # Run configuration
```

### Detection Results Format

The `detections.json` file contains:

```json
[
  {
    "image_path": "/path/to/image.jpg",
    "detections": [
      [x1, y1, x2, y2, confidence, class_id],
      [x1, y1, x2, y2, confidence, class_id],
      ...
    ],
    "num_detections": 5
  },
  ...
]
```

### Summary Statistics

The `summary.json` file contains:

```json
{
  "total_images": 100,
  "total_detections": 523,
  "avg_detections_per_image": 5.23
}
```

## How Multiscale Inference Works

1. **Multiple Scale Inference**: The input image is processed at multiple scales (e.g., 50%, 75%, 100%, 125%, 150% of base size)

2. **Per-Scale Detection**: At each scale, YOLO detects objects with relatively permissive thresholds

3. **Weighted Boxes Fusion**: Detections from all scales are merged:
   - Boxes with high IoU across scales are clustered
   - Box coordinates are weighted by detection confidence
   - Final confidence is computed (average or max)

4. **Final NMS**: A final non-maximum suppression is applied to remove remaining duplicates

## Benefits of Multiscale Inference

- **Better Small Object Detection**: Larger scales help detect small objects
- **Better Large Object Detection**: Smaller scales help detect large objects
- **Improved Localization**: Fusion of multiple predictions improves box accuracy
- **Higher Confidence**: Multiple detections of the same object increase confidence

## Performance Considerations

- **Speed vs. Accuracy Trade-off**: More scales = better accuracy but slower inference
- **Memory Usage**: Processing multiple scales requires more GPU memory
- **Optimal Scales**: Start with [0.75, 1.0, 1.25] and adjust based on results

## Troubleshooting

### Out of Memory Error

```bash
# Reduce number of scales
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.scales=[1.0,1.25]

# Reduce base image size
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.base_imgsz=480

# Exclude busy GPUs
agir-cvtoolkit infer-det \
  -o det_inference.gpu.exclude_ids=[0]
```

### Too Many Detections

```bash
# Increase confidence threshold
agir-cvtoolkit infer-det \
  -o det_inference.final_nms.conf=0.5

# Increase NMS IoU threshold (more aggressive NMS)
agir-cvtoolkit infer-det \
  -o det_inference.final_nms.iou=0.3

# Reduce max detections
agir-cvtoolkit infer-det \
  -o det_inference.final_nms.max_det=100
```

### Missing Detections

```bash
# Decrease confidence threshold
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.per_scale_conf=0.0001 \
  -o det_inference.final_nms.conf=0.1

# Add more scales
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.scales=[0.5,0.67,0.83,1.0,1.2,1.4,1.6]

# Decrease NMS IoU threshold (less aggressive NMS)
agir-cvtoolkit infer-det \
  -o det_inference.final_nms.iou=0.6
```

## Integration with Pipeline

The detection inference stage integrates seamlessly with other pipeline stages:

```bash
# 1. Query images
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley" \
  --sample "stratified:by=area_bin,per_group=50"

# 2. Run detection
agir-cvtoolkit infer-det

# 3. Upload detections to CVAT for refinement (if implemented)
# agir-cvtoolkit upload-cvat

# 4. Download refined annotations and train detector (if implemented)
# agir-cvtoolkit download-cvat
# agir-cvtoolkit train-det
```

## API Usage

For programmatic use:

```python
from omegaconf import DictConfig, OmegaConf
from agir_cvtoolkit.pipelines.stages.det_infer import DetectionInferenceStage
from agir_cvtoolkit.pipelines.utils.hydra_utils import finalize_cfg

# Create config
cfg = OmegaConf.create({
    "det_inference": {
        "model": {"weights": "models/yolov8n.pt"},
        "multiscale": {
            "scales": [0.75, 1.0, 1.25],
            "base_imgsz": 640,
        },
        # ... other settings
    },
    "paths": {
        "query": "outputs/runs/query_xxx/query",
        # ... other paths
    }
})

# Finalize config
cfg = finalize_cfg(cfg, stage="infer_det", dataset="semif", cli_overrides=[])

# Run detection
stage = DetectionInferenceStage(cfg)
stage.run()
```

## Advanced Topics

### Custom Fusion Strategy

To implement custom fusion logic, modify the `weighted_boxes_fusion()` function in `det_infer.py`.

### Model Ensemble

To combine multiple models, run inference separately with different models and merge results:

```bash
# Model 1
agir-cvtoolkit infer-det \
  -o det_inference.model.weights=models/model1.pt \
  -o det_inference.output.save_json=true

# Model 2
agir-cvtoolkit infer-det \
  -o det_inference.model.weights=models/model2.pt \
  -o det_inference.output.save_json=true

# Then merge results programmatically
```

## References

- [Ultralytics YOLO Documentation](https://docs.ultralytics.com/)
- [Weighted Boxes Fusion Paper](https://arxiv.org/abs/1910.13302)
- [Test-Time Augmentation for Object Detection](https://arxiv.org/abs/1902.08795)
