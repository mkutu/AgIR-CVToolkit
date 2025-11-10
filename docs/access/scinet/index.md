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

## Available Guides

<div class="feature-grid" markdown="1">

<div class="feature-card" markdown="1">

### 📚 Complete Setup & Query Guide
Comprehensive documentation covering setup, data staging, SLURM jobs, and best practices.

[Read Complete Guide →](query-guide.html){: .btn .btn-primary }
</div>

<div class="feature-card" markdown="1">

### ⚡ Quick Reference
One-page cheat sheet with common commands, SLURM templates, and troubleshooting.

[View Quick Reference →](quick-reference.html){: .btn .btn-blue }
</div>

</div>

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
