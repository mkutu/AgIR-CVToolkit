---
layout: default
title: SciNet Usage
parent: Access & Query
nav_order: 3
has_children: true
---

# Using AgIR on SciNet
{: .no_toc }

Complete guides for accessing and querying the AgIR dataset on USDA's SciNet HPC infrastructure.
{: .fs-6 .fw-300 }

---

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

--- 

## Overview

The AgIR dataset is hosted on SciNet, USDA's high-performance computing infrastructure. This section provides comprehensive documentation for:

- **Setting up** your SciNet environment
- **Staging data** from Juno LTS to Ceres cluster
- **Running queries** using the AgIR-CVToolkit
- **Submitting SLURM jobs** for efficient computation
- **Managing data** across storage tiers

{: .note }
> **Prerequisites**: SciNet account with access to Ceres cluster and Juno LTS storage.

---

## Data Structure on JUNO

The AgIR dataset on JUNO consists of two components:

**1. Database:** SQLite database containing metadata and file paths to the actual data. Copy this to your local user space for querying.
```bash
# Copy database to your user space
cp /juno/lts/agir/database/agir_database.db ~/agir/
```

**2. Physical Data:** Image files, annotations, and derived products stored in JUNO long-term storage. Access these directly using paths from database queries.

**Workflow:**
1. Copy the database to your SciNet user directory
2. Query the database to find images matching your criteria  
3. Access physical data files using the returned paths


---

## Quick Start

### 1. Initial Setup

```bash
# Connect to Ceres
ssh <username>@ceres.scinet.usda.gov

# Verify access
lfs quota -u $USER /project/<project_name>
```

### 2. Install AgIR-CVToolkit

```bash
# Install Mambaforge (one-time)
cd /project/<project_name>
wget https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-Linux-x86_64.sh
bash Mambaforge-Linux-x86_64.sh -b -p /project/<project_name>/miniforge3

# Create environment
mamba create -p /project/<project_name>/envs/agir_cv python=3.10
mamba activate /project/<project_name>/envs/agir_cv
pip install agir-cvtoolkit
```

### 3. Stage Data from Juno

```bash
# Setup Globus
pipx install globus-cli
globus login

# Transfer database
globus transfer $JUNO_EP:"/LTS/project/<proj>/databases/agir_semif.db" \
  $CERES_EP:"/project/<proj>/databases/agir_semif.db"
```

### 4. Run Query via SLURM

```bash
# Submit job
sbatch query_job.sh

# Monitor
squeue -u $USER
```

[See detailed examples →](query-guide.html#complete-workflow-example)

---

## Key Concepts

### Storage Tiers

| Location | Description | Use Case |
|:---------|:------------|:---------|
| **Juno LTS** | Long-term storage (backed up) | Archive, source data |
| **/project** | Active project space | Databases, scripts |
| **/project/90daydata** | High-speed scratch | Temporary staging |
| **$TMPDIR** | Node-local SSD | Fast I/O during jobs |

### Workflow Overview

```
[Juno LTS] → (Globus/DTN) → [Ceres /project] → (SLURM job) → [$TMPDIR] → Results
```

{: .important }
> Juno LTS is **not mounted** on compute nodes. Always stage data to Ceres first.

---

## Support

- **SciNet Documentation**: [scinet.usda.gov/guides](https://scinet.usda.gov/guides/)
- **SciNet Support**: scinet-support@usda.gov
- **AgIR Toolkit**: [GitHub Issues](https://github.com/your-org/AgIR-CVToolkit/issues)

---

## Related Documentation

- [Installation Guide](../installation.html) - Install AgIR-CVToolkit
- [Query Tools](../query-tools.html) - General query documentation
- [SemiF Schema](../../dataset/semif.html) - Database structure
- [Field Schema](../../dataset/field.html) - Field observations
