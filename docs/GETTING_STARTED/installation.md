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
git clone https://github.com/your-org/agir-cvtoolkit.git
cd agir-cvtoolkit

# Create environment from file (much faster than conda!)
mamba env create -f environment.yml
mamba activate agcv

# Install toolkit in editable mode
pip install -e .

# Verify installation
agir-cvtoolkit --help
```

### Option 2: From Source

```bash
# Clone the repository
git clone https://github.com/your-org/agir-cvtoolkit.git
cd agir-cvtoolkit

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
# Create a configuration directory
mkdir -p ~/.agir-cvtoolkit

# Create database config
cat > ~/.agir-cvtoolkit/databases.yaml << EOF
databases:
  semif:
    path: /path/to/semif.db
  field:
    path: /path/to/field.db
EOF
```

Or specify database paths in your project config:

```yaml
# conf/config.yaml
db:
  semif:
    sqlite_path: /path/to/semif.db
  field:
    sqlite_path: /path/to/field.db
```

### 2. CVAT API Configuration

For CVAT integration, set up your API credentials:

```bash
# Option A: Environment variables (recommended)
export CVAT_HOST="https://app.cvat.ai"
export CVAT_API_KEY="your-api-key-here"

# Option B: Create keys file
mkdir -p .keys
cat > .keys/default.yaml << EOF
cvat:
  host: "https://app.cvat.ai"
  api_key: "your-api-key-here"
  organization_slug: "your-org"  # Optional
EOF
```

**Getting your CVAT API key:**
1. Log into CVAT (https://app.cvat.ai)
2. Go to Settings → API Keys
3. Create a new key
4. Copy and save it securely

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

**You only need to:**
```bash
# Create a working directory
mkdir my-agir-project
cd my-agir-project

# Everything else is created automatically!
```

---

## 🎮 GPU Setup (Optional)

### For CUDA-enabled Training

```bash
# Install PyTorch with CUDA support
# Visit https://pytorch.org/get-started/locally/ for the latest command

# For CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Verify GPU is available
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

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
agir-cvtoolkit --help

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
agir-cvtoolkit query --db semif \
  --sqlite-path /path/to/semif.db \
  --limit 5 \
  --preview 5
```

Expected output:
```
Connecting to SemiF database...
Preview (first 5 records):
  cutout_id_001: barley (NC)
  cutout_id_002: wheat (NC)
  ...
```

### 3. Test Python API

```python
# test_installation.py
from agir_cvtoolkit.core.db import AgirDB

# Test database connection
try:
    with AgirDB.connect("semif", sqlite_path="/path/to/semif.db") as db:
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

# Test CVAT connection
try:
    client = make_client(
        host=os.getenv("CVAT_HOST"),
        credentials=(os.getenv("CVAT_USERNAME"), os.getenv("CVAT_PASSWORD"))
    )
    print("✅ CVAT connected")
except Exception as e:
    print(f"❌ CVAT error: {e}")
```

---

## 🔥 Quick Start After Installation

### 1. Run Your First Query

The toolkit automatically creates all necessary directories!

```bash
# Just run a query - everything is created automatically
agir-cvtoolkit query --db semif \
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

**Problem:** `agir-cvtoolkit: command not found`

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
agir-cvtoolkit query --db semif \
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
pip install agir-cvtoolkit
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
agir-cvtoolkit train --help
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
agir-cvtoolkit train -o train.batch_size=4

# Reduce image size
agir-cvtoolkit train \
  -o preprocess.pad_gridcrop_resize.size.height=1024

# Use smaller model
agir-cvtoolkit train -o train.model.encoder_name="resnet18"

# Reduce number of workers
agir-cvtoolkit train -o train.num_workers=2

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

# Check version
agir-cvtoolkit --version
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

# Remove configuration (optional)
rm -rf ~/.agir-cvtoolkit

# Remove your working directory (optional)
rm -rf my-agir-project/
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
agir-cvtoolkit query --db semif --filters "state=NC" --limit 100

# Run inference
agir-cvtoolkit infer-seg

# Upload to CVAT
agir-cvtoolkit upload-cvat

# Download from CVAT
agir-cvtoolkit download-cvat

# Preprocess data
agir-cvtoolkit preprocess

# Train model
agir-cvtoolkit train
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