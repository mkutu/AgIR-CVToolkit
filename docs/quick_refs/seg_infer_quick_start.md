# CVAT Upload - Quick Reference

## Overview

The CVAT upload stage uploads images and masks to CVAT for human refinement. It creates CVAT tasks with pre-populated annotations that annotators can review and correct.

**Key Features**:
- Automatic task creation
- Pre-labeled annotations from segmentation results
- Frame-image alignment guarantees
- Support for both segmentations and detections
- Project integration

## Quick Start

### Basic Upload (After Inference)

```bash
# 1. Run inference with images saved
agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true

# 2. Upload to CVAT
agir-cvtoolkit upload-cvat
```

### Upload to Existing Project

```bash
agir-cvtoolkit upload-cvat \
  -o cvat_upload.project_id=319384 \
  -o cvat_upload.organization_slug=PSA
```

## Configuration

### Basic Settings

```yaml
# conf/cvat_upload/default.yaml
project_id: 319384  # Existing project (inherits labels)
organization_slug: PSA

task_name: null  # Auto-generated from run_id

labels:  # Only used if NOT in a project
  - "weed"

mask_strategy: "mask"  # "mask" | "polygon"
```

### Source Configuration

```yaml
source:
  type: "segmentations"  # "segmentations" | "detections"
  db: "semif"
```

### Label Mapping

```yaml
label_map:
  # Map database fields to CVAT labels
  category_common_name: "{value}"  # Use field value as label
  # OR
  _default: "weed"  # All images get this label
```

## Common Use Cases

### Case 1: Standard Segmentation Upload

```bash
# Complete pipeline
agir-cvtoolkit query --db semif --filters "state=NC" --limit 100
agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true
agir-cvtoolkit upload-cvat
```

### Case 2: Upload to Specific Project

```bash
agir-cvtoolkit upload-cvat \
  -o cvat_upload.project_id=12345 \
  -o cvat_upload.organization_slug=my-org
```

### Case 3: Custom Task Name

```bash
agir-cvtoolkit upload-cvat \
  -o cvat_upload.task_name="Barley_Batch_2024-11"
```

### Case 4: Detection Upload (Bounding Boxes)

```bash
# Upload detection boxes instead of masks
agir-cvtoolkit upload-cvat \
  -o cvat_upload.source.type=detections
```

## Data Source

### Segmentation Results

Upload requires:
- `manifest.jsonl` from inference stage
- Images in `run_root/images/`
- Masks in `run_root/masks/`

```yaml
source:
  type: "segmentations"
  db: "semif"  # For metadata
```

### Detection Results

Upload requires:
- `query.json` or `query.csv` with bbox coordinates
- Images accessible via database paths

```yaml
source:
  type: "detections"
  db: "semif"
```

## Label Mapping

### Use Database Values

```yaml
label_map:
  category_common_name: "{value}"
```

Maps each record's `category_common_name` to a CVAT label.

### Fixed Label

```yaml
label_map:
  _default: "weed"
```

All uploads get the same label.

### Mixed Mapping

```yaml
label_map:
  category_common_name: "{value}"
  _default: "unknown"
```

Uses `category_common_name` if present, else "unknown".

## Project vs Standalone Tasks

### With Project (Recommended)

```yaml
project_id: 319384
```

**Benefits**:
- Inherits labels from project
- Organized under one project
- Shared annotation settings

### Standalone Task

```yaml
project_id: null
labels:
  - "barley"
  - "wheat"
  - "hairy_vetch"
```

**Use when**: Testing or one-off annotations

## Output & Metrics

### Task Created

Upload creates a CVAT task and saves metrics:

```json
{
  "total_records": 100,
  "uploaded_annotations": 98,
  "skipped": 1,
  "failed": 1,
  "task_id": 54321,
  "task_url": "https://app.cvat.ai/tasks/54321"
}
```

### Task URL

The task URL is printed at completion:
```
Task URL: https://app.cvat.ai/tasks/54321
```

## Credentials

### Setup Keys File

Create `.keys/default.yaml`:

```yaml
cvat:
  url: "https://app.cvat.ai"
  username: "your_username"
  password: "your_password"
```

### Self-Hosted CVAT

```yaml
cvat:
  url: "http://localhost:8080"
  username: "admin"
  password: "admin123"
```

## Troubleshooting

### Authentication Failed

**Problem**: Cannot connect to CVAT

**Solutions**:
1. Check credentials in `.keys/default.yaml`
2. Verify URL is correct (https vs http)
3. Test login in CVAT web interface

### Images Not Found

**Problem**: "Could not load image for record"

**Solutions**:
```bash
# Ensure inference saved images
agir-cvtoolkit infer-seg \
  -o seg_inference.output.save_images=true
```

### Project Not Found

**Problem**: "Project 12345 not found"

**Solutions**:
1. Verify project ID is correct
2. Check organization slug matches project
3. Verify account has access to project

### Label Not in Project

**Problem**: "Label 'barley' not in task"

**Solutions**:
1. Add label to project in CVAT
2. Update `label_map` to match project labels
3. Use `_default` label that exists

### Misaligned Frames

**Problem**: Images don't match annotations

**Solution**: This shouldn't happen - the pipeline guarantees alignment. If it does:
1. Check you didn't modify files between inference and upload
2. Verify manifest.jsonl exists and is complete
3. Re-run inference + upload

## Best Practices

1. **Always use projects** for organized annotation:
   ```bash
   -o cvat_upload.project_id=YOUR_PROJECT_ID
   ```

2. **Save images during inference**:
   ```bash
   -o seg_inference.output.save_images=true
   ```

3. **Use descriptive task names**:
   ```bash
   -o cvat_upload.task_name="Barley_NC_November_2024"
   ```

4. **Check metrics** after upload to verify success

5. **Keep manifest.jsonl** - don't delete between inference and upload

## Advanced Options

### Mask Strategy

```bash
# Use polygon format (works everywhere)
agir-cvtoolkit upload-cvat \
  -o cvat_upload.mask_strategy=polygon

# Use mask format (CVAT 2.0+, more accurate)
agir-cvtoolkit upload-cvat \
  -o cvat_upload.mask_strategy=mask
```

### Organization Context

```bash
# Upload to organization workspace
agir-cvtoolkit upload-cvat \
  -o cvat_upload.organization_slug=my-team

# Upload to personal workspace
agir-cvtoolkit upload-cvat \
  -o cvat_upload.organization_slug=null
```

## Integration with Pipeline

### Full Annotation Workflow

```bash
# 1. Query and infer
agir-cvtoolkit query --db semif \
  --sample "stratified:by=category_common_name,per_group=50"
agir-cvtoolkit infer-seg \
  -o seg_inference.output.save_images=true

# 2. Upload to CVAT
agir-cvtoolkit upload-cvat \
  -o cvat_upload.project_id=12345

# 3. [Annotators refine in CVAT web interface]

# 4. Download refined annotations
agir-cvtoolkit download-cvat \
  -o cvat_download.project_id=12345 \
  -o cvat_download.required_status=completed

# 5. Train on refined data
agir-cvtoolkit preprocess
agir-cvtoolkit train
```

### Iterative Improvement

```bash
# Round 1: Initial masks
agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true
agir-cvtoolkit upload-cvat -o cvat_upload.task_name="Round1_Barley"

# [Refine in CVAT]
agir-cvtoolkit download-cvat
agir-cvtoolkit train

# Round 2: Improved model
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=outputs/.../model/best.pth \
  -o seg_inference.output.save_images=true
agir-cvtoolkit upload-cvat -o cvat_upload.task_name="Round2_Barley"
```

## Quick Tips

✅ **Use projects** for better organization

✅ **Save images** during inference (required for upload)

✅ **Check task URL** in output to access in CVAT

✅ **Verify metrics** to catch failed uploads

✅ **Keep manifest.jsonl** - it ensures alignment

✅ **Test with small dataset** before large uploads

## Validation

The upload stage performs automatic validation:

- ✓ All images exist
- ✓ All masks exist (for segmentations)
- ✓ Frame order matches record order
- ✓ Labels exist in project
- ✓ Masks are valid format

Failed items are logged and counted in metrics.

## Performance

**Typical upload speed**:
- ~2-5 seconds per image
- Network-dependent
- Batch size: Processes all at once

**For large datasets**:
- Split into multiple smaller tasks
- Upload in batches
- Monitor network connection

## Summary

**Input**: Inference results (images + masks)  
**Output**: CVAT task with pre-labeled annotations  
**Time**: ~5 seconds per image  
**Next Steps**: Refine in CVAT web interface