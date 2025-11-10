# AgIR-CVToolkit Stage Quick Reference

A comprehensive guide to each pipeline stage in the AgIR-CVToolkit.

---

## Stage 1: Query

**Purpose:** Query SemiF/Field databases to select images for processing

### Basic Usage
```bash
# Simple query
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --out csv

# Stratified sampling
agir-cvtoolkit query --db semif \
  --sample "stratified:by=category_common_name,per_group=20" \
  --out csv
```

### Key Features
- **Filter** by species, location, time, area, etc.
- **Sample** with random, seeded, or stratified methods
- **Output** to JSON, CSV, or Parquet
- **Reproduce** queries via `query_spec.json`

### Common Options
| Option | Description | Example |
|--------|-------------|---------|
| `--db` | Database to query | `semif` or `field` |
| `--filters` | Filter criteria | `"state=NC,species=barley"` |
| `--sample` | Sampling strategy | `"random:n=100"` |
| `--out` | Output format | `json`, `csv`, `parquet` |
| `--limit` | Max records | `1000` |

### Output
```
outputs/runs/{run_id}/query/
├── query.csv           # Query results
├── query_spec.json     # Reproducibility record
└── metrics.json        # Summary stats
```

---

## Stage 2: Inference (Segmentation)

**Purpose:** Run segmentation models to generate mask predictions

### Basic Usage
```bash
# Run inference on queried images
agir-cvtoolkit infer-seg

# With custom model
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=models/my_model.pth
```

### Key Features
- **Automatic** input from previous query stage
- **Save** masks, images, and cutouts
- **Multiple** output formats (PNG masks, COCO JSON, YOLO)
- **GPU** acceleration support

### Common Options
| Option | Description | Example |
|--------|-------------|---------|
| `model.ckpt_path` | Model checkpoint | `models/seg_model.pth` |
| `output.save_masks` | Save mask files | `true` |
| `output.save_images` | Save original images | `true` |
| `batch_size` | Inference batch size | `8` |

### Output
```
outputs/runs/{run_id}/
├── masks/              # PNG mask files
├── images/             # Original images
├── predictions.json    # Prediction metadata
└── metrics.json        # Inference stats
```

---

## Stage 3: Upload to CVAT

**Purpose:** Upload images and preliminary annotations to CVAT for human refinement

### Basic Usage
```bash
# Upload from inference results
agir-cvtoolkit upload-cvat

# Specify project/task
agir-cvtoolkit upload-cvat \
  -o cvat_upload.project_name="Barley Segmentation" \
  -o cvat_upload.task_name="Batch_001"
```

### Key Features
- **Auto-detects** images/masks from inference stage
- **Creates** CVAT projects and tasks
- **Uploads** prelabels for faster annotation
- **Configurable** task settings (assignee, labels, etc.)

### Common Options
| Option | Description | Example |
|--------|-------------|---------|
| `project_name` | CVAT project name | `"Field Segmentation"` |
| `task_name` | CVAT task name | `"Batch_001"` |
| `organization_slug` | Organization | `null` (personal) |
| `assignee` | Task assignee | `"user@example.com"` |

### Manual Step
**Refine annotations in CVAT web interface**

---

## Stage 4: Download from CVAT

**Purpose:** Download refined annotations from CVAT after human review

### Basic Usage
```bash
# Download all completed tasks
agir-cvtoolkit download-cvat \
  -o cvat_download.required_status=completed

# Download specific tasks
agir-cvtoolkit download-cvat \
  -o cvat_download.task_ids=[101,102,103]
```

### Key Features
- **Filter** by status (completed, in-progress, etc.)
- **Select** specific tasks or projects
- **Multiple** export formats
- **Validate** image existence before download

### Common Options
| Option | Description | Example |
|--------|-------------|---------|
| `required_status` | Filter by status | `"completed"` |
| `task_ids` | Specific tasks | `[101,102,103]` |
| `project_id` | Filter by project | `12345` |
| `dataset_format` | Export format | `"Segmentation mask 1.1"` |
| `include_images` | Download images | `false` (save bandwidth) |

### Output
```
outputs/runs/{run_id}/cvat_downloads/
├── task_001/
│   ├── annotations/    # Mask files
│   └── images/         # (optional)
└── task_002/
    └── annotations/
```

---

## Stage 5: Preprocess

**Purpose:** Prepare training data by standardizing sizes, splitting datasets, and computing statistics

### Basic Usage
```bash
# Auto-runs during training (recommended)
agir-cvtoolkit train

# Manual preprocessing
agir-cvtoolkit preprocess
```

### Key Features
- **Multi-task** aggregation (combines multiple CVAT downloads)
- **Standardize** image sizes (pad/crop/resize)
- **Split** into train/val/test sets
- **Compute** normalization statistics
- **Resolve** images from multiple sources (local, CVAT, database)

### Processing Steps
1. **Aggregate** - Combine multiple CVAT tasks
2. **Resolve Images** - Find corresponding images for masks
3. **Pad/Grid-Crop/Resize** - Standardize to target size (default 2048×2048)
4. **Split** - Create train (80%) / val (15%) / test (5%) sets
5. **Compute Stats** - Calculate mean/std for normalization

### Common Options
| Option | Description | Example |
|--------|-------------|---------|
| `source.tasks` | Tasks to include | `null` (all) or `["task1"]` |
| `pad_gridcrop_resize.size` | Target dimensions | `height: 2048, width: 2048` |
| `split.train` | Train split ratio | `0.8` |
| `compute_data_stats.enabled` | Compute statistics | `true` |

### Output
```
outputs/runs/{run_id}/
├── combined/           # Aggregated tasks (if multiple)
├── train/
│   ├── images/
│   └── masks/
├── val/
│   ├── images/
│   └── masks/
├── test/
│   ├── images/
│   └── masks/
├── data_stats.json     # Mean/std for normalization
└── image_mask_manifest.txt  # Image-mask pairs
```

---

## Stage 6: Train

**Purpose:** Train segmentation models using PyTorch Lightning

### Basic Usage
```bash
# Train with defaults (auto-preprocessing)
agir-cvtoolkit train

# Custom training run
agir-cvtoolkit train \
  -o train.max_epochs=100 \
  -o train.batch_size=16 \
  -o train.model.encoder_name="resnet50"
```

### Key Features
- **Auto-preprocessing** of CVAT downloads
- **Multiple** architectures (Unet, FPN, DeepLabV3Plus, etc.)
- **Rich** augmentations (spatial, pixel, batch-level)
- **Experiment** tracking (CSV, W&B)
- **Checkpointing** and early stopping

### Model Architectures
- **Unet** - Classic encoder-decoder
- **UnetPlusPlus** - Nested skip connections
- **FPN** - Feature Pyramid Network
- **PSPNet** - Pyramid Scene Parsing
- **DeepLabV3Plus** - Atrous convolution
- **MAnet** - Multi-scale attention

### Encoder Options
- ResNet: `resnet18`, `resnet34`, `resnet50`, `resnet101`
- EfficientNet: `efficientnet-b0` through `efficientnet-b7`
- MobileNet: `mobilenet_v2`
- DenseNet: `densenet121`, `densenet169`, `densenet201`

### Common Options
| Option | Description | Example |
|--------|-------------|---------|
| `max_epochs` | Training epochs | `100` |
| `batch_size` | Batch size | `8`, `16`, `32` |
| `model.arch_name` | Architecture | `"Unet"`, `"FPN"` |
| `model.encoder_name` | Encoder backbone | `"resnet34"` |
| `optimizer.lr` | Learning rate | `0.001` |
| `auto_preprocess` | Run preprocessing | `true` |

### Output
```
outputs/runs/{run_id}/
├── model/
│   ├── best.pth        # Best model checkpoint
│   └── last.pth        # Last epoch checkpoint
├── logs/               # Training logs
├── train/              # Training data (from preprocess)
├── val/                # Validation data
└── metrics.json        # Training metrics
```

---

## Complete Pipeline Workflow

### Single-Task Workflow
```bash
# 1. Query images
agir-cvtoolkit query --db semif \
  --sample "stratified:by=category_common_name,per_group=100"

# 2. Generate masks
agir-cvtoolkit infer-seg

# 3. Upload to CVAT
agir-cvtoolkit upload-cvat

# 4. [Manual: Refine in CVAT]

# 5. Download refined masks
agir-cvtoolkit download-cvat \
  -o cvat_download.required_status=completed

# 6. Train model (auto-preprocessing)
agir-cvtoolkit train -o train.max_epochs=100

# 7. Use new model for inference
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=outputs/runs/train_xxx/model/best.pth
```

### Multi-Task Training Workflow
```bash
# 1. Segment barley batch
agir-cvtoolkit query --db semif --filters "species=barley"
agir-cvtoolkit infer-seg
agir-cvtoolkit upload-cvat

# 2. Segment wheat batch
agir-cvtoolkit query --db semif --filters "species=wheat"
agir-cvtoolkit infer-seg
agir-cvtoolkit upload-cvat

# 3. [Manual: Refine both in CVAT]

# 4. Download all completed tasks
agir-cvtoolkit download-cvat \
  -o cvat_download.required_status=completed

# 5. Train on combined dataset
agir-cvtoolkit train -o train.max_epochs=100
```

---

## Run Folder Structure

Every run creates a standardized folder:

```
outputs/runs/{project_name}/{subname}/
├── cfg.yaml                 # Full configuration
├── metrics.json             # Stage metrics
├── manifest.jsonl           # Run manifest
├── logs/                    # Execution logs
├── query/                   # Query results
│   ├── query.csv
│   └── query_spec.json
├── images/                  # Original images
├── masks/                   # Generated/refined masks
├── cvat_downloads/          # CVAT annotations
│   └── task_*/
├── train/                   # Training data
│   ├── images/
│   └── masks/
├── val/                     # Validation data
├── test/                    # Test data
└── model/                   # Trained models
    ├── best.pth
    └── checkpoints/
```

---

## Key Configuration Files

### Default Configs Location
```
src/agir_cvtoolkit/conf/
├── config.yaml              # Main config
├── io/default.yaml          # I/O settings
├── db/default.yaml          # Database settings
├── seg_inference/default.yaml  # Inference config
├── cvat_upload/default.yaml    # CVAT upload config
├── cvat_download/default.yaml  # CVAT download config
├── preprocess/default.yaml     # Preprocessing config
├── train/default.yaml          # Training config
└── augment/default.yaml        # Augmentation config
```

### Override Example
```bash
# Override via CLI
agir-cvtoolkit train \
  -o train.batch_size=16 \
  -o train.model.encoder_name="resnet50"

# Or edit config files directly in conf/
```

---

## Tips & Best Practices

### General
- **Run stages sequentially** - Each stage builds on previous outputs
- **Use same project name** - Keeps all stages in same run folder
- **Check metrics.json** - Review stage statistics after each run
- **Enable logging** - Set `log_level=INFO` or `DEBUG` for troubleshooting

### Query Stage
- Start with stratified sampling for balanced datasets
- Use `--preview` to test filters before full query
- Save `query_spec.json` for reproducibility

### Inference Stage
- Save images (`output.save_images=true`) if you'll need them later
- Adjust `batch_size` based on GPU memory

### CVAT Stages
- Download masks without images to save bandwidth
- Use `required_status=completed` to filter tasks
- Keep task names descriptive for tracking

### Preprocessing
- Let training auto-preprocess (easiest)
- Use multi-task aggregation for larger datasets
- Check `data_stats.json` for normalization values

### Training
- Start with `resnet34` encoder (good speed/accuracy)
- Enable visualizations for debugging data issues
- Use W&B logging for experiment tracking
- Monitor validation loss for early stopping

---

## Troubleshooting

### "Run not found"
- Check `outputs/runs/` for available runs
- Ensure project name matches previous stages

### "No data found"
- Verify previous stage completed successfully
- Check stage output folders exist

### "Out of memory"
- Reduce batch size: `-o train.batch_size=4`
- Reduce image size: `-o augment.train.img_size.height=512`

### "CVAT connection failed"
- Check `CVAT_HOST` and `CVAT_API_KEY` environment variables
- Verify CVAT server is accessible

### "Images not found during preprocessing"
- Run inference first with `output.save_images=true`
- Or download images from CVAT: `include_images=true`

---

## Additional Resources

- **Full Documentation**: `docs/README.md`
- **Query Guide**: `docs/db_query_usage.md`
- **Training Guide**: `docs/train_pipeline_usage.md`
- **Preprocessing Guide**: `docs/preprocessing_pipeline_usage.md`
- **CVAT Guide**: `docs/cvat_download_usage.md`

---

**Last Updated:** Based on AgIR-CVToolkit repository structure and documentation