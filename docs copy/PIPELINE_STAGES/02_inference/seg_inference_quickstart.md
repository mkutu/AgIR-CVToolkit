# Segmentation Inference - Quick Reference

## Overview

The segmentation inference stage runs trained models on images to generate masks. It supports:
- **Tiled inference** for large images
- **Multiple model architectures** (Unet, DeepLabV3+, Segformer)
- **Full image or cutout modes** - inference on complete images or cropped cutouts
- **Colorized masks** - species-specific color-coded outputs
- **RGBA transparent cutouts** - clean cutouts with transparent backgrounds
- **Post-processing** (thresholding, edge occupancy filtering)
- **Batch processing** with progress tracking

## Quick Start

### Basic Usage

```bash
# Run inference using previous query results
agir-cv query --db semif --filters "state=NC" --limit 100
agir-cv infer-seg
```

### With Custom Model

```bash
# Use specific checkpoint
agir-cv infer-seg \
  -o seg_inference.model.ckpt_path=/path/to/model.ckpt
```

### NEW: Full Image Mode

```bash
# Inference on complete images (not cutouts)
agir-cv infer-seg \
  -o seg_inference.source.image_mode=full_image
```

### NEW: Colorized Masks

```bash
# Generate color-coded masks using database RGB values
agir-cv infer-seg \
  -o seg_inference.output.save_colorized_masks=true \
  -o seg_inference.output.colorize_brightness=6.5
```

### NEW: RGBA Transparent Cutouts

```bash
# Save cutouts with transparent backgrounds
agir-cv infer-seg \
  -o seg_inference.output.save_cutouts=true \
  -o seg_inference.output.cutout_rgba_transparent=true
```

## Configuration

### Source Settings

```yaml
# conf/seg_inference/default.yaml
source:
  type: "query_result"  # "query_result" | "db_query"
  db: "semif"
  image_mode: "cutout"  # NEW: "cutout" | "full_image"
```

**Image modes:**
- `cutout`: Load pre-cropped cutouts or apply bbox cropping (default)
- `full_image`: Load complete images, ignore bbox and cropout_path

### Model Settings

```yaml
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

### Output Settings

```yaml
output:
  save_masks: true
  save_images: true
  save_cutouts: false
  save_viz: false
  
  # NEW: Cutout options
  cutout_rgba_transparent: false  # Save as RGBA with transparency
  
  # NEW: Colorization options
  save_colorized_masks: false     # Enable colorization
  colorize_brightness: 6.5        # Brightness factor (1.0-15.0)
  colorize_rgb_field: "category_rgb"  # Database RGB field
  colorize_fallback_rgb: [0, 255, 0]  # Fallback color
```

### Post-Processing

```yaml
post_process:
  threshold: 0.5
  min_area: 0  # Remove components smaller than this
  edge_occupancy_threshold: null  # Skip if edge > threshold
```

## Common Use Cases

### Case 1: Standard Pipeline (Cutouts)

```bash
# 1. Query images
agir-cv query --db semif \
  --filters "category_common_name=barley" \
  --sample "stratified:by=area_bin,per_group=50"

# 2. Run inference (auto-finds query results)
agir-cv infer-seg

# 3. Upload to CVAT for refinement
agir-cv upload-cvat
```

### Case 2: Full Image Scene Analysis

```bash
# Inference on complete field images
agir-cv query --db semif \
  --filters "state=NC" \
  --limit 50

agir-cv infer-seg \
  -o seg_inference.source.image_mode=full_image \
  -o seg_inference.output.save_images=true \
  -o seg_inference.output.save_visualizations=true
```

### Case 3: Multi-Species Colorization

```bash
# Color-code different species
agir-cv query --db semif \
  --filters "category_common_name=barley,wheat,hairy vetch" \
  --sample "stratified:by=category_common_name,per_group=30"

agir-cv infer-seg \
  -o seg_inference.output.save_masks=true \
  -o seg_inference.output.save_colorized_masks=true
```

### Case 4: Transparent Cutouts for Graphics

```bash
# Generate cutouts with transparent backgrounds
agir-cv infer-seg \
  -o seg_inference.output.save_cutouts=true \
  -o seg_inference.output.cutout_rgba_transparent=true \
  -o seg_inference.output.save_images=true
```

### Case 5: All Features Combined

```bash
# Full image + colorization + RGBA cutouts
agir-cv infer-seg \
  -o seg_inference.source.image_mode=full_image \
  -o seg_inference.output.save_masks=true \
  -o seg_inference.output.save_colorized_masks=true \
  -o seg_inference.output.save_cutouts=true \
  -o seg_inference.output.cutout_rgba_transparent=true \
  -o seg_inference.output.save_images=true
```

### Case 6: Fresh Database Query

```bash
# Run inference directly from database (no prior query stage)
agir-cv infer-seg \
  -o seg_inference.source.type=db_query \
  -o seg_inference.source.filters.state=NC \
  -o seg_inference.source.limit=100
```

### Case 7: Filter by Edge Occupancy

```bash
# Skip objects touching image edges
agir-cv infer-seg \
  -o seg_inference.post_process.edge_occupancy_threshold=0.3
```

## Output Structure

```
outputs/runs/{run_id}/
├── masks/                    # Grayscale masks (binary/8-bit)
│   ├── IMG_001.png
│   └── IMG_002.png
├── colorized_masks/          # NEW: RGB colorized masks
│   ├── IMG_001.png
│   └── IMG_002.png
├── images/                   # Source images (if save_images=true)
│   ├── IMG_001.jpg
│   └── IMG_002.jpg
├── cutouts/                  # Masked cutouts (RGB or RGBA)
│   └── IMG_001.png
├── plots/                    # Visualizations (if save_visualizations=true)
│   └── IMG_001_viz.png
├── manifest.jsonl            # Enhanced metadata
└── metrics.json              # Performance statistics
```

### Manifest Fields

```json
{
  "record_id": "IMG_001",
  "image_mode": "full_image",
  "common_name": "barley",
  "image_path": "outputs/runs/xxx/images/IMG_001.jpg",
  "mask_path": "outputs/runs/xxx/masks/IMG_001.png",
  "colorized_mask_path": "outputs/runs/xxx/colorized_masks/IMG_001.png",
  "cutout_path": "outputs/runs/xxx/cutouts/IMG_001.png",
  "cutout_rgba": true,
  "rgb_value": "[76, 142, 34]",
  "inference_time_ms": 4523,
  "edge_occupancy": 0.125,
  "image_shape": [4000, 6000, 3],
  "mask_shape": [4000, 6000]
}
```

## Data Sources

### From Previous Query

```bash
# Default: uses results from previous query stage
agir-cv query --db semif --filters "state=NC"
agir-cv infer-seg  # Reads from outputs/runs/{run_id}/query/
```

### Direct Database Query

```yaml
source:
  type: "db_query"
  db: "semif"
  image_mode: "cutout"  # or "full_image"
  
  filters:
    state: "NC"
    category_common_name: ["barley", "wheat"]
  
  sample:
    strategy: "stratified"
    by: ["category_common_name"]
    per_group: 10
  
  limit: 1000
```

## Image Mode Comparison

| Aspect | `cutout` Mode | `full_image` Mode |
|--------|---------------|-------------------|
| **Input** | Cropout or bbox-cropped region | Full resolution image |
| **Size** | 200-2000px typical | 4000-8000px typical |
| **Use Case** | Individual plant analysis | Scene-level segmentation |
| **Speed** | Faster (~0.5-1s) | Slower (~3-10s) |
| **Requires bbox** | Yes (unless cropout exists) | No |
| **Output size** | Matches cutout | Matches full image |

## Colorization Options

### Brightness Levels

| Brightness | Effect | Use Case |
|-----------|--------|----------|
| 1.0 | No enhancement | Scientific accuracy |
| 3.0-5.0 | Subtle brightening | General use |
| 6.5 | Default | Good for most cases |
| 10.0-15.0 | Very bright | Presentations |

### RGB Field Priority

The system searches for RGB values in this order:
1. `colorize_rgb_field` (configured field, e.g., `category_rgb`)
2. `category_rgb` (fallback)
3. `rgb` (fallback)
4. `category_hex` (fallback, converted to RGB)
5. `colorize_fallback_rgb` (final fallback)

### RGB Format Support

Handles multiple formats automatically:
- Normalized: `"[0.3, 0.5, 0.2]"` → scales to [76, 127, 51]
- Absolute: `"[76, 142, 34]"` → used directly
- List/Tuple: `[0.3, 0.5, 0.2]` or `[76, 142, 34]`

## Cutout Format Comparison

| Format | Background | Channels | Use Case | File Size |
|--------|-----------|----------|----------|-----------|
| **RGB** (default) | Black | 3 | Analysis, when black OK | ~200KB |
| **RGBA** (new) | Transparent | 4 | Overlays, compositing | ~250KB |

## GPU Configuration

### Select Specific GPUs

```bash
# Use 2 GPUs, excluding GPU 0
agir-cv infer-seg \
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
agir-cv infer-seg \
  -o seg_inference.tile.height=512 \
  -o seg_inference.tile.width=512

# Use CPU
agir-cv infer-seg \
  -o seg_inference.gpu.max_gpus=0

# For full images: use smaller tiles
agir-cv infer-seg \
  -o seg_inference.source.image_mode=full_image \
  -o seg_inference.tile.height=512 \
  -o seg_inference.tile.width=512
```

### Slow Inference

**Problem**: Processing is very slow

**Solutions**:
1. Check GPU utilization: `nvidia-smi`
2. Increase tile size if GPU has memory
3. Verify model is on GPU (check logs)
4. For full images: expect 3-10x longer processing time

### Image Not Found

**Problem**: "Could not load image for record"

**Solutions**:
1. Check database paths are mounted correctly
2. Verify `root_map` in `conf/db/default.yaml`
3. Check file permissions on NFS/LTS storage
4. For `full_image` mode: ensure records have `image_path` field

### Empty Masks

**Problem**: All masks are empty/black

**Solutions**:
1. Check model checkpoint path is correct
2. Verify normalization parameters match training
3. Adjust threshold: `-o seg_inference.post_process.threshold=0.3`

### Colorization Issues

**Problem**: All masks are green/same color

**Solutions**:
```bash
# Check what RGB field exists in database
agir-cv query --db semif --out csv --limit 1

# Specify correct field
agir-cv infer-seg \
  -o seg_inference.output.save_colorized_masks=true \
  -o seg_inference.output.colorize_rgb_field=rgb

# Set custom fallback color
-o seg_inference.output.colorize_fallback_rgb=[255,0,0]
```

**Problem**: Masks too dark

**Solution**:
```bash
# Increase brightness
-o seg_inference.output.colorize_brightness=10.0
```

### RGBA Issues

**Problem**: Cutouts have black background instead of transparent

**Solution**:
```bash
# Both flags required
-o seg_inference.output.save_cutouts=true \
-o seg_inference.output.cutout_rgba_transparent=true
```

**Problem**: Can't verify transparency

**Solution**:
```python
# Check in Python
from PIL import Image
img = Image.open("cutout.png")
print(f"Mode: {img.mode}")  # Should be "RGBA"
print(f"Alpha range: {img.getchannel('A').getextrema()}")
```

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

### Performance Impact

| Feature | Time/Image | Storage/File | Memory |
|---------|-----------|--------------|--------|
| Cutout inference | 0.5-1s | 200KB mask | 50MB |
| Full image | 3-10s | 5-10MB mask | 200-500MB |
| Colorization | +10-50ms | +3x mask size | Minimal |
| RGBA cutouts | +1-2ms | +25% cutout size | Minimal |

## Integration with Pipeline

### Full Workflow

```bash
# 1. Query database
agir-cv query --db semif \
  --sample "stratified:by=category_common_name,per_group=100"

# 2. Generate masks (with new features)
agir-cv infer-seg \
  -o seg_inference.output.save_images=true \
  -o seg_inference.output.save_colorized_masks=true

# 3. Upload to CVAT
agir-cv upload-cvat

# 4. [Manually refine in CVAT]

# 5. Download refined masks
agir-cv download-cvat

# 6. Preprocess for training
agir-cv preprocess

# 7. Train improved model
agir-cv train

# 8. Use new model for inference
agir-cv infer-seg \
  -o seg_inference.model.ckpt_path=outputs/runs/train_xxx/model/best.pth
```

### Workflow: Presentation Graphics

```bash
# Generate colorized masks and transparent cutouts
agir-cv query --db semif --limit 50

agir-cv infer-seg \
  -o seg_inference.output.save_colorized_masks=true \
  -o seg_inference.output.colorize_brightness=10.0 \
  -o seg_inference.output.save_cutouts=true \
  -o seg_inference.output.cutout_rgba_transparent=true

# Use outputs in presentations/web graphics
```

### Workflow: Field-Level Analysis

```bash
# Full image inference for scene analysis
agir-cv query --db field --limit 25

agir-cv infer-seg \
  -o seg_inference.source.image_mode=full_image \
  -o seg_inference.output.save_images=true \
  -o seg_inference.output.save_visualizations=true
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

6. **Start small for new features** - test with limit=5-10 first

7. **Use appropriate image mode**:
   - `cutout`: For training data, individual plant analysis
   - `full_image`: For scene analysis, when no bbox available

8. **Adjust brightness for use case**:
   - Scientific: 1.0-3.0
   - General: 5.0-7.0
   - Presentations: 8.0-12.0

9. **Choose cutout format wisely**:
   - RGB: Analysis, when black background is acceptable
   - RGBA: Overlays, compositing, web graphics

## Quick Tips

✅ **Tile overlap prevents seams** - use 0.5 for smooth masks

✅ **Save normalization stats** from training for inference

✅ **Check logs** for detailed processing info

✅ **Use manifest** to track which images were processed

✅ **Enable visualizations** during development to debug issues

✅ **Full images require more memory** - adjust tile size accordingly

✅ **Colorized masks are for visualization** - CVAT uses grayscale

✅ **RGBA adds ~25% storage** - use only when transparency needed

✅ **Test features individually** before combining

✅ **Database RGB values vary** - check your data first

## Advanced Options

### Custom Normalization

```bash
agir-cv infer-seg \
  -o seg_inference.model.normalization.mean=[0.5,0.5,0.5] \
  -o seg_inference.model.normalization.std=[0.25,0.25,0.25]
```

### Enable Visualizations

```bash
agir-cv infer-seg \
  -o seg_inference.output.save_visualizations=true \
  -o seg_inference.visualization.enabled=true
```

### Custom Colorization

```bash
# Use specific RGB field
agir-cv infer-seg \
  -o seg_inference.output.save_colorized_masks=true \
  -o seg_inference.output.colorize_rgb_field=rgb \
  -o seg_inference.output.colorize_fallback_rgb=[255,100,50]
```

### Strict Model Loading

```bash
# Require exact parameter match when loading checkpoint
agir-cv infer-seg \
  -o seg_inference.model.strict_load=true
```

### Full Image with Optimized Tiles

```bash
# Large tiles for GPUs with memory
agir-cv infer-seg \
  -o seg_inference.source.image_mode=full_image \
  -o seg_inference.tile.height=2048 \
  -o seg_inference.tile.width=2048
```

## Feature Compatibility

| Feature Combination | Compatible | Notes |
|---------------------|-----------|-------|
| Cutout + Colorization | ✅ | Standard use |
| Cutout + RGBA | ✅ | Transparent cutouts |
| Full Image + Colorization | ✅ | Scene-level colored masks |
| Full Image + RGBA | ✅ | Large transparent cutouts |
| All features | ✅ | Full feature set |
| RGBA without save_cutouts | ❌ | Must enable cutouts |
| Colorization without save_masks | ❌ | Must enable masks |

## Summary

**Input**: Database records or query results  
**Output**: Segmentation masks + optional colorized/RGBA outputs + metadata  
**Time**: ~1 second per cutout, ~3-10 seconds per full image (GPU-dependent)  

**New Capabilities**:
- 🖼️ Full image inference for scene-level analysis
- 🎨 Color-coded masks for species identification
- ✨ Transparent cutouts for overlays and graphics

**Next Steps**: Upload to CVAT, use for analysis, or create visualizations

## Quick Reference Commands

```bash
# Basic cutout inference (default)
agir-cv infer-seg

# Full image mode
agir-cv infer-seg -o seg_inference.source.image_mode=full_image

# Colorization
agir-cv infer-seg -o seg_inference.output.save_colorized_masks=true

# RGBA cutouts
agir-cv infer-seg \
  -o seg_inference.output.save_cutouts=true \
  -o seg_inference.output.cutout_rgba_transparent=true

# Everything
agir-cv infer-seg \
  -o seg_inference.source.image_mode=full_image \
  -o seg_inference.output.save_colorized_masks=true \
  -o seg_inference.output.save_cutouts=true \
  -o seg_inference.output.cutout_rgba_transparent=true
```