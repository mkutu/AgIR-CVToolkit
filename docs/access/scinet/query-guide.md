---
layout: default
title: Setup & Query Guide
parent: SciNet Usage
grand_parent: Access & Query
nav_order: 1
---

# Using AgIR-CVToolkit Query on SciNet (Ceres)
{: .no_toc }

Complete guide for querying the AgIR dataset on SciNet Ceres cluster with data staged from Juno LTS.
{: .fs-6 .fw-300 }

**Author:** AgIR Team  
**Last Updated:** November 10, 2025

---

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The AgIR-CVToolkit provides powerful query capabilities for the AgIR dataset hosted on SciNet infrastructure. This guide covers:

- Accessing AgIR databases stored on **Juno LTS** (long-term storage)
- Staging data to **Ceres** cluster for computation
- Using **$TMPDIR** for fast local I/O during query processing
- Submitting **SLURM jobs** for efficient resource utilization
- Best practices for data management and performance optimization

### Workflow Summary

```
[Juno LTS: /LTS/project/<proj>]
         ↓ (Globus or DTN rsync)
[Ceres Tier-1: /project or /project/90daydata]
         ↓ (SLURM job preamble)
[Compute Node $TMPDIR: fast local SSD/NVMe]
         ↓ (query execution)
[Results → /project/<proj>/outputs]
         ↓ (optional archive)
[Juno LTS: /LTS/project/<proj>/results]
```

---

## Prerequisites

### Required Access

1. **SciNet Account**: Active account with Ceres cluster access
2. **Project Allocation**: Computational and storage quota on Ceres
3. **Juno LTS Access**: Access to AgIR datasets on Juno long-term storage
4. **SSH Configuration**: SSH keys configured for SciNet login

### Required Knowledge

- Basic Linux command line
- Understanding of SLURM job scheduler
- Familiarity with Python environments (Conda/Mamba)

### Verify Your Access

```bash
# Connect to Ceres
ssh <username>@ceres.scinet.usda.gov

# Check your allocations
lfs quota -u $USER /project/<project_name>
df -h /home/$USER
```

---

## SciNet Architecture for AgIR Workflow

### Storage Tiers

| Storage Location | Description | Backed Up | Mounted on Compute | Use Case |
|:----------------|:------------|:----------|:-------------------|:---------|
| **Juno LTS** `/LTS/project/<proj>` | Long-term storage | ✅ Yes | ❌ No | Archive, source data |
| **Tier-1** `/project/<proj>` | Active project space | ❌ No | ✅ Yes | Active work, databases |
| **90-day** `/project/90daydata/<proj>` | High-speed scratch | ❌ No | ✅ Yes | Staging area |
| **$TMPDIR** `/local/scratch/$USER` | Per-node local SSD | ❌ No | ✅ Yes (job only) | Fast I/O during compute |

### Key Rules

{: .important }
> - **Juno LTS** is NOT mounted on compute nodes → must stage data first
> - **Tier-1** (`/project`) is for active work and persistent storage
> - **90daydata** is purged after 90 days → use for temporary staging
> - **$TMPDIR** is auto-cleaned after each job → copy results back to Tier-1

### Data Transfer Nodes (DTNs)

For transferring data between Juno and Ceres, always use DTNs:

- **Ceres DTN**: `ceres-dtn.scinet.usda.gov`
- **Juno DTN**: `nal-dtn.scinet.usda.gov`

{: .warning }
> Never run transfers from login nodes or compute nodes.

---

## Initial Setup

### 1. Install Mambaforge in Project Space

Install Mambaforge once in your project directory for shared environment management:

```bash
# On Ceres login node
ssh <username>@ceres.scinet.usda.gov

# Download and install Mambaforge
cd /project/<project_name>
wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh
bash Mambaforge-Linux-x86_64.sh -b -p /project/<project_name>/miniforge3

# Initialize for bash
/project/<project_name>/miniforge3/bin/conda init bash
source ~/.bashrc

# Or initialize manually in scripts
source /project/<project_name>/miniforge3/etc/profile.d/conda.sh
```

### 2. Create AgIR-CVToolkit Environment

```bash
# Create dedicated environment for AgIR toolkit
mamba create -p /project/<project_name>/envs/agir_cv python=3.10 -c conda-forge

# Activate environment
mamba activate /project/<project_name>/envs/agir_cv

# Install AgIR-CVToolkit and dependencies
# Option A: Install from PyPI (when available)
pip install agir-cvtoolkit

# Option B: Install from source
cd /project/<project_name>
git clone https://github.com/yourusername/AgIR-CVToolkit.git
cd AgIR-CVToolkit
pip install -e .

# Verify installation
agir-cv --version
```

### 3. Configure Globus CLI (Recommended for Large Transfers)

```bash
# Install Globus CLI
pipx install globus-cli
# Or: pip install --user globus-cli

# Login with SciNet credentials
globus login

# Find and save endpoint UUIDs
globus endpoint search "SCINet-Juno"
globus endpoint search "SCINet-Ceres"

# Save as environment variables in your ~/.bashrc
echo 'export JUNO_EP="<JUNO_UUID>"' >> ~/.bashrc
echo 'export CERES_EP="<CERES_UUID>"' >> ~/.bashrc
source ~/.bashrc
```

#### Globus Endpoint Reference

Common SCINet Globus endpoints:

1. **SciNet-Juno**: Juno LTS storage
2. **SciNet-Ceres**: Ceres cluster
3. **SciNet-Atlas**: Atlas cluster (if needed)

---

## Data Staging from Juno LTS

AgIR databases are stored on Juno LTS and must be staged to Ceres before querying. Choose the appropriate method based on your workflow.

### Method 1: Selective File Staging via DTN (Command Line)

Use this when you have a specific list of files to transfer (e.g., from a database query).

#### Step 1: Generate File List on Ceres

```bash
# On Ceres login node
# Example: Query database to get list of image paths
cd /project/<project_name>

# If you have the database locally, query for paths
sqlite3 ~/meta/agir_semif.db \
  "SELECT rel_path FROM semif WHERE state='NC' AND category_common_name='barley';" \
  > staging_paths.txt

# Example output in staging_paths.txt:
# images/2024/NC/image001.jpg
# images/2024/NC/image002.jpg
# cutouts/2024/NC/cutout001.jpg
```

#### Step 2: Transfer Files via DTN

```bash
# SSH to Ceres DTN
ssh ceres-dtn.scinet.usda.gov

# Create staging directory
mkdir -p /project/90daydata/<project_name>/staged_data

# Transfer only listed files from Juno
# --files-from: reads relative paths from file
# --no-p --no-g: avoid permission/sgid issues
rsync -avz --no-p --no-g \
  --files-from=/project/<project_name>/staging_paths.txt \
  nal-dtn.scinet.usda.gov:/LTS/project/<project_name>/ \
  /project/90daydata/<project_name>/staged_data/

# Monitor transfer
watch -n 5 'ls -lh /project/90daydata/<project_name>/staged_data/ | tail -10'
```

### Method 2: Globus Transfer (Recommended for Large Datasets)

Use Globus for large transfers, resumable transfers, or when you need reliability.

#### Globus Web UI (Interactive)

1. Open [Globus Web App](https://app.globus.org) and log in with SciNet credentials
2. **Left pane**: Select `SCINet-Juno`, navigate to `/LTS/project/<project_name>/`
3. **Right pane**: Select `SCINet-Ceres`, navigate to `/project/90daydata/<project_name>/staged_data/`
4. Select files/folders and click **Start** to begin transfer
5. Monitor progress in the "Activity" tab

#### Globus CLI (Batch Transfer)

```bash
# Build batch file with source and destination pairs
# Example: transfer specific database and associated images

cat > transfer_pairs.txt <<'EOF'
/LTS/project/<project_name>/databases/agir_semif.db /project/90daydata/<project_name>/databases/agir_semif.db
/LTS/project/<project_name>/images/2024/NC/ /project/90daydata/<project_name>/images/2024/NC/
EOF

# Start batch transfer
globus transfer $JUNO_EP $CERES_EP --batch < transfer_pairs.txt \
  --label "AgIR data staging $(date +%F)" \
  --sync-level checksum

# Monitor transfer
globus task list
globus task show <TASK_ID>
```

#### Globus CLI with File List

```bash
# If you have a list of relative paths from a query
# Convert to Globus batch format

awk -v src="/LTS/project/<project_name>" \
    -v dst="/project/90daydata/<project_name>/staged_data" \
    '{print src "/" $0, dst "/" $0}' staging_paths.txt > globus_pairs.txt

# Start transfer
globus transfer $JUNO_EP $CERES_EP --batch < globus_pairs.txt \
  --label "AgIR selective staging $(date +%F)" \
  --sync-level checksum
```

### Method 3: Transfer Entire Database

For first-time setup or when you need the complete AgIR database:

```bash
# Via Globus (recommended for large transfers)
globus transfer $JUNO_EP:"/LTS/project/<project_name>/databases/" \
  $CERES_EP:"/project/<project_name>/databases/" \
  --recursive --label "AgIR database transfer" --sync-level checksum

# Or via DTN rsync (for smaller databases)
ssh ceres-dtn.scinet.usda.gov
rsync -avz --no-p --no-g \
  nal-dtn.scinet.usda.gov:/LTS/project/<project_name>/databases/ \
  /project/<project_name>/databases/
```

### Verify Staged Data

```bash
# Check space usage
df -h /project/90daydata/<project_name>
lfs quota -u $USER /project/<project_name>

# Verify file count and sizes
du -sh /project/90daydata/<project_name>/staged_data/
find /project/90daydata/<project_name>/staged_data/ -type f | wc -l

# Quick integrity check
ls -lh /project/90daydata/<project_name>/staged_data/
```

---

## Running Queries on Ceres

### Interactive Query (Development/Testing)

For testing queries or small datasets, use an interactive session:

```bash
# Request interactive session on Ceres
salloc --partition=short --nodes=1 --ntasks=4 --mem=16G --time=01:00:00

# Once on compute node, load environment
source /project/<project_name>/miniforge3/etc/profile.d/conda.sh
conda activate /project/<project_name>/envs/agir_cv

# Run query with database in /project
agir-cv query --db semif \
  -o db.semif.db_path=/project/<project_name>/databases/agir_semif.db \
  --filters "state=NC" \
  --filters "category_common_name=barley" \
  --limit 100 \
  --output json

# View results
ls -lh outputs/runs/*/query/

# Exit when done
exit
```

### Command-Line Query from Login Node (Small Queries Only)

{: .warning }
> **WARNING**: Only for very small queries. Use SLURM jobs for production work.

```bash
# On login node (limited resources)
source /project/<project_name>/miniforge3/etc/profile.d/conda.sh
conda activate /project/<project_name>/envs/agir_cv

# Quick query example
agir-cv query --db semif \
  -o db.semif.db_path=/project/<project_name>/databases/agir_semif.db \
  --filters "cutout_id=12345" \
  --limit 10 \
  --preview
```

---

## SLURM Job Submission

For production queries, especially with large datasets, **always use SLURM** to submit batch jobs. This ensures:

- Proper resource allocation
- Optimal I/O performance using $TMPDIR
- Respectful use of shared resources
- Job logging and reproducibility

### Basic Query Job Script

Create a SLURM batch script for running queries:

```bash
#!/bin/bash
#SBATCH --job-name=agir_query
#SBATCH --partition=short        # short: up to 2 days
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/query_%j.out
#SBATCH --error=logs/query_%j.err

# Exit on any error
set -euo pipefail

# Create logs directory if it doesn't exist
mkdir -p logs

# Load environment
module purge
source /project/<project_name>/miniforge3/etc/profile.d/conda.sh
conda activate /project/<project_name>/envs/agir_cv

# Set database path
DB_PATH="/project/<project_name>/databases/agir_semif.db"

echo "Starting query job at $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Database: $DB_PATH"

# Run query
agir-cv query --db semif \
  -o db.semif.db_path="$DB_PATH" \
  --filters "state=NC" \
  --filters "category_common_name=barley,wheat,rye" \
  --sample "stratified:by=category_common_name,per_group=100" \
  --output json

echo "Query completed at $(date)"
echo "Results saved to: outputs/runs/*/query/"
```

Submit the job:

```bash
# Create logs directory
mkdir -p logs

# Submit job
sbatch scripts/query_job.sh

# Monitor job
squeue -u $USER
watch -n 5 'squeue -u $USER'

# View output
tail -f logs/query_<job_id>.out
```

### Advanced: Using $TMPDIR for Fast I/O

For queries involving large datasets or image processing, stage data to $TMPDIR (node-local SSD) for maximum performance:

```bash
#!/bin/bash
#SBATCH --job-name=agir_query_tmpdir
#SBATCH --partition=short
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=logs/query_tmpdir_%j.out
#SBATCH --error=logs/query_tmpdir_%j.err

set -euo pipefail
mkdir -p logs

# Load environment
module purge
source /project/<project_name>/miniforge3/etc/profile.d/conda.sh
conda activate /project/<project_name>/envs/agir_cv

echo "Job started: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "TMPDIR: $TMPDIR"

# 1) Stage database to $TMPDIR (fast local SSD)
echo "Staging database to $TMPDIR..."
mkdir -p "$TMPDIR/databases"
rsync -av /project/<project_name>/databases/agir_semif.db "$TMPDIR/databases/"

# Optional: Stage image data if needed
# mkdir -p "$TMPDIR/images"
# rsync -av /project/90daydata/<project_name>/staged_data/images/ "$TMPDIR/images/"

echo "Data staging complete: $(date)"
df -h "$TMPDIR"

# 2) Run query using local database
echo "Running query from $TMPDIR..."
agir-cv query --db semif \
  -o db.semif.db_path="$TMPDIR/databases/agir_semif.db" \
  --filters "state=NC" \
  --filters "estimated_bbox_area_cm2>50" \
  --sample "stratified:by=category_family,per_group=200" \
  --output json \
  --output-dir "$TMPDIR/query_results"

echo "Query execution complete: $(date)"

# 3) Copy results back to persistent storage
echo "Copying results to persistent storage..."
OUTPUT_DIR="/project/<project_name>/outputs/${SLURM_JOB_ID}"
mkdir -p "$OUTPUT_DIR"
rsync -av "$TMPDIR/query_results/" "$OUTPUT_DIR/"

echo "Results copied to: $OUTPUT_DIR"
echo "Job completed: $(date)"

# Cleanup is automatic - $TMPDIR is wiped after job ends
```

Submit and monitor:

```bash
sbatch scripts/query_tmpdir_job.sh
squeue -u $USER
tail -f logs/query_tmpdir_<job_id>.out
```

### Query with Image Export

Export images based on query results:

```bash
#!/bin/bash
#SBATCH --job-name=agir_query_images
#SBATCH --partition=short
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=logs/query_images_%j.out

set -euo pipefail
mkdir -p logs

# Load environment
module purge
source /project/<project_name>/miniforge3/etc/profile.d/conda.sh
conda activate /project/<project_name>/envs/agir_cv

echo "Starting image export job: $(date)"
echo "Job ID: $SLURM_JOB_ID"

# Stage to $TMPDIR for fast I/O
mkdir -p "$TMPDIR/databases" "$TMPDIR/images" "$TMPDIR/results"

# Copy database
echo "Staging database..."
rsync -av /project/<project_name>/databases/agir_semif.db "$TMPDIR/databases/"

# Copy image data (adjust path to your actual image location)
echo "Staging images..."
rsync -av /project/90daydata/<project_name>/staged_data/images/ "$TMPDIR/images/"

# Run query with image export
echo "Running query with image export..."
agir-cv query --db semif \
  -o db.semif.db_path="$TMPDIR/databases/agir_semif.db" \
  -o paths.image_base_path="$TMPDIR/images" \
  --filters "state=NC,TX,GA" \
  --filters "category_group=weed" \
  --filters "blur_effect<30" \
  --sample "stratified:by=category_common_name,per_group=50" \
  --export-images \
  --output json \
  --output-dir "$TMPDIR/results"

# Copy results back
echo "Copying results to persistent storage..."
OUTPUT_DIR="/project/<project_name>/outputs/${SLURM_JOB_ID}"
mkdir -p "$OUTPUT_DIR"
rsync -av "$TMPDIR/results/" "$OUTPUT_DIR/"

echo "Results location: $OUTPUT_DIR"
echo "Job completed: $(date)"

# Summary
find "$OUTPUT_DIR" -type f | wc -l
du -sh "$OUTPUT_DIR"
```

### Monitoring Jobs

```bash
# View all your jobs
squeue -u $USER

# Detailed job info
scontrol show job <job_id>

# Job history
sacct -u $USER --format=JobID,JobName,State,Elapsed,MaxRSS

# Cancel a job
scancel <job_id>

# Monitor resource usage
sstat -j <job_id> --format=JobID,MaxRSS,AveCPU

# View output in real-time
tail -f logs/query_<job_id>.out
```

---

## Best Practices

### Data Management

1. **Use 90daydata for Staging**
   - Stage data from Juno to `/project/90daydata/<proj>` for temporary work
   - Promote to `/project/<proj>` only if needed long-term
   - Remember: 90daydata is purged after 90 days

2. **Leverage $TMPDIR for I/O-Intensive Work**
   - Copy databases and data to $TMPDIR at job start
   - Run queries from $TMPDIR for maximum performance
   - Copy results back to `/project` before job ends
   - $TMPDIR provides ~2TB local SSD per node

3. **Check Quotas Regularly**
   ```bash
   lfs quota -u $USER /project/<project_name>
   df -h /project/<project_name>
   df -h /project/90daydata/<project_name>
   ```

4. **Archive Results to Juno**
   ```bash
   # From Ceres DTN
   ssh ceres-dtn.scinet.usda.gov
   rsync -avz --no-p --no-g \
     /project/<project_name>/outputs/${SLURM_JOB_ID}/ \
     nal-dtn.scinet.usda.gov:/LTS/project/<project_name>/results/${SLURM_JOB_ID}/
   ```

### Resource Allocation

1. **Choose Appropriate Partition**
   - `short`: up to 48 hours
   - `medium`: up to 7 days
   - `long`: up to 21 days
   - `brief`: up to 2 hours (priority)

2. **Request Adequate Memory**
   - Small queries (<1000 records): 8-16 GB
   - Medium queries (1000-10000 records): 32-64 GB
   - Large queries (>10000 records): 64-128 GB
   - Add 20% buffer for safety

3. **CPU Allocation**
   - Most queries: 4-8 cores
   - Parallel processing: 16-32 cores
   - Match --ntasks to actual parallelism

### Query Optimization

1. **Use Selective Filters**
   ```bash
   # Good: Specific filters reduce data transfer
   --filters "state=NC,category_common_name=barley,blur_effect<30"
   
   # Avoid: Overly broad queries
   --filters "state=NC,TX,GA,FL,AL,SC"  # Too much data
   ```

2. **Leverage Sampling**
   ```bash
   # Stratified sampling for balanced datasets
   --sample "stratified:by=category_common_name,per_group=100"
   
   # Random sampling for large queries
   --sample "random:n=1000,seed=42"
   ```

3. **Preview Before Full Query**
   ```bash
   # Test query first
   agir-cv query --db semif \
     -o db.semif.db_path="$DB_PATH" \
     --filters "state=NC" \
     --preview 10
   ```

### Performance Tips

1. **Database Indexing**
   - Ensure databases have proper indexes
   - Query by indexed columns when possible (e.g., state, category_common_name)

2. **Batch Multiple Queries**
   - Instead of submitting many small jobs, batch queries together
   - Use array jobs for multiple similar queries

3. **Monitor I/O**
   ```bash
   # In your SLURM script, monitor disk usage
   echo "TMPDIR usage before query:"
   df -h "$TMPDIR"
   
   # After query
   echo "TMPDIR usage after query:"
   df -h "$TMPDIR"
   du -sh "$TMPDIR"/*
   ```

### File Organization

Organize your project directory:

```
/project/<project_name>/
├── databases/
│   ├── agir_semif.db
│   └── agir_field.db
├── miniforge3/
│   └── (mamba installation)
├── envs/
│   └── agir_cv/
├── scripts/
│   ├── query_job.sh
│   ├── query_tmpdir_job.sh
│   └── utils/
├── outputs/
│   ├── <job_id_1>/
│   ├── <job_id_2>/
│   └── ...
└── logs/
    ├── query_12345.out
    └── query_12345.err

/project/90daydata/<project_name>/
├── staged_data/
│   ├── images/
│   └── cutouts/
└── temp_results/
```

---

## Troubleshooting

### Common Issues

#### 1. "Permission Denied" Errors

```bash
# Fix: Ensure correct group ownership
chgrp -R <project_group> /project/<project_name>/
chmod -R g+rw /project/<project_name>/

# When using rsync, add --no-p --no-g
rsync -avz --no-p --no-g source/ destination/
```

#### 2. "Database is Locked"

```bash
# Multiple processes accessing same database
# Solution: Use $TMPDIR with individual copies per job
mkdir -p "$TMPDIR/databases"
cp /project/<project_name>/databases/agir_semif.db "$TMPDIR/databases/"
```

#### 3. "$TMPDIR Out of Space"

```bash
# Check space
df -h "$TMPDIR"

# Solution: Clean up intermediate files or request node with more local storage
# Ceres $TMPDIR typically has ~1.5-2 TB per node
```

#### 4. "Module Not Found" Errors

```bash
# Ensure environment is activated
source /project/<project_name>/miniforge3/etc/profile.d/conda.sh
conda activate /project/<project_name>/envs/agir_cv

# Verify installation
which python
python -c "import agir_cvtoolkit; print(agir_cvtoolkit.__version__)"
```

#### 5. Slow Data Transfer

```bash
# Use DTNs, never login nodes
ssh ceres-dtn.scinet.usda.gov

# Use Globus for large transfers
# Enable compression for rsync
rsync -avz --compress-level=9 source/ destination/

# Check network
ping -c 3 nal-dtn.scinet.usda.gov
```

#### 6. Job Killed Due to Memory

```bash
# Check actual memory usage
sacct -j <job_id> --format=JobID,MaxRSS,Elapsed

# Request more memory in next job
#SBATCH --mem=128G  # or higher
```

### Getting Help

1. **SciNet Support**
   - Website: [scinet.usda.gov](https://scinet.usda.gov)
   - Email: scinet-support@usda.gov
   - Provide job ID and error logs

2. **AgIR-CVToolkit Issues**
   - GitHub: [AgIR-CVToolkit Issues](https://github.com/yourusername/AgIR-CVToolkit/issues)
   - Include query command and error output

3. **Documentation**
   - [SciNet User Guides](https://scinet.usda.gov/guides/)
   - [Ceres User Manual](https://scinet.usda.gov/guides/use/running-jobs)
   - [Globus Documentation](https://docs.globus.org)

---

## Complete Workflow Example

Here's a complete end-to-end example for querying AgIR data on Ceres.

### Scenario

Query all high-quality barley images from North Carolina with bounding box area > 50 cm², export images, and archive results to Juno.

### Step 1: One-Time Setup

```bash
# Connect to Ceres
ssh user@ceres.scinet.usda.gov

# Install Mambaforge (if not done)
cd /project/agir_project
wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh
bash Mambaforge-Linux-x86_64.sh -b -p /project/agir_project/miniforge3
source /project/agir_project/miniforge3/etc/profile.d/conda.sh

# Create environment
mamba create -p /project/agir_project/envs/agir_cv python=3.10
mamba activate /project/agir_project/envs/agir_cv
pip install agir-cvtoolkit

# Setup Globus
pipx install globus-cli
globus login
export JUNO_EP="<your_juno_uuid>"
export CERES_EP="<your_ceres_uuid>"
```

### Step 2: Stage Database from Juno

```bash
# Transfer database via Globus
globus transfer $JUNO_EP:"/LTS/project/agir_project/databases/agir_semif.db" \
  $CERES_EP:"/project/agir_project/databases/agir_semif.db" \
  --label "AgIR database" --sync-level checksum

# Monitor
globus task list
```

### Step 3: Create Query Script

```bash
# Create script directory
mkdir -p /project/agir_project/scripts
cd /project/agir_project/scripts

# Create query job script
cat > query_barley_nc.sh <<'EOF'
#!/bin/bash
#SBATCH --job-name=query_barley_nc
#SBATCH --partition=short
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=../logs/query_barley_%j.out
#SBATCH --error=../logs/query_barley_%j.err

set -euo pipefail

# Setup
PROJECT_DIR="/project/agir_project"
mkdir -p "${PROJECT_DIR}/logs"

# Load environment
module purge
source ${PROJECT_DIR}/miniforge3/etc/profile.d/conda.sh
conda activate ${PROJECT_DIR}/envs/agir_cv

echo "=== Job Information ==="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Start time: $(date)"
echo "TMPDIR: $TMPDIR"

# Stage database to $TMPDIR
echo "=== Staging Data to TMPDIR ==="
mkdir -p "$TMPDIR/databases"
rsync -av "${PROJECT_DIR}/databases/agir_semif.db" "$TMPDIR/databases/"
echo "Database staged at: $(date)"

# Optional: Stage image data if doing image export
# mkdir -p "$TMPDIR/images"
# rsync -av /project/90daydata/agir_project/staged_data/images/ "$TMPDIR/images/"

# Run query
echo "=== Running Query ==="
agir-cv query --db semif \
  -o db.semif.db_path="$TMPDIR/databases/agir_semif.db" \
  --filters "state=NC" \
  --filters "category_common_name=barley" \
  --filters "estimated_bbox_area_cm2>50" \
  --filters "blur_effect<30" \
  --filters "has_masks=1" \
  --sample "stratified:by=estimated_area_bin,per_group=100" \
  --output json \
  --output-dir "$TMPDIR/results"

echo "Query completed at: $(date)"

# Copy results to persistent storage
echo "=== Copying Results ==="
OUTPUT_DIR="${PROJECT_DIR}/outputs/${SLURM_JOB_ID}"
mkdir -p "$OUTPUT_DIR"
rsync -av "$TMPDIR/results/" "$OUTPUT_DIR/"

echo "=== Summary ==="
echo "Output directory: $OUTPUT_DIR"
echo "Number of files: $(find $OUTPUT_DIR -type f | wc -l)"
echo "Total size: $(du -sh $OUTPUT_DIR | cut -f1)"
echo "Job completed: $(date)"
EOF

chmod +x query_barley_nc.sh
```

### Step 4: Submit Job

```bash
# Create logs directory
mkdir -p /project/agir_project/logs

# Submit job
cd /project/agir_project/scripts
sbatch query_barley_nc.sh

# Monitor
squeue -u $USER
watch -n 5 'squeue -u $USER'

# View output
tail -f /project/agir_project/logs/query_barley_*.out
```

### Step 5: Verify Results

```bash
# After job completes, check results
JOB_ID=<your_job_id>  # from squeue output
OUTPUT_DIR="/project/agir_project/outputs/${JOB_ID}"

# Examine query results
ls -lh "$OUTPUT_DIR"
cat "$OUTPUT_DIR/query/query_spec.json"
cat "$OUTPUT_DIR/query/summary.json"

# If images were exported
find "$OUTPUT_DIR" -name "*.jpg" | wc -l
```

### Step 6: Archive Results to Juno

```bash
# Transfer results back to Juno for long-term storage
ssh ceres-dtn.scinet.usda.gov

JOB_ID=<your_job_id>
rsync -avz --no-p --no-g \
  /project/agir_project/outputs/${JOB_ID}/ \
  nal-dtn.scinet.usda.gov:/LTS/project/agir_project/results/${JOB_ID}/

# Verify transfer
ssh nal-dtn.scinet.usda.gov "ls -lh /LTS/project/agir_project/results/${JOB_ID}/"

# Clean up staging area (optional)
rm -rf /project/90daydata/agir_project/staged_data/
```

### Step 7: Reproduce Query (Optional)

```bash
# Load query specification
cd "$OUTPUT_DIR/query"

# View query summary
python -m agir_cvtoolkit.pipelines.utils.query_utils summary query_spec.json

# Get reproduction command
python -m agir_cvtoolkit.pipelines.utils.query_utils reproduce query_spec.json

# This outputs the exact command to reproduce the query
```

---

## Summary

You now have a complete workflow for querying the AgIR dataset on SciNet Ceres:

✅ **Setup**: Mambaforge environment with AgIR-CVToolkit installed  
✅ **Data Staging**: Transfer data from Juno LTS to Ceres using Globus or DTN  
✅ **Query Execution**: Run queries via SLURM jobs with $TMPDIR for performance  
✅ **Results Management**: Archive outputs to Juno LTS for long-term storage  
✅ **Best Practices**: Efficient resource usage and data management  

### Quick Reference Commands

```bash
# Connect to Ceres
ssh user@ceres.scinet.usda.gov

# Activate environment
source /project/<project_name>/miniforge3/etc/profile.d/conda.sh
conda activate /project/<project_name>/envs/agir_cv

# Submit query job
sbatch scripts/query_job.sh

# Monitor job
squeue -u $USER
tail -f logs/query_<job_id>.out

# Check quotas
lfs quota -u $USER /project/<project_name>

# Archive to Juno (from DTN)
ssh ceres-dtn.scinet.usda.gov
rsync -avz /project/<project_name>/outputs/<job_id>/ \
  nal-dtn.scinet.usda.gov:/LTS/project/<project_name>/results/<job_id>/
```

### Additional Resources

- **SciNet Documentation**: [https://scinet.usda.gov/guides/](https://scinet.usda.gov/guides/)
- **AgIR-CVToolkit Docs**: [GitHub Repository](https://github.com/yourusername/AgIR-CVToolkit)
- **Globus Documentation**: [https://docs.globus.org](https://docs.globus.org)
- **SLURM Documentation**: [https://slurm.schedmd.com](https://slurm.schedmd.com)

---

{: .note }
> **Questions or Issues?**  
> SciNet Support: scinet-support@usda.gov  
> AgIR Team: [GitHub Issues](https://github.com/yourusername/AgIR-CVToolkit/issues)

**Last Updated:** November 10, 2025
