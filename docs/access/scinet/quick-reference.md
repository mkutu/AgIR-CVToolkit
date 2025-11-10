---
layout: default
title: Quick Reference
parent: SciNet Usage
grand_parent: Access & Query
nav_order: 2
---

# AgIR-CVToolkit on SciNet - Quick Reference
{: .no_toc }

One-page reference for common SciNet + AgIR-CVToolkit commands and workflows.
{: .fs-6 .fw-300 }

---

## Common Commands

### Environment Setup

```bash
# Activate environment
source /project/<project_name>/miniforge3/etc/profile.d/conda.sh
conda activate /project/<project_name>/envs/agir_cv

# Verify installation
agir-cv --version
which python
```

### Data Transfer

```bash
# Check Globus endpoints
globus endpoint search SCINet-Juno
globus endpoint search SCINet-Ceres

# Transfer via Globus CLI
globus transfer $JUNO_EP:"/LTS/project/<proj>/source/" \
  $CERES_EP:"/project/<proj>/dest/" \
  --recursive --label "My transfer" --sync-level checksum

# Transfer via DTN rsync
ssh ceres-dtn.scinet.usda.gov
rsync -avz --no-p --no-g \
  nal-dtn.scinet.usda.gov:/LTS/project/<proj>/source/ \
  /project/<proj>/dest/
```

### Storage Locations

```bash
# Check quotas
lfs quota -u $USER /project/<project_name>
df -h /project/<project_name>
df -h /project/90daydata/<project_name>

# Check TMPDIR (only in jobs)
echo $TMPDIR
df -h $TMPDIR
```

### Job Management

```bash
# Submit job
sbatch script.sh

# Check queue
squeue -u $USER

# Job details
scontrol show job <job_id>

# Cancel job
scancel <job_id>

# Job history
sacct -u $USER --format=JobID,JobName,State,Elapsed,MaxRSS

# Real-time output
tail -f logs/job_<job_id>.out
```

### Query Commands

```bash
# Simple query
agir-cv query --db semif \
  -o db.semif.db_path=/project/<proj>/databases/agir_semif.db \
  --filters "state=NC" \
  --limit 100

# Stratified sampling
agir-cv query --db semif \
  -o db.semif.db_path=/project/<proj>/databases/agir_semif.db \
  --filters "state=NC,TX,GA" \
  --sample "stratified:by=category_common_name,per_group=50"

# Preview results
agir-cv query --db semif \
  -o db.semif.db_path=/project/<proj>/databases/agir_semif.db \
  --filters "state=NC" \
  --preview 10
```

---

## SLURM Script Template

```bash
#!/bin/bash
#SBATCH --job-name=my_query
#SBATCH --partition=short
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail
mkdir -p logs

# Load environment
module purge
source /project/<proj>/miniforge3/etc/profile.d/conda.sh
conda activate /project/<proj>/envs/agir_cv

# Your commands here
echo "Job started: $(date)"
# ... query commands ...
echo "Job finished: $(date)"
```

---

## Using $TMPDIR Template

```bash
#!/bin/bash
#SBATCH --job-name=query_tmpdir
#SBATCH --partition=short
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --mem=64G
#SBATCH --time=06:00:00

set -euo pipefail

# Load environment
source /project/<proj>/miniforge3/etc/profile.d/conda.sh
conda activate /project/<proj>/envs/agir_cv

# 1) Stage to TMPDIR
echo "Staging to $TMPDIR..."
mkdir -p "$TMPDIR/databases"
rsync -av /project/<proj>/databases/agir_semif.db "$TMPDIR/databases/"

# 2) Run query from TMPDIR
echo "Running query..."
agir-cv query --db semif \
  -o db.semif.db_path="$TMPDIR/databases/agir_semif.db" \
  --filters "state=NC" \
  --output-dir "$TMPDIR/results"

# 3) Copy results back
echo "Copying results..."
OUTPUT_DIR="/project/<proj>/outputs/${SLURM_JOB_ID}"
mkdir -p "$OUTPUT_DIR"
rsync -av "$TMPDIR/results/" "$OUTPUT_DIR/"

echo "Results: $OUTPUT_DIR"
```

---

## Common Filters

```bash
# Location
--filters "state=NC"
--filters "state=NC,TX,GA"

# Species
--filters "category_common_name=barley"
--filters "category_common_name=barley,wheat,rye"
--filters "category_group=weed"
--filters "category_family=Poaceae"

# Quality
--filters "blur_effect<30"
--filters "has_masks=1"
--filters "is_primary=1"

# Size
--filters "estimated_bbox_area_cm2>50"
--filters "estimated_area_bin=large"

# Combined
--filters "state=NC,category_common_name=barley,blur_effect<30,has_masks=1"
```

---

## Sampling Strategies

```bash
# Random sample
--sample "random:n=1000"
--sample "random:n=1000,seed=42"

# Stratified by single field
--sample "stratified:by=category_common_name,per_group=100"
--sample "stratified:by=state,per_group=50"

# Stratified by multiple fields
--sample "stratified:by=category_common_name,by=estimated_area_bin,per_group=20"
```

---

## Archive to Juno

```bash
# From Ceres DTN
ssh ceres-dtn.scinet.usda.gov

JOB_ID=<your_job_id>
rsync -avz --no-p --no-g \
  /project/<proj>/outputs/${JOB_ID}/ \
  nal-dtn.scinet.usda.gov:/LTS/project/<proj>/results/${JOB_ID}/
```

---

## Troubleshooting

```bash
# Check module availability
module avail

# Check Python environment
which python
python -c "import agir_cvtoolkit; print(agir_cvtoolkit.__version__)"

# Check job resources
sstat -j <job_id> --format=JobID,MaxRSS,AveCPU

# View job efficiency
seff <job_id>

# Check failed jobs
sacct -u $USER --state=FAILED --format=JobID,JobName,Elapsed,ExitCode
```

---

## Key Paths

```bash
# Storage tiers
/LTS/project/<proj>                    # Juno LTS (backed up)
/project/<proj>                        # Ceres Tier-1 (not backed up)
/project/90daydata/<proj>              # Ceres 90-day scratch
$TMPDIR                                # Node-local SSD (job only)

# DTNs
ceres-dtn.scinet.usda.gov             # Ceres data transfer node
nal-dtn.scinet.usda.gov               # Juno data transfer node

# Typical project structure
/project/<proj>/
├── databases/                         # AgIR databases
├── miniforge3/                        # Mamba installation
├── envs/agir_cv/                      # Toolkit environment
├── scripts/                           # Job scripts
├── outputs/                           # Query results
└── logs/                              # Job logs
```

---

## Resource Guidelines

| Query Size | Memory | CPUs | Partition |
|:-----------|:-------|:-----|:----------|
| Small (<1K records) | 8-16 GB | 4 cores | short |
| Medium (1K-10K) | 32-64 GB | 4-8 cores | short |
| Large (>10K) | 64-128 GB | 8-16 cores | short/medium |

**Time Limits:**
- `brief`: 2 hours
- `short`: 48 hours  
- `medium`: 7 days
- `long`: 21 days

---

## Support

- **SciNet**: scinet-support@usda.gov | [scinet.usda.gov](https://scinet.usda.gov)
- **AgIR Toolkit**: [GitHub Issues](https://github.com/yourusername/AgIR-CVToolkit/issues)
- **Full Documentation**: [Complete Setup & Query Guide](query-guide.html)

---

{: .note }
> **Tip**: Save this page as a bookmark for quick access, or download and keep as `~/agir_quick_ref.md` on Ceres!
