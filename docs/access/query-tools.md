---
layout: default
title: Query Guide
parent: Access & Query
nav_order: 2
---

# Query Guide
{: .no_toc }

Learn how to query the AgIR databases using filters, sampling strategies, and exports.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The AgIR-CVToolkit provides flexible querying for the **SemiF** databases through CLI commands and Python API.

{: .note }
> The **Field** database will be incorporated in a future release.


**Key Features:**
- Filtering by species, location, size, date, and more
- Sampling (random, stratified, seeded)
- Multiple export formats (JSON, CSV, Parquet)
- Reproducibility tracking

{: .note }
> **Prerequisites**: Make sure you have the toolkit installed and configured. See the [Installation Guide](installation.html) if needed.

---

## Quick Start

### CLI Examples

```bash
# Preview first 5 records
agir-cv query --db semif --preview 5

# Simple filter
agir-cv query --db semif \
  --filters "state=NC" \
  --limit 100 \
  --out csv

# Balanced sampling
agir-cv query --db semif \
  --sample "stratified:by=category_common_name,per_group=20"
```

### Python API Examples

```python
from agir_cvtoolkit.core.db import AgirDB

# Connect to database
with AgirDB.connect(
    db_type="semif",
    db_path="/path/to/semif.db",
    table="semif"
) as db:
    # Filter and sample
    records = (
        db.filter(state="NC", category_common_name="barley")
        .limit(100)
        .all()
    )
    
    # Use results
    for record in records[:5]:
        print(f"{record.cutout_id}: {record.image_path}")
```

---

## Filtering

### Simple Equality Filters

Filter by exact match on one or more fields.

**CLI:**
```bash
# Single filter
agir-cv query --db semif --filters "state=NC"

# Multiple filters (AND logic)
agir-cv query --db semif \
  --filters "state=NC" \
  --filters "category_common_name=barley"

# Multiple values for one field (OR logic)
agir-cv query --db semif \
  --filters "category_common_name=barley,wheat,rye"
```

**Python:**
```python
# Single filter
records = db.filter(state="NC").all()

# Multiple filters (AND logic)
records = db.filter(
    state="NC",
    category_common_name="barley"
).all()

# Multiple values (OR logic)
records = db.filter(
    category_common_name=["barley", "wheat", "rye"]
).all()
```

### Range Filters

Filter by numeric ranges or comparisons.

**CLI:**
```bash
# Greater than
agir-cv query --db semif --filters "estimated_bbox_area_cm2>=50"

# Less than
agir-cv query --db semif --filters "estimated_bbox_area_cm2<=200"

# Combine for range
agir-cv query --db semif \
  --filters "estimated_bbox_area_cm2>=50" \
  --filters "estimated_bbox_area_cm2<=200"
```

**Python:**
```python
# Using where() for SQL-like expressions
records = db.where("estimated_bbox_area_cm2 > 50").all()

# BETWEEN syntax
records = db.where("estimated_bbox_area_cm2 BETWEEN 50 AND 200").all()

# Combine with regular filters
records = (
    db.filter(state="NC")
    .where("estimated_bbox_area_cm2 > 50")
    .all()
)
```

### Date Filters

**CLI:**
```bash
# Records from 2022 onwards
agir-cv query --db semif --filters "datetime>=2022-01-01"

# Specific year
agir-cv query --db semif --filters "datetime>=2022-01-01,datetime<2023-01-01"
```

**Python:**
```python
# Date range
records = db.where("datetime >= '2022-01-01'").all()

# Specific period
records = db.where("datetime BETWEEN '2022-01-01' AND '2022-12-31'").all()
```

### NULL Checks

**Python:**
```python
# Records with masks
records = db.where("mask_path IS NOT NULL").all()

# Records without masks
records = db.where("mask_path IS NULL").all()
```

---

## Sampling Strategies

### Random Sampling

Get a random subset of N records after filtering.

**CLI:**
```bash
# 200 random records
agir-cv query --db semif --sample "random:n=200"

# With filters
agir-cv query --db semif \
  --filters "state=NC" \
  --sample "random:n=100"
```

**Python:**
```python
# Simple random sample
records = db.sample_random(200).all()

# With filters
records = db.filter(state="NC").sample_random(100).all()
```

### Seeded Sampling

Reproducible pseudo-random sampling (same seed = same results every time).

**CLI:**
```bash
# Seeded random sample
agir-cv query --db semif --sample "seeded:n=200,seed=42"

# Always returns the same records
agir-cv query --db semif \
  --filters "state=NC" \
  --sample "seeded:n=100,seed=42"
```

**Python:**
```python
# Reproducible sample
records = db.sample_seeded(200, seed=42).all()

# With filters
records = (
    db.filter(category_common_name=["barley", "wheat"])
    .sample_seeded(100, seed=42)
    .all()
)
```

{: .tip }
> **Use Case**: Use seeded sampling when you need to reproduce exact datasets for experiments or publications.

### Stratified Sampling

Get N records per group - perfect for balanced training datasets.

**CLI:**
```bash
# 10 records per species
agir-cv query --db semif \
  --sample "stratified:by=category_common_name,per_group=10"

# Multiple grouping columns (use | separator)
agir-cv query --db semif \
  --sample "stratified:by=category_common_name|area_bin,per_group=5"

# With pre-filtering
agir-cv query --db semif \
  --filters "state=NC" \
  --sample "stratified:by=category_common_name,per_group=10"
```

**Python:**
```python
# Single grouping column
records = db.sample_stratified(
    by=["category_common_name"],
    per_group=10
).all()

# Multiple grouping columns
records = db.sample_stratified(
    by=["category_common_name", "area_bin"],
    per_group=5
).all()

# With pre-filtering
records = (
    db.filter(state="NC")
    .sample_stratified(by=["category_common_name"], per_group=10)
    .all()
)
```

{: .tip }
> **Use Case**: Use stratified sampling to create balanced datasets where each class has equal representation for machine learning.

---

## Sorting & Pagination

### Sorting

**CLI:**
```bash
# Single sort (ascending)
agir-cv query --db semif --sort "datetime:asc" --limit 50

# Single sort (descending)
agir-cv query --db semif --sort "datetime:desc" --limit 50

# Multiple sorts (comma-separated)
agir-cv query --db semif \
  --sort "category_common_name:asc,estimated_bbox_area_cm2:desc"
```

**Python:**
```python
# Single sort
records = db.sort("datetime", "desc").limit(50).all()

# Multiple sorts
records = (
    db.sort("category_common_name", "asc")
    .sort("estimated_bbox_area_cm2", "desc")
    .all()
)

# With filters
records = (
    db.filter(state="NC")
    .sort("datetime", "desc")
    .limit(100)
    .all()
)
```

### Pagination

**CLI:**
```bash
# First 100 records
agir-cv query --db semif --limit 100

# Next 100 records (skip first 100)
agir-cv query --db semif --limit 100 --offset 100

# Third page
agir-cv query --db semif --limit 100 --offset 200
```

**Python:**
```python
# Page 1
page1 = db.filter(state="NC").limit(100).all()

# Page 2
page2 = db.filter(state="NC").limit(100).offset(100).all()

# Pagination with sort
page = (
    db.filter(state="NC")
    .sort("datetime", "desc")
    .limit(50)
    .offset(100)
    .all()
)
```

---

## Output Formats

### Export Formats

**CLI:**
```bash
# JSON (default) - full metadata
agir-cv query --db semif --out json

# CSV - spreadsheet-friendly
agir-cv query --db semif --out csv

# Parquet - efficient for large datasets
agir-cv query --db semif --out parquet
```

### Output Structure

All queries save results in a standardized folder:

```
outputs/runs/{project_name}/{subname}/
├── query/
│   ├── query.json          # Results in JSON
│   ├── query.csv           # Results in CSV (if --out csv)
│   ├── query.parquet       # Results in Parquet (if --out parquet)
│   └── query_spec.json     # Query parameters (reproducibility)
├── cfg.yaml                # Full configuration snapshot
└── logs/                   # Execution logs
```

### Using Query Results

**Load Results in Python:**

```python
import json
import pandas as pd

# Load JSON
with open("outputs/runs/{run_id}/query/query.json") as f:
    results = json.load(f)

# Load CSV
df = pd.read_csv("outputs/runs/{run_id}/query/query.csv")

# Load Parquet
df = pd.read_parquet("outputs/runs/{run_id}/query/query.parquet")
```

---

## Preview & Count

### Preview Records

See a sample without creating output files.

**CLI:**
```bash
# Preview first 5 records
agir-cv query --db semif --preview 5

# Preview with filters
agir-cv query --db semif \
  --filters "state=NC" \
  --preview 10
```

**Python:**
```python
# Preview method
preview = db.filter(state="NC").preview(n=5)
for record in preview:
    print(f"{record.cutout_id}: {record.extras['category_common_name']}")
```

### Count Records

See how many records match your filters.

**CLI:**
```bash
# Count all records (use limit 0 to skip output)
agir-cv query --db semif --limit 0

# Count filtered records
agir-cv query --db semif \
  --filters "state=NC" \
  --filters "category_common_name=barley" \
  --limit 0
```

**Python:**
```python
# Count method
count = db.filter(state="NC").count()
print(f"Found {count} matching records")
```

---

## Common Query Patterns

### Pattern 1: Balanced Training Dataset

Get equal samples per species for machine learning:

**CLI:**
```bash
agir-cv query --db semif \
  --sample "stratified:by=category_common_name,per_group=20" \
  --out csv
```

**Python:**
```python
records = db.sample_stratified(
    by=["category_common_name"],
    per_group=20
).all()
```

### Pattern 2: Multi-State, Multi-Species

Get specific species from multiple states:

**CLI:**
```bash
agir-cv query --db semif \
  --filters "state=NC,GA,SC" \
  --filters "category_common_name=barley,wheat,rye" \
  --sample "stratified:by=category_common_name,per_group=15"
```

**Python:**
```python
records = (
    db.filter(
        state=["NC", "GA", "SC"],
        category_common_name=["barley", "wheat", "rye"]
    )
    .sample_stratified(by=["category_common_name"], per_group=15)
    .all()
)
```

### Pattern 3: Size-Based Selection

Get large specimens only:

**CLI:**
```bash
agir-cv query --db semif \
  --filters "estimated_bbox_area_cm2>=100" \
  --sort "estimated_bbox_area_cm2:desc" \
  --limit 50
```

**Python:**
```python
records = (
    db.where("estimated_bbox_area_cm2 > 100")
    .sort("estimated_bbox_area_cm2", "desc")
    .limit(50)
    .all()
)
```


### Pattern 5: Temporal Range

Get images from a specific time period:

**CLI:**
```bash
agir-cv query --db semif \
  --filters "datetime>=2022-06-01" \
  --filters "datetime<2022-09-01" \
  --sort "datetime:asc"
```

**Python:**
```python
records = (
    db.where("datetime BETWEEN '2022-06-01' AND '2022-09-01'")
    .sort("datetime", "asc")
    .all()
)
```

---

## Database-Specific Tips

### SemiF Database

**Key Fields:**
- `cutout_id` - Unique identifier
- `category_common_name` - Species name
- `category_family` - Taxonomic family
- `state` - US state (two-letter code)
- `estimated_bbox_area_cm2` - Plant size
- `datetime` - Image capture timestamp
- `image_path` - Path to image
- `mask_path` - Path to segmentation mask

**Common Filters:**
```bash
# By species
--filters "category_common_name=barley"

# By family
--filters "category_family=Poaceae"

# By size
--filters "estimated_bbox_area_cm2>=50"

# By state
--filters "state=NC,GA,SC"
```

---

## Reproducibility

### Query Specifications

Every query automatically saves a `query_spec.json` file containing:
- Exact filters and values
- Sampling strategy and parameters
- Sort orders
- Database path and version
- Timestamp and user
- CLI command to reproduce

**View Query Spec:**
```bash
cat outputs/runs/{run_id}/query/query_spec.json
```

**Example `query_spec.json`:**
```json
{
  "database": {
    "type": "semif",
    "db_path": "/path/to/semif.db",
    "table": "semif"
  },
  "query_parameters": {
    "filters": {
      "raw": ["state=NC", "category_common_name=barley"],
      "parsed": {
        "state": "NC",
        "category_common_name": "barley"
      }
    },
    "sample": {
      "raw": "stratified:by=category_common_name,per_group=10",
      "parsed": {
        "strategy": "stratified",
        "by": ["category_common_name"],
        "per_group": 10
      }
    }
  },
  "timestamp": "2025-01-15T10:30:00",
  "user": "username"
}
```

### Reproduce a Previous Query

```bash
# View previous query parameters
cat outputs/runs/previous_run/query/query_spec.json | jq '.query_parameters'

# Re-run with same parameters
agir-cv query --db semif \
  --filters "state=NC" \
  --filters "category_common_name=barley" \
  --sample "stratified:by=category_common_name,per_group=10"
```

---

## Advanced Usage

### Combining Multiple Techniques

```bash
# Complex query with everything
agir-cv query --db semif \
  --filters "state=NC,GA" \
  --filters "category_common_name=barley,wheat,rye" \
  --filters "estimated_bbox_area_cm2>=50" \
  --filters "estimated_bbox_area_cm2<=200" \
  --sample "stratified:by=category_common_name|area_bin,per_group=10" \
  --sort "datetime:desc" \
  --out parquet
```

### Python Chaining

```python
# Build complex query step by step
records = (
    db.filter(state=["NC", "GA"])
    .filter(category_common_name=["barley", "wheat", "rye"])
    .where("estimated_bbox_area_cm2 BETWEEN 50 AND 200")
    .sample_stratified(
        by=["category_common_name", "area_bin"],
        per_group=10
    )
    .sort("datetime", "desc")
    .all()
)
```

### Verify Before Full Query

```python
# Check what you'll get
query = db.filter(state="NC", category_common_name="barley")

# Count first
count = query.count()
print(f"Will return {count} records")

# Preview sample
preview = query.preview(n=5)
for r in preview:
    print(f"  {r.cutout_id}: {r.extras['category_common_name']}")

# If satisfied, execute full query
if count > 0 and count < 10000:
    records = query.all()
```

---

## Next Steps

- **[Explore SemiF Schema →](../dataset/semif.html)** - Understand available fields
- **[Explore Field Schema →](../dataset/field.html)** - Understand available fields  
- **[View Installation Guide →](installation.html)** - Setup and configuration
- **[Full Toolkit Docs →](https://github.com/your-org/AgIR-CVToolkit)** - Complete pipeline features

---

## Quick Reference

### Essential Commands

```bash
# Preview
agir-cv query --db semif --preview 5

# Simple filter
agir-cv query --db semif --filters "state=NC" --limit 100

# Stratified sampling
agir-cv query --db semif \
  --sample "stratified:by=category_common_name,per_group=10"

# Export to CSV
agir-cv query --db semif --filters "state=NC" --out csv

# Count records
agir-cv query --db semif --filters "state=NC" --limit 0
```

### Filter Syntax

| Type | CLI Syntax | Example |
|------|------------|---------|
| Single value | `field=value` | `state=NC` |
| Multiple values (OR) | `field=val1,val2` | `state=NC,GA,SC` |
| Multiple filters (AND) | Multiple `--filters` | `--filters "state=NC" --filters "category=barley"` |
| Greater than | `field>=value` | `estimated_bbox_area_cm2>=50` |
| Less than | `field<=value` | `estimated_bbox_area_cm2<=200` |

### Sampling Syntax

| Strategy | CLI Syntax | Example |
|----------|------------|---------|
| Random | `random:n=N` | `--sample "random:n=100"` |
| Seeded | `seeded:n=N,seed=S` | `--sample "seeded:n=100,seed=42"` |
| Stratified (single) | `stratified:by=field,per_group=N` | `--sample "stratified:by=category_common_name,per_group=10"` |
| Stratified (multiple) | `stratified:by=f1\|f2,per_group=N` | `--sample "stratified:by=common_name\|area_bin,per_group=5"` |