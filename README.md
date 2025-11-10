# AgIR-CVToolkit

Agricultural Image Repository Computer Vision Toolkit - A pipeline for querying agricultural databases and running CV models.

## Quick Start

```bash
# Install
pip install -e .

# Query database
agir-cvtoolkit query --db semif --filters "state=NC"

# Run detection
agir-cvtoolkit infer-det

# Run inference
agir-cvtoolkit infer-seg

# Upload to CVAT
agir-cvtoolkit cvat-upload

# Download annotations
agir-cvtoolkit cvat-download
```

## Pipeline Stages

1. **Query** - Query SemiF/Field databases
2. **Inference** - Run segmentation models
3. **CVAT Upload** - Upload images for annotation
4. **CVAT Download** - Download refined annotations
5. **Preprocessing** - Prepare data for training
6. **Training** - Train models

## Documentation

Full documentation available in `docs/` directory:
- [Getting Started](docs_copy/GETTING_STARTED/installation.md)
- [Pipeline Overview](docs_copy/GETTING_STARTED/pipeline_overview.md)
- [Configuration Guide](docs_copy/CONFIGURATION/hydra_config_quick_ref.md)

## Structure

```
AgIR-CVToolkit/
├── src/agir_cvtoolkit/    # Main package
├── docs/                   # Full documentation
├── conf/                   # Configuration files
└── outputs/                # Pipeline outputs
```

## License

See LICENSE file for details.