# AgIR-CVToolkit - Complete Pipeline Overview

## The Complete Workflow

The AgIR-CVToolkit implements a full machine learning lifecycle for agricultural image segmentation:

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  Query  │────▶│ Infer   │────▶│ Upload  │────▶│  CVAT   │
│   DB    │     │  Seg    │     │  CVAT   │     │ Refine  │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
                                                      │
                                                      ▼
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  Infer  │◀────│  Train  │◀────│Preprocess│◀────│Download │
│  (New)  │     │  Model  │     │         │     │  CVAT   │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
```

## All Stages Quick Reference

### 1. Query (`query`)

**Purpose**: Select images from database  
**Input**: Database + filters  
**Output**: `query.json`, `query_spec.json`

```bash
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --sample "stratified:by=category_common_name,per_group=50"
```

📖 **Full docs**: [Query Quickstart](query_quickstart.md) | [Query Guide](PIPELINE_STAGES/01_query/db_query_usage.md) | [Query Specs](../PIPELINE_STAGES/01_query/query_specs_quick_reference.md)

---

### 2. Segmentation Inference (`infer-seg`)

**Purpose**: Generate masks using trained model  
**Input**: Query results or direct DB query  
**Output**: Masks, images, manifest

```bash
agir-cvtoolkit infer-seg \
  -o seg_inference.output.save_images=true
```

📖 **Full docs**: [Inference Quick Reference](../PIPELINE_STAGES/02_inference/seg_inference_quickstart.md)

---

### 3. CVAT Upload (`upload-cvat`)

**Purpose**: Upload images + masks to CVAT for refinement  
**Input**: Inference results (images + masks)  
**Output**: CVAT task

```bash
agir-cvtoolkit upload-cvat \
  -o cvat_upload.project_id=12345
```

📖 **Full docs**: [Upload Quick Reference](../PIPELINE_STAGES/03_cvat_upload/cvat_upload_usage.md)

---

### 4. CVAT Refinement (Manual)

**Purpose**: Human review and correction of masks  
**Interface**: CVAT web application  
**Actions**: Correct boundaries, add/remove regions, validate labels

🌐 **Access**: Task URL provided by upload stage

---

### 5. CVAT Download (`download-cvat`)

**Purpose**: Download refined masks from CVAT  
**Input**: CVAT project/tasks  
**Output**: Refined masks + annotations

```bash
agir-cvtoolkit download-cvat \
  -o cvat_download.project_id=12345 \
  -o cvat_download.required_status=completed
```

📖 **Full docs**: [Download Guide](../PIPELINE_STAGES/04_cvat_download/cvat_download_usage.md)

---

### 6. Preprocessing (`preprocess`)

**Purpose**: Prepare data for training  
**Input**: Downloaded masks (can combine multiple tasks)  
**Output**: train/val/test splits, normalized images

```bash
agir-cvtoolkit preprocess
```

📖 **Full docs**: [Preprocessing Guide](../PIPELINE_STAGES/05_preprocessing/preprocessing_pipeline_usage.md)

---

### 7. Training (`train`)

**Purpose**: Train improved segmentation model  
**Input**: Preprocessed train/val data  
**Output**: Trained model checkpoint

```bash
agir-cvtoolkit train \
  -o train.max_epochs=100 \
  -o train.batch_size=8
```

📖 **Full docs**: [Training Guide](../PIPELINE_STAGES/06_training/train_pipeline_usage.md)

---

## Complete Examples

### Example 1: First Iteration

Initial model training from scratch:

```bash
# 1. Query database for balanced dataset
agir-cvtoolkit query --db semif \
  --sample "stratified:by=category_common_name,per_group=100" \
  --out csv

# 2. Run inference with initial model
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=/path/to/initial_model.ckpt \
  -o seg_inference.output.save_images=true

# 3. Upload to CVAT
agir-cvtoolkit upload-cvat \
  -o cvat_upload.project_id=12345 \
  -o cvat_upload.task_name="Initial_Barley_Batch"

# 4. [Manually refine in CVAT]

# 5. Download refined masks
agir-cvtoolkit download-cvat \
  -o cvat_download.project_id=12345 \
  -o cvat_download.required_status=completed

# 6. Preprocess for training
agir-cvtoolkit preprocess

# 7. Train model
agir-cvtoolkit train \
  -o train.max_epochs=100 \
  -o train.model.encoder_name="resnet50"
```

### Example 2: Iterative Improvement

Improve model with multiple annotation rounds:

```bash
# ============ Round 1 ============
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley" \
  --sample "stratified:by=area_bin,per_group=50"

agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true
agir-cvtoolkit upload-cvat -o cvat_upload.task_name="Round1_Barley"

# [Refine in CVAT]

agir-cvtoolkit download-cvat
agir-cvtoolkit train

# ============ Round 2 ============
agir-cvtoolkit query --db semif \
  --filters "category_common_name=wheat" \
  --sample "stratified:by=area_bin,per_group=50"

agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=outputs/runs/train_xxx/model/best.pth \
  -o seg_inference.output.save_images=true

agir-cvtoolkit upload-cvat -o cvat_upload.task_name="Round2_Wheat"

# [Refine in CVAT]

agir-cvtoolkit download-cvat
agir-cvtoolkit train  # Combines Round 1 + Round 2 data!
```

### Example 3: Multi-Species Training

Combine multiple CVAT tasks for multi-class training:

```bash
# ============ Barley Batch ============
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley" \
  --sample "stratified:by=area_bin,per_group=100"

agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true
agir-cvtoolkit upload-cvat -o cvat_upload.task_name="Barley_Annotations"

# ============ Wheat Batch ============
agir-cvtoolkit query --db semif \
  --filters "category_common_name=wheat" \
  --sample "stratified:by=area_bin,per_group=100"

agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true
agir-cvtoolkit upload-cvat -o cvat_upload.task_name="Wheat_Annotations"

# ============ Hairy Vetch Batch ============
agir-cvtoolkit query --db semif \
  --filters "category_common_name=hairy vetch" \
  --sample "stratified:by=area_bin,per_group=100"

agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true
agir-cvtoolkit upload-cvat -o cvat_upload.task_name="HairyVetch_Annotations"

# [Refine all in CVAT]

# ============ Download All ============
agir-cvtoolkit download-cvat \
  -o cvat_download.required_status=completed

# ============ Train Multi-Class Model ============
# Preprocessing automatically combines all tasks!
agir-cvtoolkit train \
  -o train.max_epochs=100 \
  -o train.batch_size=16
```

## Configuration Management

### Project Organization

```yaml
# Set in CLI or config
project:
  name: "barley_segmentation"
  subname: "round_001"
```

Output structure:
```
outputs/runs/barley_segmentation/round_001/
├── query/
├── masks/
├── images/
├── cvat_downloads/
├── train/
└── model/
```

### Shared Configuration

The `cfg.yaml` tracks all stages:

```yaml
runtime:
  stage: "train"
  run_id: "barley_segmentation/round_001"
  
query:
  filters: ["state=NC"]
  sample: "stratified:..."

seg_inference:
  model:
    ckpt_path: "/path/to/model.ckpt"

train:
  max_epochs: 100
  batch_size: 8
```

## Common Patterns

### Pattern 1: Quick Validation

Test pipeline on small dataset:

```bash
agir-cvtoolkit query --db semif --limit 10
agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true
agir-cvtoolkit upload-cvat -o cvat_upload.task_name="Test_Batch"
```

### Pattern 2: Balanced Multi-Class

Create balanced training set:

```bash
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley,wheat,rye" \
  --sample "stratified:by=category_common_name|area_bin,per_group=50"
```

### Pattern 3: Progressive Refinement

Gradually improve model:

```bash
# Week 1: Initial model
agir-cvtoolkit infer-seg
agir-cvtoolkit upload-cvat
# [Refine 100 images]

# Week 2: Train v1
agir-cvtoolkit download-cvat
agir-cvtoolkit train

# Week 3: Refine with v1
agir-cvtoolkit infer-seg -o seg_inference.model.ckpt_path=.../v1.ckpt
agir-cvtoolkit upload-cvat
# [Refine 200 more images]

# Week 4: Train v2 (300 total refined images)
agir-cvtoolkit download-cvat
agir-cvtoolkit train
```

## Output Files Cheat Sheet

| Stage | Key Output Files | Purpose |
|-------|-----------------|---------|
| Query | `query.json`, `query_spec.json` | Data records, reproducibility |
| Infer-Seg | `masks/*.png`, `manifest.jsonl` | Generated masks, metadata |
| Upload-CVAT | `metrics.json` | Task URL, upload stats |
| Download-CVAT | `cvat_downloads/<task>/` | Refined annotations |
| Preprocess | `train/`, `val/`, `test/` | Split datasets |
| Train | `model/best.pth`, `checkpoints/` | Trained model |

## Stage Dependencies

```
┌──────────┐
│  query   │─┐
└──────────┘ │
             ▼
         ┌──────────┐
         │infer-seg │─┐
         └──────────┘ │
                      ▼
                  ┌──────────┐
                  │upload-   │
                  │  cvat    │
                  └──────────┘
                      │
                      ▼
                  ┌──────────┐
                  │download- │─┐
                  │  cvat    │ │
                  └──────────┘ │
                               ▼
                           ┌──────────┐
                           │preprocess│─┐
                           └──────────┘ │
                                        ▼
                                    ┌──────────┐
                                    │  train   │
                                    └──────────┘
```

**Legend**:
- → Required dependency
- Stages can be run independently if you provide required inputs

## Troubleshooting by Stage

### Query Issues
- **No results**: Check filters match database schema
- **Slow queries**: Add indexes to database or reduce result size

### Inference Issues
- **OOM errors**: Reduce tile size or batch size
- **Slow inference**: Check GPU usage, increase tile size if possible
- **Empty masks**: Verify model checkpoint and normalization

### Upload Issues
- **Auth failed**: Check `.keys/default.yaml` credentials
- **Images not found**: Ensure `save_images=true` during inference
- **Labels missing**: Add labels to CVAT project

### Download Issues
- **No tasks found**: Check project_id and required_status
- **Format errors**: Use supported formats (COCO, Segmentation mask)

### Preprocessing Issues
- **No data found**: Verify CVAT downloads exist
- **Size mismatches**: Check image/mask pairing
- **Out of memory**: Reduce worker count

### Training Issues
- **Data not found**: Run preprocessing first or enable auto_preprocess
- **OOM errors**: Reduce batch_size or image size
- **Poor performance**: Increase augmentation, check data quality

## Best Practices

### 🎯 For Reproducibility

1. Always save `query_spec.json` with your datasets
2. Use `project.name` and `project.subname` for organization
3. Keep `cfg.yaml` for complete run history
4. Document model checkpoints with version numbers

### ⚡ For Performance

1. Use stratified sampling for balanced datasets
2. Save images during inference (faster than re-reading)
3. Use appropriate tile sizes based on GPU memory
4. Enable multiprocessing for preprocessing

### 🔄 For Iteration

1. Start with small validation sets
2. Use same project for multiple annotation rounds
3. Incrementally increase dataset size
4. Track metrics at each iteration

### 🛡️ For Reliability

1. Monitor logs for warnings/errors
2. Check metrics.json after each stage
3. Verify data quality before training
4. Keep backups of CVAT exports

## Summary

| Stage | Command | Input | Output | Time |
|-------|---------|-------|--------|------|
| Query | `query` | Database | Records | Seconds |
| Infer | `infer-seg` | Records | Masks | ~1s/image |
| Upload | `upload-cvat` | Masks + Images | Task | ~5s/image |
| Refine | CVAT UI | Task | Refined masks | Hours |
| Download | `download-cvat` | CVAT | Annotations | Minutes |
| Preprocess | `preprocess` | Annotations | Splits | Minutes |
| Train | `train` | Splits | Model | Hours |

## Quick Links

- [Query Guide](../PIPELINE_STAGES/01_query/db_query_usage.md) - Database querying
- [Query Specs](../PIPELINE_STAGES/01_query/query_specs_quick_reference.md) - Reproducibility
- [Inference Reference](../PIPELINE_STAGES/02_inference/seg_inference_quickstart.md) - Model inference
- [Upload Reference](../PIPELINE_STAGES/03_cvat_upload/cvat_upload_usage.md) - CVAT upload
- [Download Guide](../PIPELINE_STAGES/04_cvat_download/cvat_download_usage.md) - CVAT download
- [Preprocessing Guide](../PIPELINE_STAGES/05_preprocessing/preprocessing_pipeline_usage.md) - Data preparation
- [Training Guide](../PIPELINE_STAGES/06_training/train_pipeline_usage.md) - Model training
- [Config Guide](../CONFIGURATION/hydra_config_quick_ref.md) - Configuration

## Getting Help

1. Check the stage-specific guide
2. Review the [README](README.md) navigation
3. Examine logs in `outputs/runs/{run_id}/logs/`
4. Check metrics in `metrics.json`
5. Verify data exists at each stage

---

**Pro Tip**: Run a complete mini-pipeline on 10 images first to validate your setup before scaling up! 🚀