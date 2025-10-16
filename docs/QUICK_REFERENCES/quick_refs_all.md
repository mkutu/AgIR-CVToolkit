# AgIR-CVToolkit Pipeline Quick Reference

## Overview

The AgIR-CVToolkit pipeline consists of 5 main stages:

```
Query → Infer-Seg → Upload-CVAT → Download-CVAT → Preprocess → Train
```

---

## 1. Query Stage

**Purpose:** Query agricultural image databases and retrieve records for processing.

### Basic Usage

```bash
# Simple query
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --limit 100

# Balanced dataset (stratified sampling)
agir-cvtoolkit query --db semif \
  --sample "stratified:by=category_common_name,per_group=20" \
  --out csv
```

### Common Filters

```bash
# Single value
--filters "state=NC"

# Multiple values (OR)
--filters "category_common_name=barley,wheat,rye"

# Multiple filters (AND)
--filters "state=NC" --filters "category_common_name=barley"

# Range filters
--filters "estimated_bbox_area_cm2>=50"
--filters "estimated_bbox_area_cm2 between 50 and 200"
```

### Sampling Strategies

```bash
# Random sample
--sample "random:n=200"

# Seeded (reproducible)
--sample "seeded:n=200,seed=42"

# Stratified (balanced)
--sample "stratified:by=category_common_name,per_group=10"

# Multi-column stratified
--sample "stratified:by=category_common_name|area_bin,per_group=5"
```

### Output Options

```bash
# Output format
--out json    # Default
--out csv     # For Excel/pandas
--out parquet # For large datasets

# Column selection
--projection "cutout_id,category_common_name,estimated_bbox_area_cm2"

# Sorting
--sort "datetime:desc"
--sort "category_common_name:asc,estimated_bbox_area_cm2:desc"
```

### Output Location

```
outputs/runs/{run_id}/query/
├── query.csv          # Query results
└── query_spec.json    # Query parameters (for reproducibility)
```

### Reproduce a Query

```bash
# Show what was queried
python -m agir_cvtoolkit.pipelines.utils.query_utils summary \
  outputs/runs/{run_id}/query/query_spec.json

# Get reproduction command
python -m agir_cvtoolkit.pipelines.utils.query_utils reproduce \
  outputs/runs/{run_id}/query/query_spec.json
```

---

## 2. Infer-Seg Stage

**Purpose:** Run segmentation inference on queried images using trained models.

### Basic Usage

```bash
# Run inference (uses previous query results)
agir-cvtoolkit infer-seg

# Specify custom model checkpoint
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=/path/to/model.ckpt
```

### Key Configuration

```yaml
# Source (conf/seg_inference/default.yaml)
source:
  type: "query_result"  # Use previous query
  db: "semif"

# Model
model:
  arch: "unet"
  encoder_name: "mit_b0"
  ckpt_path: /path/to/checkpoint.ckpt

# GPU
gpu:
  max_gpus: 1
  exclude_ids: [0]

# Output
output:
  save_masks: true
  save_images: true
  save_cutouts: false
  save_visualizations: false
```

### Output Location

```
outputs/runs/{run_id}/
├── images/           # Source images
├── masks/            # Predicted masks (.png)
├── cutouts/          # Masked cutouts (optional)
├── plots/            # Visualizations (optional)
└── manifest.jsonl    # Image-mask pairs metadata
```

---

## 3. Upload-CVAT Stage

**Purpose:** Upload images and preliminary annotations to CVAT for human refinement.

### Basic Usage

```bash
# Upload segmentation masks
agir-cvtoolkit upload-cvat

# Upload to specific project
agir-cvtoolkit upload-cvat \
  -o cvat_upload.project_id=12345
```

### Key Configuration

```yaml
# conf/cvat_upload/default.yaml
project_id: 319384        # CVAT project ID
organization_slug: PSA    # Organization name

task_name: null           # Auto-generated if null
labels: ["weed"]          # Labels for task

source:
  type: "segmentations"   # or "detections"
  db: "semif"

mask_strategy: "mask"     # or "polygon"
```

### Output

- Creates CVAT task with images and annotations
- Task URL printed to console
- Metrics saved to `metrics.json`

---

## 4. Download-CVAT Stage

**Purpose:** Download refined annotations from CVAT after human review.

### Basic Usage

```bash
# Download all completed tasks
agir-cvtoolkit download-cvat

# Download specific tasks
agir-cvtoolkit download-cvat \
  -o cvat_download.task_ids=[101,102,103]

# Download from project
agir-cvtoolkit download-cvat \
  -o cvat_download.project_id=12345 \
  -o cvat_download.required_status=completed
```

### Key Configuration

```yaml
# conf/cvat_download/default.yaml
organization_slug: PSA
project_id: 318055        # null = all projects
task_ids: null            # null = all tasks
required_status: "completed"  # Filter by status

dataset_format: "CamVid 1.0"  # Export format
include_images: false     # Download images too?
check_image_exists: true  # Validate images exist
overwrite_existing: false # Re-download if exists
```

### Common Options

```bash
# Download masks only (save bandwidth)
-o cvat_download.include_images=false

# Different format
-o cvat_download.dataset_format="COCO 1.0"

# All tasks (any status)
-o cvat_download.required_status=null

# Force re-download
-o cvat_download.overwrite_existing=true
```

### Output Location

```
outputs/runs/{run_id}/cvat_downloads/
├── task_1/
│   ├── images/       # (if include_images=true)
│   └── annotations/  # Masks/annotations
├── task_2/
│   └── annotations/
└── task_3/
    └── annotations/
```

---

## 5. Preprocess Stage

**Purpose:** Prepare training data by aggregating tasks, resolving images, standardizing sizes, and splitting datasets.

### Basic Usage

```bash
# Automatic preprocessing (combines all CVAT tasks)
agir-cvtoolkit preprocess

# Preprocess specific tasks
agir-cvtoolkit preprocess \
  -o preprocess.source.tasks='["task_1","task_2"]'

# Custom image size
agir-cvtoolkit preprocess \
  -o preprocess.pad_gridcrop_resize.size.height=1024 \
  -o preprocess.pad_gridcrop_resize.size.width=1024
```

### Key Configuration

```yaml
# conf/preprocess/default.yaml

# Source
source:
  type: "cvat_download"
  tasks: null  # null = ALL tasks
  db: "semif"  # For image resolution

# Standardize sizes
pad_gridcrop_resize:
  enabled: true
  size:
    height: 2048
    width: 2048
  use_concurrency: true
  num_workers: 16

# Train/val/test split
split:
  enabled: true
  train: 0.8
  val: 0.15
  test: 0.05

# Dataset statistics
compute_data_stats:
  enabled: true
```

### What Preprocessing Does

1. **Task Aggregation** (if multiple tasks)
   - Combines images/masks from multiple CVAT tasks
   - Prefixes filenames to avoid collisions

2. **Image Resolution** (NEW)
   - Finds images for masks-only downloads
   - Searches: run_images → CVAT → database
   - Creates `image_mask_manifest.txt`

3. **Pad/Grid-Crop/Resize**
   - Small images: padded to target size
   - Large images: grid-cropped into tiles
   - Medium images: resized and padded

4. **Train/Val/Test Split**
   - Splits data into training sets
   - Deterministic (uses seed)

5. **Dataset Statistics**
   - Computes RGB mean/std for normalization

### Output Location

```
outputs/runs/{run_id}/
├── cvat_downloads/       # Source CVAT data
├── combined/             # Aggregated tasks (multi-task)
├── resolved_images/      # Images from database
├── preprocessed/         # Standardized sizes
├── train/               # Training set
│   ├── images/
│   └── masks/
├── val/                 # Validation set
│   ├── images/
│   └── masks/
├── test/                # Test set
│   ├── images/
│   └── masks/
├── datastats/           # Normalization statistics
│   └── rgb_mean_std.json
└── image_mask_manifest.txt  # Image-mask pairs
```

---

## 6. Train Stage

**Purpose:** Train segmentation models using PyTorch Lightning.

### Basic Usage

```bash
# Train with auto-preprocessing
agir-cvtoolkit train

# Train with custom parameters
agir-cvtoolkit train \
  -o train.max_epochs=100 \
  -o train.batch_size=16 \
  -o train.model.encoder_name="resnet50"

# Skip auto-preprocessing (use existing data)
agir-cvtoolkit train -o train.auto_preprocess=false
```

### Key Configuration

```yaml
# conf/train/default.yaml

# Hyperparameters
seed: 42
max_epochs: 100
batch_size: 8
num_workers: 4

# Auto-preprocessing
auto_preprocess: true  # Run preprocess if needed

# Model
model:
  arch_name: "Unet"
  encoder_name: "resnet34"
  encoder_weights: "imagenet"
  in_channels: 3
  classes: 1

# Optimizer
optimizer:
  _target_: torch.optim.Adam
  lr: 0.001
  weight_decay: 0.0001

# Scheduler
scheduler:
  _target_: torch.optim.lr_scheduler.ReduceLROnPlateau
  mode: "min"
  factor: 0.5
  patience: 5

# GPU
use_multi_gpu: false
gpu:
  max_gpus: 1
  exclude_ids: [0]
```

### Augmentations

```bash
# Disable augmentations
-o train.use_data_augmentation=false

# Enable visualizations
-o train.dataloader_visualizer.enabled=true
-o train.augmentation_visualizer.enabled=true

# Enable batch augmentations
-o augment.train.batch.mixup.enable=true
-o augment.train.batch.cutmix.enable=true
```

### Supported Models

**Architectures:**
- Unet, UnetPlusPlus
- FPN, PSPNet
- DeepLabV3Plus
- MAnet, Segformer

**Encoders:**
- ResNet: `resnet18`, `resnet34`, `resnet50`
- EfficientNet: `efficientnet-b0` to `efficientnet-b7`
- MobileNet: `mobilenet_v2`
- MiT: `mit_b0` to `mit_b5`

### Output Location

```
outputs/runs/{run_id}/
├── checkpoints/         # Training checkpoints
│   ├── epoch=00-step=100.ckpt
│   └── last.ckpt
├── model/              # Exported weights
│   └── epoch=01-step=200.pth
├── csv_logs/           # Training metrics
├── image_logs/         # Visualizations (if enabled)
└── metrics.json        # Training summary
```

### Using Trained Model

```bash
# Use trained model for inference
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=outputs/runs/train_xxx/checkpoints/best.ckpt
```

---

## Complete Pipeline Example

### Multi-Task Training Workflow

```bash
# 1. Query database
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley" \
  --sample "stratified:by=area_bin,per_group=50"

# 2. Run inference
agir-cvtoolkit infer-seg

# 3. Upload to CVAT
agir-cvtoolkit upload-cvat

# [Manual: Refine masks in CVAT]

# 4. Query more data (different species)
agir-cvtoolkit query --db semif \
  --filters "category_common_name=wheat" \
  --sample "stratified:by=area_bin,per_group=50"

# 5. Run inference
agir-cvtoolkit infer-seg

# 6. Upload to CVAT
agir-cvtoolkit upload-cvat

# [Manual: Refine masks in CVAT]

# 7. Download all completed tasks
agir-cvtoolkit download-cvat \
  -o cvat_download.required_status=completed

# 8. Train on combined dataset (automatic multi-task aggregation!)
agir-cvtoolkit train \
  -o train.max_epochs=100 \
  -o train.batch_size=8

# 9. Use trained model
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=outputs/runs/train_xxx/model/best.pth
```

---

## Common Issues & Solutions

### Query Stage

**No matching records:**
- Verify filters with `db.count()` first
- Check column names in database

### Download-CVAT Stage

**Authentication errors:**
- Check credentials in `.keys/default.yaml`
- Verify CVAT URL is correct

**Task not found:**
- Verify task IDs exist
- Check organization slug

### Preprocess Stage

**Images not found:**
- Enable database resolution: `preprocess.source.db=semif`
- Check `image_mask_manifest.txt` for missing images

**"None of the specified tasks found":**
- List available tasks: `ls outputs/runs/{run_id}/cvat_downloads/`
- Use exact directory names (lowercase, underscores)

### Train Stage

**Out of memory:**
- Reduce batch size: `-o train.batch_size=4`
- Reduce image size: `-o preprocess.pad_gridcrop_resize.size.height=1024`
- Use smaller encoder: `-o train.model.encoder_name="resnet18"`

**Training data not found:**
- Run preprocessing first: `agir-cvtoolkit preprocess`
- Or enable auto-preprocessing: `-o train.auto_preprocess=true`

---

## Tips & Best Practices

1. **Use stratified sampling** for balanced datasets
2. **Save query_spec.json** for reproducibility
3. **Download masks only** from CVAT to save bandwidth
4. **Combine multiple tasks** for diverse training data
5. **Enable visualizations** when debugging
6. **Use auto-preprocessing** for convenience
7. **Monitor training metrics** with W&B or CSV logs
8. **Start with smaller models** (resnet34) before scaling up

---

## Getting Help

- **Documentation:** `docs/README.md`
- **Query Guide:** `docs/db_query_usage.md`
- **CVAT Guide:** `docs/cvat_download_usage.md`
- **Preprocessing Guide:** `docs/preprocessing_pipeline_usage.md`
- **Training Guide:** `docs/train_pipeline_usage.md`