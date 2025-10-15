# Preprocessing Pipeline Usage Guide

## Overview

The preprocessing pipeline prepares training data by:
1. **Standardizing sizes** via pad/grid-crop/resize
2. **Splitting** into train/val/test sets
3. **Computing statistics** for normalization

## Quick Start

### Automatic Preprocessing (Recommended)

The simplest way is to let training automatically preprocess data:

```bash
# 1. Download CVAT annotations
agir-cvtoolkit download-cvat -o cvat_download.project_id=12345

# 2. Train (preprocessing runs automatically)
agir-cvtoolkit train
```

Training will automatically:
- Find CVAT downloaded data
- Preprocess images/masks
- Split into train/val/test
- Compute normalization statistics
- Start training

### Manual Preprocessing

For more control, run preprocessing separately:

```bash
# 1. Download CVAT annotations
agir-cvtoolkit download-cvat -o cvat_download.project_id=12345

# 2. Run preprocessing
agir-cvtoolkit preprocess

# 3. Train using preprocessed data
agir-cvtoolkit train -o train.auto_preprocess=false
```

## Configuration

### Basic Preprocessing Config

Edit `conf/preprocess/default.yaml`:

```yaml
# Source of data
source:
  type: "cvat_download"  # or "custom"

# Standardize image sizes
pad_gridcrop_resize:
  enabled: true
  size:
    height: 2048
    width: 2048
  
  pad:
    enabled: true
    fill: 0  # Black padding
  
  grid_crop:
    enabled: true
    stride: 512
    threshold: 2.5  # Crop if >2.5x target size
  
  resize:
    enabled: true
    interpolation:
      image: BILINEAR
      mask: NEAREST

# Train/val/test split
split:
  enabled: true
  train: 0.8
  val: 0.15
  test: 0.05

# Compute normalization stats
compute_data_stats:
  enabled: true
```

### Training Config

Edit `conf/train/default.yaml`:

```yaml
# Auto-run preprocessing before training
auto_preprocess: true

# Data paths (set automatically if auto_preprocess=true)
train_images_dir: ${paths.run_root}/train/images
train_masks_dir: ${paths.run_root}/train/masks
val_images_dir: ${paths.run_root}/val/images
val_masks_dir: ${paths.run_root}/val/masks
```

## Common Use Cases

### 1. Standard Training Workflow

Download from CVAT and train with automatic preprocessing:

```bash
# Download refined annotations
agir-cvtoolkit download-cvat \
  -o cvat_download.project_id=12345 \
  -o cvat_download.required_status=completed

# Train (preprocessing happens automatically)
agir-cvtoolkit train \
  -o train.max_epochs=50 \
  -o train.batch_size=8
```

### 2. Custom Image Size

Train with 1024x1024 images instead of default 2048x2048:

```bash
agir-cvtoolkit train \
  -o preprocess.pad_gridcrop_resize.size.height=1024 \
  -o preprocess.pad_gridcrop_resize.size.width=1024
```

### 3. Different Train/Val Split

Use 90% train, 10% val (no test set):

```bash
agir-cvtoolkit preprocess \
  -o preprocess.split.train=0.9 \
  -o preprocess.split.val=0.1 \
  -o preprocess.split.test=0.0
```

### 4. Custom Data Source

Preprocess from custom directories instead of CVAT:

```bash
agir-cvtoolkit preprocess \
  -o preprocess.source.type=custom \
  -o preprocess.source.custom_images_dir=/path/to/images \
  -o preprocess.source.custom_masks_dir=/path/to/masks
```

### 5. Skip Preprocessing

Train using pre-existing preprocessed data:

```bash
agir-cvtoolkit train -o train.auto_preprocess=false
```

### 6. Fast Preprocessing (No Grid Crop)

For smaller images, disable grid cropping:

```bash
agir-cvtoolkit preprocess \
  -o preprocess.pad_gridcrop_resize.grid_crop.enabled=false
```

## Understanding Preprocessing Steps

### Step 1: Pad/Grid-Crop/Resize

This standardizes all images to a fixed size (default 2048x2048):

**Small images (< target):**
- Padded to target size with black borders

**Large images (> 2.5× target):**
- Grid-cropped into overlapping tiles
- Creates multiple training samples from one image
- Useful for very large images

**Medium images (between target and 2.5× target):**
- Resized to fit in target dimensions
- Padded to exact target size
- Preserves aspect ratio

**Example:**
```
Input: 1500x1000 image
↓ Resize to fit 2048x2048 → 2048x1365
↓ Pad to exact size → 2048x2048
```

### Step 2: Train/Val/Test Split

Splits preprocessed data into three sets:

- **Train (80%):** For model training
- **Val (15%):** For validation during training
- **Test (5%):** For final evaluation

**Note:** Split is deterministic based on seed for reproducibility.

### Step 3: Compute Dataset Statistics

Computes RGB mean and std across all training images:

- Used for normalization during training
- Improves model convergence
- Saved to `datastats/rgb_mean_std.json`

**Example output:**
```json
{
  "mean": [0.414023, 0.397339, 0.307019],
  "std": [0.164442, 0.144112, 0.147795]
}
```

## Output Structure

After preprocessing, your run folder contains:

```
outputs/runs/{run_id}/
├── cvat_downloads/       # Downloaded CVAT data
│   └── task_name/
│       ├── images/
│       └── annotations/
├── preprocessed/         # Standardized images
│   ├── images/
│   └── masks/
├── train/               # Training set
│   ├── images/
│   └── masks/
├── val/                 # Validation set
│   ├── images/
│   └── masks/
├── test/                # Test set
│   ├── images/
│   └── masks/
└── datastats/           # Normalization stats
    └── rgb_mean_std.json
```

## Performance Tuning

### Enable Multiprocessing

Speed up preprocessing with parallel workers:

```bash
agir-cvtoolkit preprocess \
  -o preprocess.pad_gridcrop_resize.use_concurrency=true \
  -o preprocess.pad_gridcrop_resize.num_workers=16
```

### Disk Space Management

Remove source files after processing to save disk space:

```bash
agir-cvtoolkit preprocess \
  -o preprocess.pad_gridcrop_resize.remove_src=true \
  -o preprocess.split.remove_src=true
```

**Warning:** Only enable `remove_src` if you have backups!

### Skip Empty Images

Ignore images with no annotations:

```bash
agir-cvtoolkit preprocess \
  -o preprocess.pad_gridcrop_resize.ignore_empty_data=true
```

## Troubleshooting

### "CVAT downloads directory not found"

**Cause:** Haven't downloaded CVAT data yet.

**Solution:**
```bash
agir-cvtoolkit download-cvat -o cvat_download.project_id=YOUR_PROJECT_ID
```

### "Train images directory is empty"

**Cause:** Preprocessing hasn't run yet.

**Solutions:**
1. Enable auto-preprocessing: `train.auto_preprocess=true` (default)
2. Run manually: `agir-cvtoolkit preprocess` before training

### "No mask found for image"

**Cause:** CVAT export format doesn't include masks.

**Solution:** Re-download with mask format:
```bash
agir-cvtoolkit download-cvat \
  -o cvat_download.dataset_format="Segmentation mask 1.1"
```

### Out of Memory During Preprocessing

**Solution:** Reduce number of workers:
```bash
agir-cvtoolkit preprocess \
  -o preprocess.pad_gridcrop_resize.num_workers=4
```

## Best Practices

1. **Always use version control** for your config files
2. **Keep CVAT downloads** as backups (don't enable `remove_src` on first run)
3. **Test preprocessing** on a small subset first
4. **Use same image size** for training and inference
5. **Document your preprocessing** settings for reproducibility
6. **Compute statistics** on train set only (never val/test)

## Integration with Full Pipeline

Complete training workflow:

```bash
# 1. Query and segment images
agir-cvtoolkit query --db semif --sample "stratified:by=common_name,per_group=100"
agir-cvtoolkit infer-seg

# 2. Upload to CVAT for refinement
agir-cvtoolkit upload-cvat

# [Manual: Refine masks in CVAT]

# 3. Download refined masks
agir-cvtoolkit download-cvat -o cvat_download.required_status=completed

# 4. Train (preprocessing automatic)
agir-cvtoolkit train -o train.max_epochs=100

# 5. Use trained model for new inference
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=outputs/runs/train_xxx/model/best.pth
```