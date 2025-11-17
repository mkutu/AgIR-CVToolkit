---
layout: default
title: Installation & Setup
parent: Access & Query
nav_order: 1
---

# Installation & Setup
{: .no_toc }

Install and configure the AgIR-CVToolkit for database access.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## System Requirements

| Component | Requirement |
|-----------|-------------|
| **Python** | 3.10+ (3.13 recommended) |
| **OS** | Linux, macOS, or Windows with WSL2 |
| **RAM** | 8 GB minimum |
| **Storage** | Space for databases + outputs |

{: .note }
> GPU is not required for querying databases. GPU requirements apply only if using the full CV pipeline (inference, training).

---

## Installation

### Method: Conda/Mamba

For a controlled environment with all dependencies:

```bash
# Install mamba (faster than conda)
conda install mamba -n base -c conda-forge

# Clone repository
git clone https://github.com/your-org/AgIR-CVToolkit.git
cd AgIR-CVToolkit

# Create environment from file
mamba env create -f environment.yml
mamba activate agcv

# Install toolkit in editable mode
pip install -e .

# Verify installation
agir-cv --help
```

---

## Database Configuration

The toolkit needs to know where your database files are located. Choose one of the following methods:

### Option 1: Configuration File (Recommended)

Create a configuration file that persists database locations:

```bash
# Create config directory (if it doesn't exist)
mkdir -p src/agir_cvtoolkit/conf/db

# Create database config
cat > src/agir_cvtoolkit/conf/db/default.yaml << EOF
semif:
  db_path: /path/to/semif.db
  table: semif
field:
  db_path: /path/to/field.db
  table: field_data
EOF
```

**Example with actual paths:**

```yaml
# src/agir_cvtoolkit/conf/db/default.yaml
semif:
  db_path: /data/agir/AgIR_DB_v1_SemiF.db
  table: semif
field:
  db_path: /data/agir/AgIR_DB_v1_Field.db
  table: field_data
```

### Option 2: Command-Line Override

Specify database paths directly in each command:

```bash
agir-cv query --db semif \
  -o "db.semif.db_path=/path/to/semif.db"
```


{: .tip }
> **Recommended**: Use Option 1 (configuration file) for permanent setup. Use Option 2 for one-off queries or testing different databases.

---

## Verify Installation

### Test Database Connection

```bash
# Test SemiF database
agir-cv query --db semif --preview 5

# Test Field database
agir-cv query --db field --preview 5
```

**Expected output:**

```
============================================================
Preview: First 5 records
============================================================

[INFO] - Query stats (semif): rows_scanned=5 rows_returned=5
Record 1:
  ID: MD_1659702025
  Image: .../MD_1659702025.jpg
  category_common_name: giant foxtail
  state: MD
  estimated_bbox_area_cm2: 0.08
  ...
------------------------------------------------------------
```

### Test CLI Commands

```bash
# Check available commands
agir-cv --help

# Should show:
#   query        - Query databases
#   infer-seg    - Run segmentation inference
#   upload-cvat  - Upload to CVAT
#   download-cvat - Download from CVAT
#   preprocess   - Preprocess data
#   train        - Train models
```

### Test Python Import

```python
# test_install.py
from agir_cvtoolkit.core.db import AgirDB

# Test connection
try:
    with AgirDB.connect(
        db_type="semif",
        db_path="/path/to/semif.db",
        table="semif"
    ) as db:
        count = db.count()
        print(f"✅ Connected to SemiF: {count} records")
except Exception as e:
    print(f"❌ Error: {e}")
```

---

## Get Sample Databases

For testing and learning, use the sample databases included in the repository:

```bash
# Clone repository if you haven't already
git clone https://github.com/your-org/AgIR-CVToolkit.git
cd AgIR-CVToolkit

# Sample databases are in:
ls tests/data/db/

# Output:
#   AgIR_DB_v1_SemiF_sample_50.db
#   AgIR_DB_v1_Field_sample_10.db
```

**Update your config to use samples:**

```yaml
# src/agir_cvtoolkit/conf/db/default.yaml
semif:
  db_path: tests/data/db/AgIR_DB_v1_SemiF_sample_50.db
  table: semif
field:
  db_path: tests/data/db/AgIR_DB_v1_Field_sample_10.db
  table: field_data
```


---

## Output Directory

The toolkit automatically creates output directories when you run queries. No manual setup needed!

**Auto-generated structure:**

```
outputs/
└── runs/
    └── {project_name}/{subname}/
        ├── query/           # Query results
        │   ├── query.json
        │   ├── query.csv
        │   └── query_spec.json
        ├── cfg.yaml         # Configuration snapshot
        └── logs/            # Execution logs
```

---

## Troubleshooting

### Command Not Found

**Problem:** `agir-cv: command not found`

**Solutions:**

```bash
# 1. Check if installed
pip show agir-cvtoolkit

# 2. Use python -m syntax
python -m agir_cvtoolkit.cli --help

# 3. Activate environment
mamba activate agcv  # or: conda activate agcv

# 4. Reinstall if needed
mamba activate agcv
pip install --force-reinstall agir-cvtoolkit
```

### Database Not Found

**Problem:** `FileNotFoundError: Database not found`

**Solutions:**

```bash
# 1. Verify database exists
ls -lh /path/to/semif.db

# 2. Use absolute path
agir-cv query --db semif \
  -o "db.semif.db_path=/absolute/path/to/semif.db"

# 3. Check permissions
ls -l /path/to/semif.db
chmod 644 /path/to/semif.db  # Fix if needed
```

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'X'`

**Solutions:**

```bash
# 1. Install missing dependency
pip install <missing-package>

# 2. Check for conflicts
pip check

# 3. Create fresh environment
mamba create -n agcv-fresh python=3.13
mamba activate agcv-fresh
pip install agir-cvtoolkit
```

### Permission Denied

**Problem:** `PermissionError: Permission denied`

**Solutions:**

```bash
# Check and fix file permissions
ls -l /path/to/semif.db
chmod 644 /path/to/semif.db

# Check directory permissions
ls -ld /path/to/
chmod 755 /path/to/
```

---

## Update & Uninstall

### Update Toolkit

```bash
# Update toolkit within mamba environment
mamba activate agcv
pip install --upgrade agir-cvtoolkit
```

### Uninstall

```bash
# Uninstall package
pip uninstall agir-cvtoolkit

# Remove mamba/conda environment
mamba env remove -n agcv  # or: conda env remove -n agcv
```

---

## Next Steps

Now that you have the toolkit installed and configured:

1. **[Learn to Query →](query-tools.html)** - Filter, sample, and export data
2. **[View Examples →](query-tools.html#common-query-patterns)** - Common query patterns
3. **[Explore Schemas →](../dataset/)** - Understand database structure

---

## Additional Resources

### Documentation
- **[Query Guide](query-tools.html)** - Complete query documentation
- **[SemiF Schema](../dataset/semif.html)** - SemiF database fields
- **[Field Schema](../dataset/field.html)** - Field database fields
- **[Full Pipeline Docs](https://github.com/your-org/AgIR-CVToolkit)** - Complete toolkit features

### Support
- **GitHub Repository**: [AgIR-CVToolkit](https://github.com/your-org/AgIR-CVToolkit)
- **Issues**: [Report bugs](https://github.com/your-org/AgIR-CVToolkit/issues)
- **Discussions**: [Ask questions](https://github.com/your-org/AgIR-CVToolkit/discussions)

---

{: .note }
> This guide covers installation for database querying only. For the full CV pipeline (inference, annotation, training), see the [complete installation guide](https://github.com/your-org/AgIR-CVToolkit/docs/GETTING_STARTED/installation.md).