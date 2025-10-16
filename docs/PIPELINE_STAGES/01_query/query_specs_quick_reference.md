# Query Specification - Quick Reference

## What is query_spec.json?

A **permanent**, **human-readable** record of every query's parameters, automatically saved alongside results for reproducibility and auditing.

## Location

```
outputs/runs/{run_id}/query/query_spec.json
```

## Structure

```json
{
  "query_metadata": {
    "run_id": "query_semif_h=abc123",
    "timestamp": "2025-01-15T14:30:45",
    "user": "username",
    "host": "hostname",
    "git_commit": "abc123"
  },
  "database": {
    "type": "semif",
    "sqlite_path": "/path/to/db.sqlite",
    "table": "semif"
  },
  "query_parameters": {
    "filters": {
      "raw": ["state=NC"],
      "parsed": {"state": "NC"}
    },
    "projection": ["cutout_id", "category_common_name"],
    "sort": {
      "raw": "datetime:desc",
      "parsed": [["datetime", "desc"]]
    },
    "limit": 100,
    "offset": null,
    "sample": {
      "raw": "stratified:by=category_common_name,per_group=10",
      "parsed": {
        "strategy": "stratified",
        "by": ["category_common_name"],
        "per_group": 10
      }
    }
  },
  "execution": {
    "preview_mode": false,
    "output_format": "json"
  }
}
```

## Quick Commands

### View Query Summary
```bash
python -m agir_cvtoolkit.pipelines.utils.query_utils summary \
  outputs/runs/{run_id}/query/query_spec.json
```

**Output:**
```
Run ID: query_semif_h=abc123
Timestamp: 2025-01-15T14:30:45

Database: semif
Table: semif

Filters:
  - state = NC

Sampling: Stratified (10 per group by category_common_name)
Limit: 100 records
Output: JSON
```

### Get Reproduction Command
```bash
python -m agir_cvtoolkit.pipelines.utils.query_utils reproduce \
  outputs/runs/{run_id}/query/query_spec.json
```

**Output:**
```
agir-cvtoolkit query \
  --db semif \
  --filters "state=NC" \
  --sample "stratified:by=category_common_name,per_group=10" \
  --limit 100 \
  --out json
```

### Compare Two Queries
```bash
python -m agir_cvtoolkit.pipelines.utils.query_utils compare \
  outputs/runs/run1/query/query_spec.json \
  outputs/runs/run2/query/query_spec.json
```

## Python API

### Load and Inspect

```python
from agir_cvtoolkit.pipelines.utils.query_utils import (
    load_query_spec,
    query_spec_summary,
)

# Load
spec = load_query_spec("outputs/runs/{run_id}/query/query_spec.json")

# Print summary
print(query_spec_summary(spec))

# Access specific parts
filters = spec["query_parameters"]["filters"]["parsed"]
sample = spec["query_parameters"]["sample"]["parsed"]
```

### Reproduce Programmatically

```python
from agir_cvtoolkit.pipelines.utils.query_utils import load_query_spec
from agir_cvtoolkit.core.db import AgirDB

# Load spec
spec = load_query_spec("query_spec.json")

# Extract parameters
db_info = spec["database"]
params = spec["query_parameters"]
filters = params["filters"]["parsed"]
sample = params["sample"]["parsed"]

# Reproduce query
with AgirDB.connect(db_info["type"], sqlite_path=db_info["sqlite_path"]) as db:
    query = db.builder()
    
    # Apply filters
    for key, value in filters.items():
        if key != "$raw":
            query = query.filter(**{key: value})
    
    # Apply sampling
    if sample:
        if sample["strategy"] == "stratified":
            query = query.sample_stratified(
                by=sample["by"],
                per_group=sample["per_group"]
            )
    
    # Execute
    records = query.all()
```

### Modify and Re-run

```python
from agir_cvtoolkit.pipelines.utils.query_utils import (
    load_query_spec,
    query_spec_to_cli_args,
)

# Load previous query
spec = load_query_spec("previous_query_spec.json")

# Modify sample size
spec["query_parameters"]["sample"]["parsed"]["per_group"] = 20

# Get new CLI command
args = query_spec_to_cli_args(spec)
print("agir-cvtoolkit query", " ".join(args))
```

## Use Cases

### ✅ Reproducibility
Save exact query parameters for reproducing datasets months/years later.

### ✅ Documentation
Human-readable record of what data was queried for papers/reports.

### ✅ Auditing
Track what queries were run, when, and by whom.

### ✅ Collaboration
Share query specs with collaborators to reproduce datasets.

### ✅ Debugging
Understand what data was used if issues arise downstream.

### ✅ Iteration
Easily modify and re-run queries with different parameters.

## Common Workflows

### Workflow 1: Query → Analyze → Reproduce

```bash
# 1. Run query
agir-cvtoolkit query --db semif --sample "stratified:by=common_name,per_group=10"

# 2. Analyze results
python analyze.py outputs/runs/{run_id}/query/query.json

# 3. Later, reproduce
python -m agir_cvtoolkit.pipelines.utils.query_utils reproduce \
  outputs/runs/{run_id}/query/query_spec.json
# Copy output and run
```

### Workflow 2: Compare Different Sampling Strategies

```bash
# Query A: random sampling
agir-cvtoolkit query --db semif --sample "random:n=100"

# Query B: stratified sampling
agir-cvtoolkit query --db semif --sample "stratified:by=common_name,per_group=10"

# Compare
python -m agir_cvtoolkit.pipelines.utils.query_utils compare \
  outputs/runs/queryA/query/query_spec.json \
  outputs/runs/queryB/query/query_spec.json
```

### Workflow 3: Incremental Dataset Growth

```python
from agir_cvtoolkit.pipelines.utils.query_utils import load_query_spec

# Load previous spec
spec = load_query_spec("v1/query_spec.json")

# Increase sample size for v2
sample = spec["query_parameters"]["sample"]["parsed"]
sample["per_group"] = sample["per_group"] * 2

# Run new query with increased size
# (use modified params)
```

## Tips

💡 **Always keep query_spec.json with your results** - it's small but invaluable for reproducibility

💡 **Use `summary` to quickly check what a dataset contains** before loading large files

💡 **Use `compare` to verify training/validation splits** were created with correct parameters

💡 **Version control query_spec.json files** for important datasets

💡 **Reference query_spec in your research papers** for full transparency

## File Comparison

| File | Purpose | Persistence | Size |
|------|---------|-------------|------|
| `query_spec.json` | Query parameters only | Permanent | ~2KB |
| `cfg.yaml` | Full Hydra config | Overwritten by same project | ~10KB |
| `query.json` | Query results | Permanent | Variable |

**Best Practice:** Always use `query_spec.json` for reproducibility, not `cfg.yaml`.

## Examples Gallery

### Example 1: Simple Filter Query

```json
{
  "query_parameters": {
    "filters": {
      "parsed": {"state": "NC"}
    },
    "limit": 100
  }
}
```

### Example 2: Stratified Sampling

```json
{
  "query_parameters": {
    "filters": {
      "parsed": {"state": "NC"}
    },
    "sample": {
      "parsed": {
        "strategy": "stratified",
        "by": ["category_common_name", "area_bin"],
        "per_group": 10,
        "seed": 42
      }
    }
  }
}
```

### Example 3: Complex Multi-Filter Query

```json
{
  "query_parameters": {
    "filters": {
      "parsed": {
        "state": "NC",
        "category_common_name": ["barley", "wheat", "rye"],
        "$raw": ["estimated_bbox_area_cm2 > 50"]
      }
    },
    "sort": {
      "parsed": [["datetime", "desc"]]
    },
    "limit": 500
  }
}
```

## Integration with Other Tools

### With Segmentation Pipeline

```bash
# Query creates query_spec.json
agir-cvtoolkit query --db semif --sample "stratified:by=common_name,per_group=10"

# Segmentation references the query
agir-cvtoolkit infer-seg --override seg_inference.source.type=query_result

# Both specs preserved:
# - outputs/runs/{query_id}/query/query_spec.json
# - outputs/runs/{infer_id}/cfg.yaml (includes query reference)
```

### With Custom Analysis Scripts

```python
#!/usr/bin/env python3
"""analyze_dataset.py - Custom analysis script"""
import argparse
from agir_cvtoolkit.pipelines.utils.query_utils import load_query_spec, query_spec_summary

parser = argparse.ArgumentParser()
parser.add_argument("--query-spec", required=True)
args = parser.parse_args()

# Load and display query info
spec = load_query_spec(args.query_spec)
print("Dataset was created with:")
print(query_spec_summary(spec))

# Use spec info in analysis
# ...
```

## Troubleshooting

**Q: Where is my query_spec.json?**  
A: `outputs/runs/{run_id}/query/query_spec.json`

**Q: How do I find the run_id?**  
A: It's printed at the end of query execution, or check `outputs/runs/` for recent directories

**Q: Can I edit query_spec.json?**  
A: Yes, but it's for documentation. Editing won't re-run the query. Use it as a template for new queries.

**Q: What if I lost the query_spec.json?**  
A: Check `cfg.yaml` in the same directory, though it's less clean. Better to regenerate the query.

## Summary

✅ Automatic - saved on every query  
✅ Complete - all parameters captured  
✅ Readable - JSON format, human-friendly  
✅ Reproducible - exact CLI command recoverable  
✅ Shareable - send to collaborators  
✅ Auditable - who, when, what  
✅ Permanent - never overwritten  

**Bottom line:** `query_spec.json` makes your research reproducible! 🎯