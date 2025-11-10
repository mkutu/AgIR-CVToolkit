# Image Resolution Guide

## Overview

When downloading annotations from CVAT, you often download **masks only** (not images) to save bandwidth and storage. The preprocessing stage now includes an **image resolution** step that automatically finds and organizes the corresponding images from multiple sources.

## How It Works

### Resolution Process

For each mask file, the system searches for the corresponding image in this order:

1. **run_root/images/** - Images from previous inference runs
2. **cvat_downloads/<task>/images/** - Images included in CVAT download
3. **Database query** - Queries the database using the cutout_id extracted from the mask filename

### Cutout ID Extraction

The system extracts cutout IDs from mask filenames using these patterns:

- `<task_name>_<cutout_id>.png` (aggregated tasks)
- `<cutout_id>_mask.png` (standard format)
- `<cutout_id>.png` (simple format)

Example: `barley_task_IMG_20240515_123456.png` → cutout_id: `IMG_20240515_123456`

### Database Resolution

When images aren't found locally:

1. Queries the database using the cutout_id
2. Finds the image path on NFS/LTS storage
3. Copies image to `run_root/resolved_images/`
4. Applies bounding box crop if needed (for full images)

### Output Manifest

Creates `image_mask_manifest.txt` with paired locations:

```
/path/to/image1.jpg,/path/to/mask1.png
/path/to/image2.jpg,/path/to/mask2.png
...
```

## Configuration

### Enable/Disable Image Resolution

```yaml
# conf/preprocess/default.yaml
resolve_images:
  enabled: true  # Set to false to skip image resolution
```

### Specify Database for Resolution

```yaml
source:
  type: "cvat_download"
  db: "semif"  # "semif" | "field" | null
```

Set `db: null` if you don't want database lookups (local files only).

## Usage Examples

### Example 1: CVAT Download with Masks Only

```bash
# 1. Download masks only from CVAT (save bandwidth)
agir-cvtoolkit download-cvat \
  -o cvat_download.include_images=false \
  -o cvat_download.dataset_format="Segmentation mask 1.1"

# 2. Preprocess - automatically resolves images
agir-cvtoolkit preprocess
```

The preprocessing will:
- Find masks in `cvat_downloads/<task>/annotations/`
- Check if images are in `run_root/images/` (from prior inference)
- If not found, query database and download to `resolved_images/`
- Create manifest at `run_root/image_mask_manifest.txt`

### Example 2: Multiple CVAT Tasks

```bash
# 1. Download multiple tasks (masks only)
agir-cvtoolkit download-cvat \
  -o cvat_download.task_ids=[101,102,103] \
  -o cvat_download.include_images=false

# 2. Preprocess - resolves images for all tasks
agir-cvtoolkit preprocess
```

The system automatically:
- Aggregates masks from all tasks
- Extracts task names from filenames
- Resolves images for each mask
- Creates unified manifest

### Example 3: Using Inference Results

If you already ran inference and have images:

```bash
# 1. Run inference (creates run_root/images/)
agir-cvtoolkit query --db semif --filters "state=NC"
agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true

# 2. Download refined masks from CVAT
agir-cvtoolkit download-cvat -o cvat_download.include_images=false

# 3. Preprocess - finds images in run_root/images/
agir-cvtoolkit preprocess
```

Resolution will find images in `run_root/images/` (fast, no database query needed).

### Example 4: Disable Database Queries

```bash
# Only use local images (no database lookups)
agir-cvtoolkit preprocess \
  -o preprocess.source.db=null
```

## Output Structure

After preprocessing with image resolution:

```
outputs/runs/{run_id}/
├── cvat_downloads/          # Downloaded CVAT tasks
│   ├── barley_task/
│   │   └── annotations/     # Masks only
│   └── wheat_task/
│       └── annotations/
├── images/                  # From inference (if present)
├── resolved_images/         # Downloaded from database
│   ├── IMG_001.jpg
│   └── IMG_002.jpg
├── image_mask_manifest.txt  # ← NEW: Paired locations
├── combined/                # Aggregated from tasks
│   ├── images/
│   └── masks/
├── preprocessed/            # Standardized sizes
├── train/                   # Split datasets
├── val/
└── test/
```

## Metrics

The preprocessing metrics include image resolution statistics:

```json
{
  "source_images": 150,
  "resolved_images": 145,
  "resolution_stats": {
    "total_masks": 150,
    "found_in_run_images": 80,
    "found_in_cvat": 20,
    "found_in_db": 45,
    "copied_from_db": 45,
    "not_found": 5
  }
}
```

## Troubleshooting

### Missing Images

**Problem**: Some images not resolved (not_found > 0)

**Solutions**:
1. Check cutout_id extraction: Look at mask filenames and verify IDs are correct
2. Verify database connectivity: Ensure database path is correct in config
3. Check database records: Query database directly to verify records exist
4. Manual resolution: Add missing images to `run_root/images/`

### Incorrect Cutout IDs

**Problem**: Cutout IDs extracted incorrectly from filenames

**Solution**: Rename mask files to standard format:
- `<cutout_id>.png`
- `<cutout_id>_mask.png`

### Slow Database Queries

**Problem**: Image resolution is very slow

**Solutions**:
1. Pre-populate `run_root/images/`: Run inference first to save images
2. Include images in CVAT download: Set `cvat_download.include_images=true`
3. Use local copies: Copy images from NFS to local disk first

### Database Connection Errors

**Problem**: Cannot connect to database

**Solutions**:
1. Check database path in `conf/db/default.yaml`
2. Verify database file exists
3. Set `preprocess.source.db=null` to skip database resolution

## Best Practices

1. **Run inference first** if possible - saves database queries:
   ```bash
   agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true
   agir-cvtoolkit upload-cvat
   # [Refine in CVAT]
   agir-cvtoolkit download-cvat -o cvat_download.include_images=false
   agir-cvtoolkit preprocess  # Fast: finds images in run_root/images/
   ```

2. **Use consistent naming** - Keep cutout_ids in mask filenames

3. **Check metrics** - Review resolution stats after preprocessing

4. **Verify manifest** - Spot-check `image_mask_manifest.txt` before training

5. **Clean up** - Remove `resolved_images/` after training to save space

## Integration with Training

The manifest file is automatically used by the training data loader:

```bash
# Preprocess creates manifest
agir-cvtoolkit preprocess

# Training uses manifest (automatic)
agir-cvtoolkit train

# Or train with auto-preprocessing
agir-cvtoolkit train -o train.auto_preprocess=true
```

## Advanced: Custom Image Sources

To add custom image resolution logic, extend the `ImageResolver` class:

```python
from agir_cvtoolkit.pipelines.utils.image_resolver import ImageResolver

class CustomResolver(ImageResolver):
    def find_image_in_custom_location(self, cutout_id: str):
        # Add your custom logic here
        pass
```

## Summary

The image resolution feature:

✅ **Automatic** - No manual image organization needed  
✅ **Multi-source** - Checks local, CVAT, and database  
✅ **Efficient** - Database queries only when necessary  
✅ **Transparent** - Detailed metrics and logging  
✅ **Integrated** - Works seamlessly with existing pipeline  

This enables a streamlined workflow:
1. Download masks from CVAT (lightweight)
2. Preprocess automatically resolves images
3. Train with organized, paired data