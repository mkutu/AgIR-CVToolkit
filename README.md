# AgIR-CVToolkit Documentation

**Agricultural Image Research Computer Vision Toolkit** - A unified pipeline for querying agricultural databases, running CV models, and managing annotation workflows.

---

## 🚀 Quick Start

**New to the toolkit?** Start here:

1. **[5-Minute Quickstart](query_quickstart.md)** - Get up and running with common examples
2. **[Pipeline Overview](quick_refs/pipeline_overview.md)** - Understand the complete workflow
3. **[Repository Structure](repo_skeleton.md)** - Learn how the codebase is organized

---

## 📚 Documentation Structure

### **Core Pipeline Stages**

Complete guides for each stage of the CV pipeline:

| Stage | Guide | Purpose |
|-------|-------|---------|
| **1. Query** | [Query Guide](db_query_usage.md) | Query SemiF/Field databases with filters and sampling |
| **2. Inference** | [Inference Guide](seg_inference_quickstart.md) | Run segmentation models to generate masks |
| **3. CVAT Upload** | [Upload Guide](cvat_upload_usage.md) | Upload images + prelabels to CVAT |
| **4. CVAT Download** | [Download Guide](cvat_download_usage.md) | Download refined annotations from CVAT |
| **5. Preprocessing** | [Preprocessing Guide](preprocessing_pipeline_usage.md) | Prepare data for training |
| **6. Training** | [Training Guide](train_pipeline_usage.md) | Train segmentation models |

### **Database Documentation** 📊

Understanding your data sources:

- **[SemiF Database Documentation](semif_database_documentation.md)**
  - 62 columns covering cutout images, bounding boxes, taxonomy, quality metrics
  - Optimized for machine learning training with precise annotations
  - Primary use: Object detection and weed segmentation

- **[Field Database Documentation](field_database_documentation.md)**
  - 72 columns with comprehensive agricultural context
  - Multi-stage quality control workflows
  - Primary use: Field observation research and phenological tracking

### **Configuration & Reproducibility** ⚙️

- **[Hydra Configuration Guide](hydra_config_quick_ref.md)** - Multi-stage workflow configs
- **[Query Specifications Guide](query_specs_quick_reference.md)** - Reproducible queries with `query_spec.json`

### **Quick References** ⚡

Fast lookups and common patterns:

- **[Complete Pipeline Overview](quick_refs/pipeline_overview.md)** - All stages, examples, troubleshooting
- **[CVAT Upload Quick Start](quick_refs/cvat_upload_quick_start.md)** - Fast CVAT upload patterns
- **[Query Examples Guide](query_example_guide.md)** - 20+ query patterns from basic to advanced
- **[All Quick References](quick_refs/quick_refs_all.md)** - Consolidated quick reference guide

### **Design & Architecture** 🏗️

Technical design documents:

- **[Architecture Decision Records](design/adr/0001-foundation.md)** - Foundation decisions
- **[Feature Requirements (FR-01)](design/FR-01.md)** - Database query and file staging specs
- **[Repository Skeleton](repo_skeleton.md)** - Codebase structure
- **[Roadmap](roadmap.md)** - Future features and milestones

---

## 🎯 Common Workflows

### **Complete ML Pipeline**

Train a segmentation model from scratch:

```bash
# 1. Query database for balanced dataset
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --sample "stratified:by=category_common_name,per_group=50"

# 2. Run inference with existing model
agir-cvtoolkit infer-seg \
  -o seg_inference.output.save_images=true

# 3. Upload to CVAT for human refinement
agir-cvtoolkit upload-cvat \
  -o cvat_upload.project_id=12345

# [Manually refine masks in CVAT web interface]

# 4. Download refined annotations
agir-cvtoolkit download-cvat \
  -o cvat_download.required_status=completed

# 5. Train improved model (auto-preprocessing)
agir-cvtoolkit train \
  -o train.max_epochs=100 \
  -o train.batch_size=8

# 6. Use new model for inference
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=outputs/runs/train_xxx/model/best.pth
```

### **Multi-Species Training**

Combine multiple annotation batches:

```bash
# Annotate barley
agir-cvtoolkit query --db semif --filters "category_common_name=barley"
agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true
agir-cvtoolkit upload-cvat -o cvat_upload.task_name="Barley_Batch"

# Annotate wheat
agir-cvtoolkit query --db semif --filters "category_common_name=wheat"
agir-cvtoolkit infer-seg -o seg_inference.output.save_images=true
agir-cvtoolkit upload-cvat -o cvat_upload.task_name="Wheat_Batch"

# [Refine both in CVAT]

# Download and train on combined dataset (automatic!)
agir-cvtoolkit download-cvat
agir-cvtoolkit train
```

---

## 🔍 Find What You Need

### **I want to...**

#### **Query the Database**
- [Filter by species, state, or date](db_query_usage.md#simple-equality-filters)
- [Use stratified sampling](db_query_usage.md#stratified-sampling)
- [Reproduce a previous query](query_specs_quick_reference.md#reproducing-queries)
- [See query examples](query_example_guide.md)
- [Understand SemiF schema](semif_database_documentation.md)
- [Understand Field schema](field_database_documentation.md)

#### **Run Models**
- [Run segmentation inference](seg_inference_quickstart.md)
- [Use custom model checkpoints](seg_inference_quickstart.md#using-custom-models)
- [Adjust batch size and GPU settings](seg_inference_quickstart.md#configuration)

#### **Annotate Data**
- [Upload to CVAT](cvat_upload_usage.md)
- [Download from CVAT](cvat_download_usage.md)
- [Combine multiple annotation batches](preprocessing_pipeline_usage.md#multi-task-aggregation)

#### **Train Models**
- [Train segmentation models](train_pipeline_usage.md)
- [Preprocess training data](preprocessing_pipeline_usage.md)
- [Configure data augmentation](train_pipeline_usage.md#augmentation)
- [Use different model architectures](train_pipeline_usage.md#model-configuration)

#### **Troubleshoot**
- [Query issues](query_example_guide.md#common-issues)
- [CVAT connection problems](cvat_download_usage.md#troubleshooting)
- [Training errors](train_pipeline_usage.md#troubleshooting)
- [Preprocessing issues](preprocessing_pipeline_usage.md#troubleshooting)

#### **Understand the System**
- [See complete pipeline overview](quick_refs/pipeline_overview.md)
- [Learn Hydra configuration](hydra_config_quick_ref.md)
- [Understand repository structure](repo_skeleton.md)
- [Check project roadmap](roadmap.md)

---

## 📊 Database Quick Reference

### **SemiF Database**
- **Records**: Individual plant cutouts with bounding boxes
- **Columns**: 62 (taxonomy, spatial data, quality metrics)
- **Key Fields**: `cutout_id`, `category_common_name`, `state`, `estimated_bbox_area_cm2`
- **Use Case**: Machine learning training, object detection

### **Field Database**
- **Records**: Field observation specimens with context
- **Columns**: 72 (agricultural context, phenology, quality control)
- **Key Fields**: `id`, `common_name`, `us_state`, `growth_stage`, `crop_type_secondary`
- **Use Case**: Agricultural research, field monitoring

[→ Full SemiF Documentation](semif_database_documentation.md) | [→ Full Field Documentation](field_database_documentation.md)

---

## 🛠️ Configuration Files

```
AgIR-CVToolkit/
├── conf/
│   ├── config.yaml              # Main Hydra config
│   ├── query/default.yaml       # Query settings
│   ├── seg_inference/default.yaml  # Inference settings
│   ├── cvat_upload/default.yaml    # CVAT upload settings
│   ├── cvat_download/default.yaml  # CVAT download settings
│   ├── preprocess/default.yaml     # Preprocessing settings
│   ├── train/default.yaml          # Training settings
│   └── augment/default.yaml        # Data augmentation
```

[→ Configuration Guide](hydra_config_quick_ref.md)

---

## 📁 Output Structure

```
outputs/runs/{project_name}/{subname}/
├── query/
│   ├── query.csv              # Query results
│   ├── query_spec.json        # Reproducibility record
│   └── metrics.json           # Summary statistics
├── masks/                     # Generated segmentation masks
├── images/                    # Original or staged images
├── cvat_downloads/            # Downloaded CVAT annotations
│   ├── task_1/
│   └── task_2/
├── train/                     # Training split
│   ├── images/
│   └── masks/
├── val/                       # Validation split
├── test/                      # Test split
├── checkpoints/               # Training checkpoints
├── model/                     # Exported model weights
├── cfg.yaml                   # Complete run configuration
└── logs/                      # Execution logs
```

---

## ✨ Best Practices

### **For Reproducibility**
- ✅ Always save `query_spec.json` with datasets
- ✅ Use `project.name` and `project.subname` for organization
- ✅ Keep `cfg.yaml` for complete run history
- ✅ Document model checkpoints with version numbers

### **For Performance**
- ✅ Use stratified sampling for balanced datasets
- ✅ Save images during inference (faster than re-reading)
- ✅ Use appropriate tile sizes based on GPU memory
- ✅ Enable multiprocessing for preprocessing

### **For Iteration**
- ✅ Start with small validation sets
- ✅ Use same project for multiple annotation rounds
- ✅ Incrementally increase dataset size
- ✅ Track metrics at each iteration

---

## 🆘 Getting Help

1. **Check the relevant guide** - Use the table above to find your stage
2. **Review examples** - See [Query Examples](query_example_guide.md) or [Pipeline Overview](quick_refs/pipeline_overview.md)
3. **Check troubleshooting** - Each guide has a troubleshooting section
4. **Examine logs** - Located in `outputs/runs/{run_id}/logs/`
5. **Verify metrics** - Check `metrics.json` after each stage

---

## 🔗 Quick Links

| Topic | Link |
|-------|------|
| **Getting Started** | [5-Minute Quickstart](query_quickstart.md) |
| **Complete Pipeline** | [Pipeline Overview](quick_refs/pipeline_overview.md) |
| **Database Schemas** | [SemiF](semif_database_documentation.md) \| [Field](field_database_documentation.md) |
| **Query System** | [Guide](db_query_usage.md) \| [Examples](query_example_guide.md) \| [Specs](query_specs_quick_reference.md) |
| **CVAT Integration** | [Upload](cvat_upload_usage.md) \| [Download](cvat_download_usage.md) |
| **Training** | [Train Guide](train_pipeline_usage.md) \| [Preprocess Guide](preprocessing_pipeline_usage.md) |
| **Configuration** | [Hydra Guide](hydra_config_quick_ref.md) |
| **Architecture** | [Repo Structure](repo_skeleton.md) \| [Design Docs](design/adr/0001-foundation.md) \| [Roadmap](roadmap.md) |

---

## 📝 Version Information

**Current Version**: v1.0  
**Last Updated**: October 2025

**Toolkit Components**:
- Query System (v1.0)
- Segmentation Inference (v1.0)
- CVAT Integration (v1.0)
- Preprocessing Pipeline (v1.0)
- Training Pipeline (v1.0)

**Coming Soon**:
- Detection models support
- Multi-modal inputs
- Automated experiment tracking
- Production deployment guides

---

## 📄 License & Support

For issues, questions, or contributions:
1. Review this documentation
2. Check stage-specific troubleshooting guides
3. Examine execution logs and metrics
4. Consult design documents for architectural questions

**Remember**: Run a complete mini-pipeline on 10 images first to validate your setup before scaling up! 🚀