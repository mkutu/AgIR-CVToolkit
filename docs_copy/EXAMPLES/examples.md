# AgIR-CVToolkit Examples

A comprehensive collection of examples for the Agricultural Image Repository Computer Vision Toolkit. These examples cover all pipeline stages from database queries to model training.

---

## Table of Contents

- [Quick Start Examples](#quick-start-examples)
- [Query Examples](#query-examples)
- [Inference Examples](#inference-examples)
- [CVAT Workflow Examples](#cvat-workflow-examples)
- [Preprocessing Examples](#preprocessing-examples)
- [Training Examples](#training-examples)
- [Complete Workflow Examples](#complete-workflow-examples)
- [Advanced Examples](#advanced-examples)

---

## Quick Start Examples

### Example 1: Your First Query

Query the SemiF database for images from North Carolina:

```bash
agir-cv query --db semif \
  --filters "state=NC" \
  --limit 100 \
  --out csv
```

**Output**: Creates `outputs/runs/query_semif_*/query/query.csv` with 100 records.

### Example 2: Simple Inference Pipeline

Run segmentation on queried images:

```bash
# 1. Query
agir-cv query --db semif --filters "state=NC" --limit 50

# 2. Run inference
agir-cv infer-seg
```

### Example 3: End-to-End with CVAT

Complete pipeline from query to annotation:

```bash
# 1. Query
agir-cv query --db semif --filters "category_common_name=barley" --limit 100

# 2. Inference (save images for CVAT)
agir-cv infer-seg -o seg_inference.output.save_images=true

# 3. Upload to CVAT
agir-cv upload-cvat -o cvat_upload.project_id=12345
```

---

## Query Examples

### Basic Filtering

#### Single Filter
```bash
# Query by state
agir-cv query --db semif --filters "state=NC"

# Query by species
agir-cv query --db semif --filters "category_common_name=barley"

# Query by date
agir-cv query --db semif --filters "datetime>=2024-01-01"
```

#### Multiple Filters (AND Logic)
```bash
# North Carolina barley only
agir-cv query --db semif \
  --filters "state=NC" \
  --filters "category_common_name=barley"
```

#### Multiple Values (OR Logic)
```bash
# Multiple species
agir-cv query --db semif \
  --filters "category_common_name=barley,wheat,rye"

# Multiple states
agir-cv query --db semif \
  --filters "state=NC,TX,MD"
```

### Comparison Operators

```bash
# Size filtering
agir-cv query --db semif \
  --filters "estimated_bbox_area_cm2>=50" \
  --filters "estimated_bbox_area_cm2<=200"

# Date ranges
agir-cv query --db semif \
  --filters "datetime>=2024-01-01" \
  --filters "datetime<=2024-12-31"

# Quality filtering
agir-cv query --db semif \
  --filters "blur_effect<=2.0" \
  --filters "num_components==1"
```

### Sampling Strategies

#### Random Sampling
```bash
# Simple random sample
agir-cv query --db semif \
  --filters "state=NC" \
  --sample "random:n=100"
```

#### Seeded Random Sampling (Reproducible)
```bash
# Same seed = same results every time
agir-cv query --db semif \
  --filters "state=NC" \
  --sample "seeded:n=100,seed=42"
```

#### Stratified Sampling (Balanced Dataset)
```bash
# Balance by species - 10 of each
agir-cv query --db semif \
  --sample "stratified:by=category_common_name,per_group=10"

# Balance by multiple columns
agir-cv query --db semif \
  --sample "stratified:by=category_common_name|estimated_area_bin,per_group=5"

# Balance by state and species
agir-cv query --db semif \
  --filters "state=NC,SC" \
  --sample "stratified:by=category_common_name,per_group=20"
```

### Output Formats

```bash
# JSON output (default)
agir-cv query --db semif --filters "state=NC" --out json

# CSV output (Excel-friendly)
agir-cv query --db semif --filters "state=NC" --out csv

# Parquet output (efficient for large datasets)
agir-cv query --db semif --filters "state=NC" --out parquet
```

### Projection (Select Specific Columns)

```bash
# Only essential fields
agir-cv query --db semif \
  --filters "state=NC" \
  --projection "cutout_id,category_common_name,estimated_bbox_area_cm2"

# Taxonomy only
agir-cv query --db semif \
  --projection "cutout_id,category_genus,category_species,category_common_name"
```

### Sorting

```bash
# Sort by date (newest first)
agir-cv query --db semif \
  --filters "state=NC" \
  --sort "datetime:desc"

# Sort by area (largest first)
agir-cv query --db semif \
  --sort "estimated_bbox_area_cm2:desc"

# Multiple sort criteria
agir-cv query --db semif \
  --sort "category_common_name:asc,estimated_bbox_area_cm2:desc"
```

### Preview Mode

```bash
# Check what you'll get without full query
agir-cv query --db semif \
  --filters "category_common_name=barley" \
  --preview 5
```

### Complex Query Examples

#### High-Quality Large Specimens
```bash
agir-cv query --db semif \
  --filters "estimated_bbox_area_cm2>=100" \
  --filters "num_components==1" \
  --sample "random:n=200"
```

#### Multi-State Stratified Sample
```bash
agir-cv query --db semif \
  --filters "state=NC,TX,NC" \
  --sample "stratified:by=state|category_common_name|estimated_area_bin,per_group=5"
```

#### Recent Images
```bash
agir-cv query --db semif \
  --filters "datetime>=2024-01-01" \
  --sort "datetime:desc" \
  --limit 500
```

---

## Inference Examples

### Basic Inference

```bash
# Run inference on previously queried data
agir-cv infer-seg
```

### Custom Model Checkpoint

```bash
# Use your own trained model
agir-cv infer-seg \
  -o seg_inference.model.ckpt_path=/path/to/model.pth
```

### Inference with Image Saving

```bash
# Save images for later use (CVAT, visualization)
agir-cv infer-seg \
  -o seg_inference.output.save_images=true
```

### Inference with Custom Batch Size

```bash
# Adjust for GPU memory
agir-cv infer-seg \
  -o seg_inference.batch_size=16
```

### Inference on Specific GPU

```bash
# Select GPU
CUDA_VISIBLE_DEVICES=1 agir-cv infer-seg
```

### Complete Inference Configuration

```bash
agir-cv infer-seg \
  -o seg_inference.model.ckpt_path=models/best.pth \
  -o seg_inference.batch_size=8 \
  -o seg_inference.output.save_images=true \
  -o seg_inference.output.save_masks=true
```

---

## CVAT Workflow Examples

### Upload to CVAT

#### Basic Upload
```bash
# Upload to existing project
agir-cv upload-cvat \
  -o cvat_upload.project_id=12345
```

#### Create New Project
```bash
# Create new project with task
agir-cv upload-cvat \
  -o cvat_upload.project_name="Barley Segmentation 2024" \
  -o cvat_upload.task_name="Batch_001"
```

#### Upload with Custom Labels
```bash
agir-cv upload-cvat \
  -o cvat_upload.project_id=12345 \
  -o cvat_upload.labels='["background","weed","crop"]'
```

### Download from CVAT

#### Download Completed Tasks
```bash
# Only download completed tasks
agir-cv download-cvat \
  -o cvat_download.required_status=completed
```

#### Download Specific Tasks
```bash
# Download by task IDs
agir-cv download-cvat \
  -o cvat_download.task_ids=[101,102,103]
```

#### Download Masks Only (Bandwidth Saver)
```bash
# Don't download images (faster)
agir-cv download-cvat \
  -o cvat_download.include_images=false \
  -o cvat_download.dataset_format="Segmentation mask 1.1"
```

#### Download Entire Project
```bash
# Download all tasks from a project
agir-cv download-cvat \
  -o cvat_download.project_id=12345
```

---

## Preprocessing Examples

### Automatic Preprocessing

```bash
# Let training handle preprocessing
agir-cv train  # Auto-preprocessing enabled by default
```

### Manual Preprocessing

```bash
# Run preprocessing separately
agir-cv preprocess
```

### Multi-Task Preprocessing

```bash
# Combine multiple annotation batches
agir-cv download-cvat -o cvat_download.task_ids=[101,102,103]
agir-cv preprocess  # Automatically combines all tasks!
```

### Custom Image Size

```bash
agir-cv preprocess \
  -o preprocess.pad_gridcrop_resize.size.height=1024 \
  -o preprocess.pad_gridcrop_resize.size.width=1024
```

### Custom Train/Val/Test Split

```bash
agir-cv preprocess \
  -o preprocess.split.train=0.7 \
  -o preprocess.split.val=0.2 \
  -o preprocess.split.test=0.1
```

### Disable Grid Cropping

```bash
# For smaller images that don't need cropping
agir-cv preprocess \
  -o preprocess.pad_gridcrop_resize.grid_crop.enabled=false
```

---

## Training Examples

### Basic Training

```bash
# Train with default settings
agir-cv train
```

### Custom Epochs and Batch Size

```bash
agir-cv train \
  -o train.max_epochs=100 \
  -o train.batch_size=8
```

### Different Model Architecture

```bash
# Use ResNet50 encoder
agir-cv train \
  -o train.model.encoder_name="resnet50"

# Use EfficientNet
agir-cv train \
  -o train.model.encoder_name="efficientnet-b3"
```

### Training with Weights & Biases

```bash
agir-cv train \
  -o train.logger.wandb.enabled=true \
  -o train.logger.wandb.project="weed-segmentation" \
  -o train.logger.wandb.name="experiment_001"
```

### Training on Specific GPU

```bash
CUDA_VISIBLE_DEVICES=0 agir-cv train
```

### Complete Training Configuration

```bash
agir-cv train \
  -o train.max_epochs=150 \
  -o train.batch_size=16 \
  -o train.model.encoder_name="resnet50" \
  -o train.model.decoder_channels=[256,128,64,32,16] \
  -o train.optimizer.lr=0.001 \
  -o train.logger.wandb.enabled=true \
  -o train.logger.wandb.project="barley-segmentation"
```

### Continue Training from Checkpoint

```bash
agir-cv train \
  -o train.resume_from_checkpoint=outputs/runs/train_xxx/model/last.ckpt
```

---

## Complete Workflow Examples

### Example 1: First Model Training

Train a segmentation model from scratch:

```bash
# 1. Query balanced dataset
agir-cv query --db semif \
  --sample "stratified:by=category_common_name,per_group=100" \
  --out csv

# 2. Run inference with initial model
agir-cv infer-seg \
  -o seg_inference.model.ckpt_path=models/initial_model.pth \
  -o seg_inference.output.save_images=true

# 3. Upload to CVAT for refinement
agir-cv upload-cvat \
  -o cvat_upload.project_name="Initial Training" \
  -o cvat_upload.task_name="Batch_001"

# [Manually refine masks in CVAT]

# 4. Download refined annotations
agir-cv download-cvat \
  -o cvat_download.required_status=completed

# 5. Train model (auto-preprocessing)
agir-cv train \
  -o train.max_epochs=100 \
  -o train.batch_size=8 \
  -o train.model.encoder_name="resnet50"
```

### Example 2: Iterative Model Improvement

Improve model with multiple annotation rounds:

```bash
# ============ Round 1: Barley ============
agir-cv query --db semif \
  --filters "category_common_name=barley" \
  --sample "stratified:by=estimated_area_bin,per_group=50"

agir-cv infer-seg -o seg_inference.output.save_images=true
agir-cv upload-cvat -o cvat_upload.task_name="Round1_Barley"

# [Refine in CVAT]
agir-cv download-cvat
agir-cv train

# ============ Round 2: Wheat ============
agir-cv query --db semif \
  --filters "category_common_name=wheat" \
  --sample "stratified:by=estimated_area_bin,per_group=50"

# Use improved model from Round 1
agir-cv infer-seg \
  -o seg_inference.model.ckpt_path=outputs/runs/train_xxx/model/best.pth \
  -o seg_inference.output.save_images=true

agir-cv upload-cvat -o cvat_upload.task_name="Round2_Wheat"

# [Refine in CVAT]
agir-cv download-cvat

# Train on combined dataset (Round 1 + Round 2)
agir-cv train \
  -o train.max_epochs=150
```

### Example 3: Multi-Species Dataset

Create a diverse training set:

```bash
# 1. Query multiple species
agir-cv query --db semif \
  --filters "category_common_name=barley,wheat,rye,oat" \
  --sample "stratified:by=category_common_name|state,per_group=25"

# 2. Inference and upload
agir-cv infer-seg -o seg_inference.output.save_images=true
agir-cv upload-cvat \
  -o cvat_upload.project_name="Multi-Species Training" \
  -o cvat_upload.task_name="Diverse_Batch"

# [Refine in CVAT]

# 3. Download and train
agir-cv download-cvat -o cvat_download.required_status=completed
agir-cv train \
  -o train.max_epochs=100 \
  -o train.batch_size=8
```

### Example 4: Quality-Focused Dataset

Focus on high-quality specimens:

```bash
# 1. Query high-quality images
agir-cv query --db semif \
  --filters "estimated_bbox_area_cm2>=75" \
  --filters "blur_effect<=1.5" \
  --filters "num_components==1" \
  --sample "stratified:by=category_common_name,per_group=50"

# 2. Inference
agir-cv infer-seg -o seg_inference.output.save_images=true

# 3. Upload to CVAT
agir-cv upload-cvat \
  -o cvat_upload.project_name="High Quality Training" \
  -o cvat_upload.task_name="Quality_Batch"

# [Refine in CVAT]

# 4. Train
agir-cv download-cvat -o cvat_download.required_status=completed
agir-cv train -o train.max_epochs=120
```
agir-cvtoolkit upload-cvat -o cvat_upload.task_name="Round1_Barley"

# [Refine in CVAT]
agir-cvtoolkit download-cvat
agir-cvtoolkit train

# ============ Round 2: Wheat ============
agir-cvtoolkit query --db semif \
  --filters "category_common_name=wheat" \
  --sample "stratified:by=estimated_area_bin,per_group=50"

# Use improved model from Round 1
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=outputs/runs/train_xxx/model/best.pth \
  -o seg_inference.output.save_images=true

agir-cvtoolkit upload-cvat -o cvat_upload.task_name="Round2_Wheat"

# [Refine in CVAT]
agir-cvtoolkit download-cvat

# Train on combined dataset (Round 1 + Round 2)
agir-cvtoolkit train \
  -o train.max_epochs=150
```

### Example 3: Multi-Species Dataset

Create a diverse training set:

```bash
# 1. Query multiple species
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley,wheat,rye,oat" \
  --sample "stratified:by=category_common_name|state,per_group=25"

# 2. Inference and upload
agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true
agir-cvtoolkit upload-cvat \
  -o cvat_upload.project_name="Multi-Species Training" \
  -o cvat_upload.task_name="Diverse_Batch"

# [Refine in CVAT]

# 3. Download and train
agir-cvtoolkit download-cvat -o cvat_download.required_status=completed
agir-cvtoolkit train \
  -o train.max_epochs=100 \
  -o train.batch_size=8
```

### Example 4: Quality-Focused Dataset

Focus on high-quality specimens:

```bash
# 1. Query high-quality images
agir-cvtoolkit query --db semif \
  --filters "estimated_bbox_area_cm2>=75" \
  --filters "blur_effect<=1.5" \
  --filters "num_components==1" \
  --sample "stratified:by=category_common_name,per_group=50"

# 2. Inference
agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true

# 3. Upload to CVAT
agir-cvtoolkit upload-cvat \
  -o cvat_upload.project_name="High Quality Training" \
  -o cvat_upload.task_name="Quality_Batch"

# [Refine in CVAT]

# 4. Train
agir-cvtoolkit download-cvat -o cvat_download.required_status=completed
agir-cvtoolkit train -o train.max_epochs=120
```

---

## Advanced Examples

### Example 1: Reproduce a Previous Query

```bash
# View the reproduction command
cat outputs/runs/query_xxx/query/query_spec.json

# Run the exact same query again
agir-cv query --db semif \
  --filters "state=NC" \
  --sample "stratified:by=category_common_name,per_group=20"
```

### Example 2: Custom Data Augmentation

```bash
agir-cv train \
  -o augment.train.horizontal_flip.enabled=true \
  -o augment.train.horizontal_flip.p=0.5 \
  -o augment.train.vertical_flip.enabled=true \
  -o augment.train.vertical_flip.p=0.3 \
  -o augment.train.rotate.enabled=true \
  -o augment.train.rotate.limit=45 \
  -o augment.train.brightness_contrast.enabled=true
```

### Example 3: Custom Learning Rate Schedule

```bash
agir-cv train \
  -o train.optimizer.lr=0.0001 \
  -o train.scheduler.mode="min" \
  -o train.scheduler.factor=0.1 \
  -o train.scheduler.patience=10
```

### Example 4: Multi-GPU Training

```bash
CUDA_VISIBLE_DEVICES=0,1 agir-cv train \
  -o train.devices=2 \
  -o train.strategy="ddp" \
  -o train.batch_size=16
```

### Example 5: Export Model for Production

```bash
# Train model
agir-cv train -o train.max_epochs=100

# Use trained model for inference
agir-cv infer-seg \
  -o seg_inference.model.ckpt_path=outputs/runs/train_xxx/model/best.pth
```

### Example 6: Combine Multiple Annotation Batches

```bash
# Download multiple completed tasks
agir-cv download-cvat \
  -o cvat_download.task_ids=[101,102,103,104,105]

# Preprocess combines all automatically
agir-cv preprocess

# Train on combined dataset
agir-cv train \
  -o train.max_epochs=150 \
  -o train.batch_size=8
```

### Example 7: Field Database Query with Context

```bash
# Query field database with agricultural context
agir-cv query --db field \
  --filters "us_state=NC" \
  --filters "crop_type_secondary=soybean" \
  --filters "growth_stage=flowering" \
  --sample "stratified:by=common_name,per_group=20"
```

### Example 8: Size-Specific Training

```bash
# Query small specimens only
agir-cv query --db semif \
  --filters "estimated_area_bin=small" \
  --sample "random:n=200"

# Train with smaller image size
agir-cv infer-seg -o seg_inference.output.save_images=true
agir-cv upload-cvat
# [Refine]
agir-cv download-cvat
agir-cv preprocess \
  -o preprocess.pad_gridcrop_resize.size.height=512 \
  -o preprocess.pad_gridcrop_resize.size.width=512

agir-cv train \
  -o train.batch_size=32
```

---

## Tips for Examples

### General Tips
- Always save `query_spec.json` for reproducibility
- Use meaningful project/task names for organization
- Start with small datasets (10-50 images) to validate pipeline
- Monitor GPU memory usage and adjust batch size accordingly

### Query Tips
- Use `--preview` to test filters before full query
- Use stratified sampling for balanced datasets
- Save queries in different output formats for different uses

### Inference Tips
- Always save images if uploading to CVAT
- Use appropriate batch size for your GPU
- Keep model checkpoints organized with version numbers

### CVAT Tips
- Download masks only to save bandwidth
- Use `required_status=completed` to filter tasks
- Keep task names descriptive for tracking

### Training Tips
- Start with smaller encoders (resnet18/resnet34)
- Enable W&B logging for experiment tracking
- Use auto-preprocessing unless you need custom control
- Monitor validation loss for early stopping

---

## Quick Reference Commands

```bash
# Essential pipeline
agir-cv query --db semif --filters "state=NC" --sample "random:n=100"
agir-cv infer-seg
agir-cv upload-cvat
agir-cv download-cvat
agir-cv train

# With common options
agir-cv query --db semif --sample "stratified:by=common_name,per_group=20" --out csv
agir-cv infer-seg -o seg_inference.output.save_images=true
agir-cv train -o train.max_epochs=100 -o train.batch_size=8

# Environment setup
export CVAT_HOST="https://app.cvat.ai"
export CVAT_API_KEY="your-key"
export CUDA_VISIBLE_DEVICES="0"
```

---

## Getting Help

- **Documentation**: See main README and stage-specific guides
- **Troubleshooting**: Check logs in `outputs/runs/{run_id}/logs/`
- **Configuration**: Review `conf/` directory for all options
- **Examples**: This document!