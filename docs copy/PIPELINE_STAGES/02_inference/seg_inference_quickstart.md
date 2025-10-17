# Segmentation Inference - Quick Reference

## Overview

The segmentation inference stage runs trained models on images to generate masks. It supports:
- Tiled inference for large images
- Multiple model architectures (Unet, DeepLabV3+, Segformer)
- Post-processing (thresholding, edge occupancy filtering)
- Batch processing with progress tracking

## Quick Start

### Basic Usage

```bash
# Run inference using previous query results
agir-cvtoolkit query --db semif --filters "state=NC" --limit 100
agir-cvtoolkit infer-seg
```

### With Custom Model

```bash
# Use specific checkpoint
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=/path/to/model.ckpt
```

## Configuration

### Model Settings

```yaml
# conf/seg_inference/default.yaml
model:
  arch: "unet"  # unet | deeplabv3plus | segformer
  encoder_name: "mit_b0"
  ckpt_path: /path/to/checkpoint.ckpt
  
  normalization:
    mean: [0.414, 0.397, 0.307]
    std: [0.164, 0.144, 0.148]
```

### Tiled Inference

```yaml
tile:
  height: 1024
  width: 1024
  overlap: 0.5  # 50% overlap between tiles
  pad_mode: "reflect"
```

### Post-Processing

```yaml
post_process:
  threshold: 0.5
  min_area: 0  # Remove components smaller than this
  edge_occupancy_threshold: null  # Skip if edge > threshold
```

## Common Use Cases

### Case 1: Standard Pipeline

```bash
# 1. Query images
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley" \
  --sample "stratified:by=area_bin,per_group=50"

# 2. Run inference (auto-finds query results)
agir-cvtoolkit infer-seg

# 3. Upload to CVAT for refinement
agir-cvtoolkit upload-cvat
```

### Case 2: Fresh Database Query

```bash
# Run inference directly from database (no prior query stage)
agir-cvtoolkit infer-seg \
  -o seg_inference.source.type=db_query \
  -o seg_inference.source.filters.state=NC \
  -o seg_inference.source.limit=100
```

### Case 3: Save Images + Masks

```bash
# Save both images and masks for later upload
agir-cvtoolkit infer-seg \
  -o seg_inference.output.save_masks=true \
  -o seg_inference.output.save_images=true
```

### Case 4: Filter by Edge Occupancy

```bash
# Skip objects touching image edges
agir-cvtoolkit infer-seg \
  -o seg_inference.post_process.edge_occupancy_threshold=0.3
```

## Output Structure

```
outputs/runs/{run_id}/
├── masks/                    # Generated masks
│   ├── IMG_001.png
│   └── IMG_002.png
├── images/                   # Source images (if save_images=true)
│   ├── IMG_001.jpg
│   └── IMG_002.jpg
├── cutouts/                  # Masked cutouts (if save_cutouts=true)
│   └── IMG_001.png
├── plots/                    # Visualizations (if save_visualizations=true)
│   └── IMG_001_viz.png
├── manifest.jsonl            # Metadata for all outputs
└── metrics.json              # Performance statistics
```

## Data Sources

### From Previous Query

```bash
# Default: uses results from previous query stage
agir-cvtoolkit query --db semif --filters "state=NC"
agir-cvtoolkit infer-seg  # Reads from outputs/runs/{run_id}/query/
```

### Direct Database Query

```yaml
source:
  type: "db_query"
  db: "semif"
  
  filters:
    state: "NC"
    category_common_name: ["barley", "wheat"]
  
  sample:
    strategy: "stratified"
    by: ["category_common_name"]
    per_group: 10
  
  limit: 1000
```

## GPU Configuration

### Select Specific GPUs

```bash
# Use 2 GPUs, excluding GPU 0
agir-cvtoolkit infer-seg \
  -o seg_inference.gpu.max_gpus=2 \
  -o seg_inference.gpu.exclude_ids=[0]
```

### Auto GPU Selection

```yaml
# Automatically selects GPUs with low memory usage
gpu:
  max_gpus: 1
  exclude_ids: []  # Empty list = use any available GPU
```

## Troubleshooting

### Out of Memory

**Problem**: CUDA out of memory errors

**Solutions**:
```bash
# Reduce tile size
agir-cvtoolkit infer-seg \
  -o seg_inference.tile.height=512 \
  -o seg_inference.tile.width=512

# Use CPU
agir-cvtoolkit infer-seg \
  -o seg_inference.gpu.max_gpus=0
```

### Slow Inference

**Problem**: Processing is very slow

**Solutions**:
1. Check GPU utilization: `nvidia-smi`
2. Increase tile size if GPU has memory
3. Verify model is on GPU (check logs)

### Image Not Found

**Problem**: "Could not load image for record"

**Solutions**:
1. Check database paths are mounted correctly
2. Verify `root_map` in `conf/db/default.yaml`
3. Check file permissions on NFS/LTS storage

### Empty Masks

**Problem**: All masks are empty/black

**Solutions**:
1. Check model checkpoint path is correct
2. Verify normalization parameters match training
3. Adjust threshold: `-o seg_inference.post_process.threshold=0.3`

## Performance Metrics

The `metrics.json` file contains:

```json
{
  "total_records": 150,
  "processed": 145,
  "skipped": 3,
  "failed": 2,
  "avg_inference_time_ms": 842.5
}
```

## Integration with Pipeline

### Full Workflow

```bash
# 1. Query database
agir-cvtoolkit query --db semif \
  --sample "stratified:by=category_common_name,per_group=100"

# 2. Generate masks
agir-cvtoolkit infer-seg \
  -o seg_inference.output.save_images=true

# 3. Upload to CVAT
agir-cvtoolkit upload-cvat

# 4. [Manually refine in CVAT]

# 5. Download refined masks
agir-cvtoolkit download-cvat

# 6. Preprocess for training
agir-cvtoolkit preprocess

# 7. Train improved model
agir-cvtoolkit train

# 8. Use new model for inference
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=outputs/runs/train_xxx/model/best.pth
```

## Best Practices

1. **Always save images** when uploading to CVAT:
   ```bash
   -o seg_inference.output.save_images=true
   ```

2. **Use edge occupancy filtering** to skip incomplete objects:
   ```bash
   -o seg_inference.post_process.edge_occupancy_threshold=0.3
   ```

3. **Monitor GPU usage** to optimize tile size

4. **Keep manifest.jsonl** - it tracks all processed images and is used by upload stage

5. **Use stratified sampling** for balanced datasets

## Quick Tips

✅ **Tile overlap prevents seams** - use 0.5 for smooth masks

✅ **Save normalization stats** from training for inference

✅ **Check logs** for detailed processing info

✅ **Use manifest** to track which images were processed

✅ **Enable visualizations** during development to debug issues

## Advanced Options

### Custom Normalization

```bash
agir-cvtoolkit infer-seg \
  -o seg_inference.model.normalization.mean=[0.5,0.5,0.5] \
  -o seg_inference.model.normalization.std=[0.25,0.25,0.25]
```

### Enable Visualizations

```bash
agir-cvtoolkit infer-seg \
  -o seg_inference.output.save_visualizations=true \
  -o seg_inference.visualization.enabled=true
```

### Strict Model Loading

```bash
# Require exact parameter match when loading checkpoint
agir-cvtoolkit infer-seg \
  -o seg_inference.model.strict_load=true
```

## Summary

**Input**: Database records or query results  
**Output**: Segmentation masks + metadata  
**Time**: ~1 second per image (GPU-dependent)  
**Next Steps**: Upload to CVAT or use for analysis