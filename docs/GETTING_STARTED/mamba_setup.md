# Quick Guide for Mamba/Conda Users

Since you're using mamba (smart choice! 🚀), here's everything you need to know.

## ⚡ TL;DR - Fast Setup

```bash
# Create environment
mamba create -n agcv python=3.13 -y

# Activate
mamba activate agcv

# Install package
pip install -e ".[dev]"
```

## 📦 Two Installation Methods

### Method 1: Quick Install (Fastest)

```bash
mamba create -n agcv python=3.11 -y
mamba activate agcv
pip install -e ".[dev]"
```

**Pros**: Fastest, simplest
**When**: Quick testing or development

### Method 2: environment.yml (Recommended for Teams)

```bash
mamba env create -f environment.yml
mamba activate agcv
pip install -e .
```

**Pros**: Reproducible, shareable, optimized binaries
**When**: Production, team environments, HPC

## 📝 The environment.yml File

```yaml
name: agcv
channels:
  - conda-forge
  - nvidia      # for pytorch-cuda builds
  - defaults

dependencies:
  # === Core ===
  - python=3.13
  - pip

  # === Development / Testing ===
  - pytest
  - black
  - ruff
  - mypy

  # === Scientific / Computer Vision Stack ===
  - numpy
  - pillow
  - opencv
  - matplotlib

  # === Pip-installed Packages ===
  - pip:
      # ---- Configuration / CLI ----
      - hydra-core>=1.3
      - typer>=0.12
      - pydantic>=2.6
      - rich>=13

      # ---- Data Handling ----
      - pyarrow>=21.0.0
      - fastparquet>=2024.11.0

      # ---- CV / ML Core ----
      - torch>=2.8.0
      - torchmetrics==1.8.2
      - torchvision==0.23.0
      - albumentationsx>=2.0.12

      # ---- Segmentation / Deep Learning ----
      - segmentation-models-pytorch>=0.5.0
      - pytorch-lightning>=2.5.5

      # ---- Tools / SDKs ----
      - cvat-sdk>=2.14
      - GPUtil>=1.4.0
```

**Why split dependencies?**
- Conda packages (numpy, pandas): Optimized binaries, better performance
- Pip packages (pydantic, typer): Latest versions, better compatibility


## 🛠️ Common Tasks

### Update Package

```bash
mamba activate agcv
pip install -e ".[dev]" --upgrade
```

### Reinstall Package

```bash
mamba activate agcv
pip uninstall agcv
pip install -e ".[dev]"
```

### Update Environment

```bash
# If you have environment.yml
mamba env update -f environment.yml

# Or update specific package
mamba update numpy pandas
```

### Export Environment

For sharing with team:

```bash
# Full export
mamba env export > environment.lock.yml

# Or just package list
mamba list --export > requirements-conda.txt
pip freeze > requirements-pip.txt
```

## 🖥️ HPC-Specific Tips

### On SLURM Systems

```bash
# In your job script
#!/bin/bash
#SBATCH --job-name=agcv
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G

# Load conda/mamba module (system-specific)
module load mamba  # or conda, miniconda, etc.

# Activate environment
mamba activate agcv

# Run your job
agir-cv query --limit 10
```

## 🐛 Troubleshooting

### "Command not found: mamba"

**Install mamba**:
```bash
# From base conda
conda install mamba -n base -c conda-forge

# Or install Mambaforge
wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh
bash Mambaforge-Linux-x86_64.sh
```

### "Command not found: agcv"

**Solution**:
```bash
# Make sure environment is activated
mamba activate agcv
which python  # Should point to agcv env

# Reinstall
pip uninstall agir-cvtoolkit
pip install -e ".[dev]"
```

### "Solving environment: failed"

**Solution**:
```bash
# Clear cache
mamba clean --all

# Try again
mamba create -n agcv python=3.13 -y
```

## ✅ Verification Checklist

After setup, verify everything works:

```bash
# Environment exists
mamba env list | grep agcv

# Environment is activated
echo $CONDA_DEFAULT_ENV  # Should show: agcv

# Package is installed
pip show agir-cvtoolkit

# CLI works
agir-cv --help

# Python imports work
python -c "from agcv.config import Config; print('✓ Imports work')"

# Configuration loads
python -c "from agcv.config import Config; Config.from_yaml('conf/config.yaml')"

# Sample build works
agir-cv query --sample 5 --verbose
```

## 📊 Disk Space Management

Mamba/conda environments use more disk space:

```bash
# Check environment size
du -sh ~/.local/share/mamba/envs/agcv

# Clean unused packages
mamba clean --all

# Remove environment when done
mamba env remove -n agcv
```

Typical sizes:
- Base environment: ~500MB
- With dev dependencies: ~1GB
- With large packages (torch, etc.): 5-10GB

## 🌐 Working Across Systems

### Local Development

```bash
# On your laptop
mamba create -n agcv python=3.13 -y
mamba activate agcv
pip install -e ".[dev]"
```

### On HPC Cluster

```bash
# On cluster (load module first)
module load mamba
mamba create -n agcv python=3.13 -y
mamba activate agcv
pip install -e ".[dev]"
```

### In Docker (Optional)

Use the Mambaforge base image (see MAMBA_SETUP.md).

## ❓ FAQ

**Q: Should I use mamba or conda?**
A: Use mamba. It's faster and a drop-in replacement.

**Q: Can I use both mamba and conda?**
A: Yes, they share the same environments. But stick to one for consistency.

**Q: Why use pip inside mamba?**
A: Some packages are only on PyPI, or pip versions are newer. Mamba handles the Python environment, pip handles Python packages.

**Q: How do I uninstall?**
A: `mamba env remove -n agcv`

**Q: Can I rename the environment?**
A: Yes, but you'll need to update any scripts that reference "agcv".

**Q: How much disk space do I need?**
A: ~2GB for environment + database + logs.