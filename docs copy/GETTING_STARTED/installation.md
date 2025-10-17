# Installation & Setup Guide

Complete guide to installing and configuring the AgIR-CVToolkit.

---

## 📋 System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Linux, macOS, or Windows with WSL2 |
| **Python** | 3.10 or higher (3.13 recommended) |
| **RAM** | 8 GB minimum (16+ GB recommended) |
| **Storage** | 10 GB free space for toolkit + datasets |

### Optional (for GPU acceleration)

| Component | Requirement |
|-----------|-------------|
| **GPU** | NVIDIA GPU with CUDA support |
| **CUDA** | 11.8 or higher |
| **VRAM** | 8+ GB for training |

---

## 🚀 Quick Install

### Option 1: Mamba Environment (Recommended)

```bash
# Install mamba if you don't have it
conda install mamba -n base -c conda-forge

# Clone the repository
git clone https://github.com/your-org/AgIR-CVToolkit.git
cd AgIR-CVToolkit

# Create environment from file (much faster than conda!)
mamba env create -f environment.yml
mamba activate agcv

# Install toolkit in editable mode
pip install -e .

# Verify installation
agir-cv --help
```

### Option 2: From Source

```bash
# Clone the repository
git clone https://github.com/your-org/AgIR-CVToolkit.git
cd AgIR-CVToolkit

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install toolkit in editable mode
pip install -e .

# Verify installation
agir-cvtoolkit --help
```

---

## 📦 Core Dependencies

The toolkit automatically installs these core dependencies:

### Environment Management

**Using Mamba (Recommended):** Mamba is a faster, drop-in replacement for conda. If you're using the `environment.yml` approach, install mamba first:

```bash
conda install mamba -n base -c conda-forge
```

Then use `mamba` instead of `conda` for all commands - it's significantly faster!

### Essential Packages
- **hydra-core** (≥1.3) - Configuration management
- **typer** (≥0.12) - CLI framework
- **pydantic** (≥2.6) - Data validation
- **rich** (≥13) - Terminal formatting
- **opencv-python** (≥4.9) - Image processing
- **numpy** (≥1.26) - Numerical computing
- **Pillow** (≥10.3) - Image I/O
- **sqlalchemy** (≥2.0) - Database interface

### Optional Packages

Install these for specific features:

```bash
# For CVAT integration
pip install cvat-sdk>=2.14

# For training models
pip install pytorch-lightning>=2.0.0 \
            segmentation-models-pytorch>=0.3.3 \
            torchmetrics \
            albumentations

# For experiment tracking
pip install wandb

# For data export
pip install pyarrow>=21.0 fastparquet>=2024.11.0
```

---

## 🔧 Configuration Setup

### 1. Database Configuration

Set up your database paths:

```bash
# Create database config
cat > src/agir_cvtoolkit/conf/db/default.yaml << EOF
semif:
  db_path: tests/data/db/AgIR_DB_v1_SemiF_sample_50_20251016.db
  table: semif
field:
  db_path: tests/data/db/AgIR_DB_v1_Field_sample_10_20251016.db
  table: field_data
EOF
```

Or specify database paths in your project config:

```yaml
# conf/config.yaml
db:
  semif:
    db_path: /path/to/semif.db
    table: semif
  field:
    db_path: /path/to/field.db
    table: field_data
```

### 2. CVAT API Configuration


For CVAT integration, set up your API credentials:
 
These environment variables configure access to a CVAT instance:
   - `CVAT_HOST`     : URL of the CVAT server (e.g. https://cvat.example.com)
   - `CVAT_USERNAME` : Username for authentication
   - `CVAT_PASSWORD` : Password or token for authentication

#### Option 1. Unix (temporary for current shell):
```sh
export CVAT_HOST="https://cvat.example.com"
export CVAT_USERNAME="alice"
export CVAT_PASSWORD="s3cr3t"
```

#### Option 2. Unix (persist across sessions):
   - Add the three export lines above to ~/.bashrc, ~/.profile, or ~/.zshrc
   - Then reload: source ~/.bashrc   (or open a new terminal)
.env file (example; do NOT commit to version control):

```
CVAT_HOST=https://cvat.example.com
CVAT_USERNAME=alice
CVAT_PASSWORD=s3cr3t
```

#### Option 3. Alternatively use a key file:

```bash
# Create keys file
mkdir -p .keys
cat > .keys/default.yaml << EOF
cvat:
  host: "https://app.cvat.ai"
  username: "your-username"
  password: "your-password"
  organization_slug: "your-org"  # Optional
EOF
```

**Security notes:**
   - Avoid committing credentials to source control.
   - Prefer using a secret manager or OS credential store for production.
   - If using CI, use the CI provider's secret storage and mask values in logs.
   - Consider using API tokens instead of plain passwords when supported.


### 3. Output Directory (Auto-Generated)

The toolkit **automatically creates** the workspace structure when you run commands. You don't need to create anything manually!

When you run your first command, the toolkit will generate:

```
outputs/
└── runs/
    └── {project_name}/{subname}/    # Auto-generated run folder
        ├── query/                    # Query results
        ├── masks/                    # Generated masks
        ├── images/                   # Images
        ├── cvat_downloads/           # CVAT annotations
        ├── train/                    # Training data
        ├── cfg.yaml                  # Run configuration
        └── logs/                     # Execution logs
```

---

## 🎮 GPU Setup (Optional)

### For CUDA-enabled Training

TODO

### Configure GPU Usage

Edit your training config:

```yaml
# conf/train/default.yaml
train:
  use_multi_gpu: false
  gpu:
    max_gpus: 1
    exclude_ids: []  # Or [0] to exclude GPU 0
```

---

## ✅ Verify Installation

### 1. Check CLI Access

```bash
# Check toolkit is installed
agir-cv --help

# Should show available commands:
#   query
#   infer-seg
#   upload-cvat
#   download-cvat
#   preprocess
#   train
```

### 2. Test Database Connection

```bash
# Test query (replace with your database path)
agir-cv query --db semif \
  -o "db.semif.db_path=/path/to/semif.db" \
  --preview 5
```

Expected output:
```
============================================================
Preview: First 5 records
============================================================

[2025-11-01 14:23:03,739][agir_cvtoolkit.core.db.agir_db][INFO] - Query stats (semif): rows_scanned=5 rows_returned=5 rows_invalid=0 query_ms=1
Record 1:
  ID: MD_1659702025
  Image: ...d-developed-images/MD_2022-08-05/images/MD_1659702025.jpg
  Mask: ...MD_2022-08-05/meta_masks/semantic_masks/MD_1659702025.png
  category_common_name: giant foxtail
  state: MD
  estimated_bbox_area_cm2: 0.08
  bbox_area_cm2: 0.00
  datetime: 2022:08:05 20:16:57
  category_family: Poaceae
  season: weeds_2022
  bbot_version: 2.0
  batch_id: MD_2022-08-05
  image_id: MD_1659702025
  fullres_height: 6368
  ... and 45 more fields
------------------------------------------------------------
```

### 3. Test Python API

```python
# test_installation.py
from agir_cvtoolkit.core.db import AgirDB

# Test database connection
try:
    with AgirDB.connect("semif", table="semif", db_path="path/to/semif.db") as db:
        count = db.count()
        print(f"✅ Database connected: {count} records")
except Exception as e:
    print(f"❌ Database error: {e}")

# Test database connection
try:
    with AgirDB.connect("field", table="field_data", db_path="path/to/field.db") as db:
        count = db.count()
        print(f"✅ Database connected: {count} records")
except Exception as e:
    print(f"❌ Database error: {e}")

# Test imports
try:
    from agir_cvtoolkit.pipelines.stages import query
    print("✅ Pipeline stages imported")
except Exception as e:
    print(f"❌ Import error: {e}")

print("\n✅ Installation verified!")
```

Run the test:
```bash
python test_installation.py
```

### 4. Test CVAT Connection (Optional)

```python
# test_cvat.py
import os
from cvat_sdk import make_client
from agir_cvtoolkit.pipelines.utils.hydra_utils import read_yaml
# Test CVAT connection
try:
    client = make_client(
        host=os.getenv("CVAT_HOST"),
        credentials=(os.getenv("CVAT_USERNAME"), os.getenv("CVAT_PASSWORD"))
    )
    print("✅ CVAT connected using env vars")
except Exception as e:
    print(f"❌ CVAT error using env vars: {e}")

try:
    keys = read_yaml("./.keys/default.yaml").get('cvat', {})
    client = make_client(
        host=keys.get("host"),
        credentials=(keys.get("username"), keys.get("password"))
    )
    print("✅ CVAT connected using keys file")
except Exception as e:
    print(f"❌ CVAT error using keys file: {e}")
```

---

## 🔥 Quick Start After Installation

### 1. Run Your First Query

The toolkit automatically creates all necessary directories!

```bash
# Just run a query - everything is created automatically
agir-cv query --db semif \
  --filters "state=NC" \
  --limit 10 \
  --out csv
```

### 2. Check Auto-Generated Output

```bash
# The toolkit automatically created this structure:
ls -R outputs/runs/

# You'll see:
#   outputs/runs/query_semif_XXXXX/
#       ├── query/
#       │   ├── query.csv         # Your results
#       │   ├── query_spec.json   # Reproducibility record
#       │   └── metrics.json      # Summary stats
#       ├── cfg.yaml              # Full configuration
#       └── logs/                 # Execution logs
```

### 3. Next Steps

The workspace is now set up! Continue with:

- **[5-Minute Quickstart](query_quickstart.md)** - Learn common query patterns
- **[Pipeline Overview](quick_refs/pipeline_overview.md)** - Understand the full workflow
- **[Database Documentation](DATABASES/)** - Explore available data

---

## 🐛 Troubleshooting

### Command Not Found

**Problem:** `agir-cv: command not found`

**Solutions:**
```bash
# Option 1: Reinstall toolkit
pip install --force-reinstall agir-cvtoolkit

# Option 2: Check PATH
which python
pip show agir-cvtoolkit

# Option 3: Use python -m
python -m agir_cvtoolkit.cli --help

# Option 4: Activate mamba/conda environment
mamba activate agcv  # or: conda activate agcv
```

### Database Connection Errors

**Problem:** `Database not found` or `No such table`

**Solutions:**
```bash
# 1. Verify database exists
ls -lh /path/to/semif.db

# 2. Check file permissions
chmod 644 /path/to/semif.db

# 3. Test with absolute path
agir-cv query --db semif \
  --sqlite-path /absolute/path/to/semif.db \
  --limit 1

# 4. Verify database integrity
sqlite3 /path/to/semif.db "SELECT COUNT(*) FROM semif;"
```

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'X'`

**Solutions:**
```bash
# Install missing dependency
pip install <missing-package>

# Reinstall all dependencies
pip install -r requirements.txt

# Check for conflicts
pip check

# Create fresh environment (using mamba - much faster!)
mamba create -n agcv-fresh python=3.13
mamba activate agcv-fresh
pip install agir-cv
```

### CVAT Connection Issues

**Problem:** `Authentication failed` or `Connection refused`

**Solutions:**
```bash
# 1. Verify credentials
echo $CVAT_HOST
echo $CVAT_API_KEY

# 2. Test API key in browser
# Visit: https://app.cvat.ai/api/docs

# 3. Check network connectivity
curl -I https://app.cvat.ai

# 4. Regenerate API key
# Go to CVAT Settings → API Keys → Create New
```

### GPU Not Detected

**Problem:** `CUDA not available` or training uses CPU

**Solutions:**
```bash
# 1. Check NVIDIA driver
nvidia-smi

# 2. Verify CUDA installation
nvcc --version

# 3. Test PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# 4. Reinstall PyTorch with CUDA
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 5. Check GPU config
agir-cv train --help
# Look for gpu.max_gpus option
```

### Permission Denied Errors

**Problem:** `Permission denied` when accessing files

**Solutions:**
```bash
# 1. Check file ownership
ls -l /path/to/database/

# 2. Fix permissions
chmod 755 /path/to/database/
chmod 644 /path/to/database/*.db

# 3. Run without sudo
# Don't use sudo with pip or conda!

# 4. Check output directory permissions
mkdir -p outputs/runs
chmod -R 755 outputs/
```

### Out of Memory Errors

**Problem:** Training or inference crashes with OOM

**Solutions:**
```bash
# Reduce batch size
agir-cv train -o train.batch_size=4

# Reduce image size
agir-cv train \
  -o preprocess.pad_gridcrop_resize.size.height=1024

# Use smaller model
agir-cv train -o train.model.encoder_name="resnet18"

# Reduce number of workers
agir-cv train -o train.num_workers=2

# Clear CUDA cache (in Python)
import torch
torch.cuda.empty_cache()
```

---

## 🔄 Updating

### Update to Latest Version

```bash
# Update via pip
pip install --upgrade agir-cvtoolkit

# Or update from source
cd agir-cvtoolkit
git pull
pip install -e .
```

### Update Dependencies

```bash
# Update all dependencies
pip install --upgrade -r requirements.txt

# Or update mamba/conda environment (mamba is faster!)
mamba env update -f environment.yml
mamba activate agcv

# Or with conda
conda env update -f environment.yml
conda activate agcv
```

---

## 🗑️ Uninstallation

### Remove Toolkit

```bash
# Uninstall package
pip uninstall agir-cvtoolkit

# Remove mamba/conda environment
mamba env remove -n agcv  # or: conda env remove -n agcv
```

---

## 📚 Additional Resources

### Documentation
- **[5-Minute Quickstart](query_quickstart.md)** - Get started fast
- **[Pipeline Overview](quick_refs/pipeline_overview.md)** - Complete workflow
- **[Configuration Guide](hydra_config_quick_ref.md)** - Advanced configuration

### Support
- **GitHub Issues**: Report bugs or request features
- **Documentation**: Check stage-specific guides
- **Community**: Join discussions

### Example Projects
- **Basic Query**: Simple database queries
- **Training Pipeline**: End-to-end model training
- **Multi-Task Workflow**: Combine multiple annotation batches

---

## ✨ Quick Reference

### Essential Commands

```bash
# Query database
agir-cv query --db semif --filters "state=NC" --limit 100

# Run inference
agir-cv infer-seg

# Upload to CVAT
agir-cv upload-cvat

# Download from CVAT
agir-cv download-cvat

# Preprocess data
agir-cv preprocess

# Train model
agir-cv train
```

### Essential Paths

All paths are **auto-generated** by the toolkit!

```bash
# Auto-generated outputs
outputs/runs/{run_id}/          # All pipeline outputs (created automatically)
outputs/runs/{run_id}/query/    # Query results
outputs/runs/{run_id}/masks/    # Generated masks

# Optional: Custom configuration (only if you need it)
conf/config.yaml                # Override default configs
.keys/default.yaml              # API credentials
```

### Essential Environment Variables

```bash
export CVAT_HOST="https://app.cvat.ai"
export CVAT_API_KEY="your-key"
export CUDA_VISIBLE_DEVICES="0"  # GPU selection
```

---

**🎉 Installation Complete!** You're ready to start using the AgIR-CVToolkit. Begin with the [5-Minute Quickstart](query_quickstart.md) to learn the basics.