---
layout: default
title: SciNet Usage
parent: Access & Query
nav_order: 3
---

# Using AgIR on SciNet
{: .no_toc }

Guide for accessing and querying the AgIR dataset on SciNet, USDA's high-performance computing infrastructure.
{: .fs-6 .fw-300 }

{: .warning }
> **Documentation In Progress**: This page is a placeholder. Comprehensive SciNet documentation will be added soon.

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

<div class="feature-card" markdown="1">

**SciNet** is the USDA's high-performance computing (HPC) infrastructure, providing researchers with powerful computational resources for data-intensive agricultural research.

The AgIR dataset is hosted on SciNet and accessible to authorized USDA users through standard HPC workflows.

</div>

---

## SciNet Architecture

### Compute Resources

SciNet provides several types of compute nodes optimized for different workloads:

| Node Type | Purpose | Typical Use |
|:----------|:--------|:------------|
| **Login Nodes** | Interactive access, job submission | Lightweight tasks, script development |
| **Compute Nodes** | CPU-intensive processing | Data processing, analysis |
| **GPU Nodes** | Accelerated computing | Deep learning, model training |
| **High-Memory Nodes** | Large-memory tasks | Big data processing |

{: .note }
> **Best Practice**: Never run compute-intensive tasks on login nodes. Always submit jobs to the scheduler.

### Job Scheduler

SciNet uses a job scheduling system (typically SLURM) to manage computational resources:

- **Interactive Jobs**: For development and testing
- **Batch Jobs**: For production workflows
- **Array Jobs**: For parallel processing of multiple tasks

---

## Getting Started

### Prerequisites

Before using AgIR on SciNet:

1. **SciNet Account**: Request access through your USDA administrator
2. **Project Allocation**: Ensure your project has computational allocation
3. **SSH Access**: Configure SSH keys for secure connection
4. **Storage Quota**: Verify sufficient storage for your datasets

### Initial Setup

```bash
# Connect to SciNet (placeholder - actual connection details TBD)
ssh username@scinet.usda.gov

# Load required modules (placeholder)
module load python
module load cuda  # For GPU jobs

# Verify AgIR-CVToolkit installation
agir-cv --version
```

---

## Working with AgIR Data

### Data Location

{: .important }
> **Data Paths**: Specific paths to AgIR databases on SciNet will be documented here.

```bash
# Example paths (placeholder - actual paths TBD)
export AGIR_DATA=/path/to/agir/data
export SEMIF_DB=$AGIR_DATA/semif.db
export FIELD_DB=$AGIR_DATA/field.db
```

### Querying Data on SciNet

Basic query example on SciNet:

```bash
# Load environment
module load agir-cvtoolkit

# Run query (example)
agir-cv query --db semif \
  --filters "state=NC" \
  --limit 100 \
  -o "db.semif.db_path=$SEMIF_DB"
```

---

## Job Submission

### Interactive Jobs

For development and testing:

```bash
# Request interactive session (placeholder example)
salloc --nodes=1 --ntasks=4 --time=2:00:00

# With GPU
salloc --nodes=1 --ntasks=4 --gres=gpu:1 --time=2:00:00
```

### Batch Jobs

Create a batch script for production workflows:

```bash
#!/bin/bash
#SBATCH --job-name=agir_query
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --time=4:00:00
#SBATCH --output=agir_query_%j.out
#SBATCH --error=agir_query_%j.err

# Load modules
module load agir-cvtoolkit

# Run query
agir-cv query --db semif \
  --filters "state=NC" \
  --sample "stratified:by=category_common_name,per_group=100"
```

Submit the job:

```bash
sbatch query_job.sh
```

### GPU Jobs for Model Training

Example GPU batch script:

```bash
#!/bin/bash
#SBATCH --job-name=agir_train
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --gres=gpu:2
#SBATCH --time=24:00:00
#SBATCH --output=train_%j.out

# Load modules
module load agir-cvtoolkit
module load cuda

# Run training
agir-cv train \
  -o train.devices=2 \
  -o train.max_epochs=100
```

---

## Resource Management

### Storage Considerations

- **Home Directory**: Limited space, for scripts and configs only
- **Project Storage**: Larger allocation for datasets and outputs
- **Scratch Space**: Temporary high-speed storage for job I/O

### Monitoring Jobs

```bash
# Check job status
squeue -u $USER

# View job details
scontrol show job <job_id>

# Cancel a job
scancel <job_id>

# View completed jobs
sacct -u $USER
```

---

## Best Practices

### Efficient Data Access

1. **Use Local Scratch**: Copy data to node-local scratch for faster I/O
2. **Batch Processing**: Group queries to minimize overhead
3. **Parallel Processing**: Utilize array jobs for independent tasks

### Resource Requests

- **Right-size Jobs**: Don't request more resources than needed
- **Walltime**: Estimate realistic completion times
- **Test Scaling**: Start small, then scale up

### Data Management

- **Clean Up**: Remove temporary files after job completion
- **Archive Results**: Move completed results to project storage
- **Compress Output**: Use compression for large result files

---

## Common Workflows

### Workflow 1: Dataset Query and Export

```bash
# 1. Submit query job
sbatch scripts/query_dataset.sh

# 2. Wait for completion
squeue -u $USER

# 3. Verify output
ls -lh outputs/runs/query_*/query/
```

### Workflow 2: Model Training Pipeline

```bash
# 1. Query training data
sbatch scripts/query_training_data.sh

# 2. Train model (after query completes)
sbatch scripts/train_model.sh

# 3. Monitor training
tail -f train_*.out
```

### Workflow 3: Batch Inference

```bash
# 1. Prepare inference data
sbatch scripts/prepare_inference.sh

# 2. Run inference as array job
sbatch --array=1-10 scripts/inference_batch.sh
```

---

## Troubleshooting

### Common Issues

**Issue: Job won't start**
- Check queue status: `squeue`
- Verify allocation: `sshare -U`
- Review resource requests

**Issue: Out of memory**
- Request more memory: `--mem=64G`
- Use high-memory nodes
- Optimize data loading

**Issue: Storage quota exceeded**
- Check quota: `quota -s`
- Clean up temporary files
- Use scratch space

**Issue: Module not found**
- List available modules: `module avail`
- Load required modules in job script
- Check module dependencies

---

## Additional Resources

### Documentation

{: .note }
> Detailed SciNet documentation coming soon. This will include:
> - Complete scheduler commands reference
> - Node specifications and capabilities
> - Storage system architecture
> - Network configuration
> - Performance optimization guides

### Support

- **SciNet User Guides**: [scinet.usda.gov](https://scinet.usda.gov)
- **USDA Support**: [scinet-support@usda.gov](mailto:scinet-support@usda.gov)
- **AgIR Issues**: [GitHub Issues](https://github.com/your-org/AgIR-CVToolkit/issues)

### Related Documentation

- [Installation Guide](installation.html) - Install AgIR-CVToolkit
- [Query Guide](query-tools.html) - Learn to query datasets
- [SemiF Schema](../dataset/semif.html) - Database structure
- [Field Schema](../dataset/field.html) - Field observations

---

## Coming Soon

This placeholder will be expanded with:

- [ ] Detailed SciNet cluster specifications
- [ ] Complete job scheduler command reference
- [ ] Node type selection guidelines
- [ ] Storage tier descriptions and best practices
- [ ] Network architecture and data transfer protocols
- [ ] Performance benchmarking results
- [ ] Advanced parallelization techniques
- [ ] Container usage (Singularity/Apptainer)
- [ ] Example job scripts for all workflow types
- [ ] Debugging and profiling tools

---

{: .note }
> **Feedback Welcome**: If you have specific questions or topics you'd like covered in the SciNet documentation, please [open an issue](https://github.com/your-org/AgIR-CVToolkit/issues) or contact the development team.