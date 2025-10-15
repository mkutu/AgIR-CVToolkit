# AgIR CV Toolkit - 5-Minute Quickstart

Get started with the AgIR CV Toolkit in just a few minutes. This guide covers the most common use cases.

## Prerequisites

```bash
# Install the toolkit
pip install agir-cvtoolkit

# Or if using conda
conda env create -f environment.yml
conda activate agir-cv
```

## Quick Start Examples

### Example 1: Simple Query

Get 100 barley images from North Carolina:

**CLI:**
```bash
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --filters "category_common_name=barley" \
  --limit 100
```

**Python:**
```python
from agir_cvtoolkit.core.db import AgirDB

with AgirDB.connect("semif", sqlite_path="data/semif.db") as db:
    records = db.filter(
        state="NC",
        category_common_name="barley"
    ).limit(100).all()

print(f"Found {len(records)} records")
```

**Output:** Results saved to `outputs/runs/{run_id}/query/query.json`

---

### Example 2: Balanced Dataset (Stratified Sampling)

Get 20 images per species for a balanced training set:

**CLI:**
```bash
agir-cvtoolkit query --db semif \
  --sample "stratified:by=category_common_name,per_group=20" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("semif", sqlite_path="data/semif.db") as db:
    records = db.sample_stratified(
        by=["category_common_name"],
        per_group=20
    ).all()

# Verify balance
from collections import Counter
species_counts = Counter(r.extras["category_common_name"] for r in records)
for species, count in species_counts.items():
    print(f"{species}: {count}")
```

**Output:** Each species will have exactly 20 records (or fewer if not available)

---

### Example 3: Filter by Size Range

Get large plant instances (bbox area > 100 cm²):

**CLI:**
```bash
agir-cvtoolkit query --db semif \
  --filters "estimated_bbox_area_cm2>=100" \
  --sort "estimated_bbox_area_cm2:desc" \
  --limit 50
```

**Python:**
```python
with AgirDB.connect("semif", sqlite_path="data/semif.db") as db:
    records = (
        db.where("estimated_bbox_area_cm2 > 100")
        .sort("estimated_bbox_area_cm2", "desc")
        .limit(50)
        .all()
    )
```

---

### Example 4: Multi-Species with Sampling

Get 10 images per species for barley, wheat, and rye from NC only:

**CLI:**
```bash
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --filters "category_common_name=barley,wheat,rye" \
  --sample "stratified:by=category_common_name,per_group=10"
```

**Python:**
```python
with AgirDB.connect("semif", sqlite_path="data/semif.db") as db:
    records = (
        db.filter(
            state="NC",
            category_common_name=["barley", "wheat", "rye"]
        )
        .sample_stratified(
            by=["category_common_name"],
            per_group=10
        )
        .all()
    )
```

---

### Example 5: Preview Before Running

Check what a query will return before executing:

**Python:**
```python
with AgirDB.connect("semif", sqlite_path="data/semif.db") as db:
    # Count matching records
    count = db.filter(state="NC").count()
    print(f"Found {count} matching records")
    
    # Preview first 5
    preview = db.filter(state="NC").preview(n=5)
    for record in preview:
        print(f"  {record.cutout_id}: {record.extras['category_common_name']}")
```

---

## Understanding Output

Every query creates a standardized folder:

```
outputs/runs/{run_id}/
├── query/
│   ├── query.json          # Your results
│   └── query_spec.json     # How to reproduce this query
├── cfg.yaml                # Full configuration
└── logs/                   # Execution logs
```

### The run_id

The `run_id` is printed at the end of execution:
```
Query complete! Results saved to: outputs/runs/query_semif_h=a1b2c3d4/query/
```

---

## Reproducing a Query

Later, you can reproduce any query exactly:

```bash
# Get the command to reproduce
python -m agir_cvtoolkit.pipelines.utils.query_utils reproduce \
  outputs/runs/{run_id}/query/query_spec.json

# Output will show the exact CLI command:
# agir-cvtoolkit query --db semif --filters "state=NC" ...

# Copy and run it
```

---

## Common Patterns Cheat Sheet

### Filtering
```bash
# Single value
--filters "state=NC"

# Multiple values (OR logic)
--filters "category_common_name=barley,wheat,rye"

# Multiple filters (AND logic)
--filters "state=NC" --filters "category_common_name=barley"

# Comparison operators
--filters "estimated_bbox_area_cm2>=50"
--filters "estimated_bbox_area_cm2<=200"
```

### Sampling
```bash
# Random sample
--sample "random:n=100"

# Reproducible random (same seed = same results)
--sample "seeded:n=100,seed=42"

# Stratified (balanced by one column)
--sample "stratified:by=category_common_name,per_group=10"

# Stratified by multiple columns
--sample "stratified:by=category_common_name|area_bin,per_group=5"
```

### Output Formats
```bash
# JSON (default)
--out json

# CSV (easier for Excel/pandas)
--out csv

# Parquet (efficient for large datasets)
--out parquet
```

### Sorting
```bash
# Single sort
--sort "datetime:desc"

# Multiple sorts
--sort "category_common_name:asc,estimated_bbox_area_cm2:desc"
```

---

## Next Steps

Now that you've run your first queries, explore more advanced features:

1. **[Query User Guide](db_query_usage.md)** - Complete API reference and advanced usage
2. **[Query Specifications](query_specs_quick_reference.md)** - Reproducibility and comparing queries
3. **[Configuration Guide](hydra_config_quick_ref.md)** - Multi-stage workflows

---

## Quick Tips

✅ **Use context managers** in Python for automatic cleanup:
```python
with AgirDB.connect("semif", sqlite_path="data.db") as db:
    records = db.filter(state="NC").all()
# Connection automatically closed
```

✅ **Check counts first** before fetching large results:
```python
count = db.filter(state="NC").count()
if count > 10000:
    print("Large result set, consider adding limits")
```

✅ **Use stratified sampling** for balanced ML datasets

✅ **Save query_spec.json** with your results for reproducibility

✅ **Use CSV output** for easy inspection in Excel or pandas

---

## Common Issues

**"Command not found: agir-cvtoolkit"**
- Make sure you've installed: `pip install agir-cvtoolkit`
- Or activated the conda environment: `conda activate agir-cv`

**"Database not found"**
- Specify the full path: `--db semif --sqlite-path /full/path/to/db.sqlite`

**"No matching records"**
- Use `db.count()` to verify filters are correct
- Try simpler filters first, then add constraints

**"Memory error with large queries"**
- Use `.execute()` instead of `.all()` for iteration:
  ```python
  for record in db.filter(state="NC").execute():
      process(record)
  ```

---

**Ready for more?** Check out the [complete documentation](README.md) or jump straight to the [Query User Guide](db_query_usage.md)!