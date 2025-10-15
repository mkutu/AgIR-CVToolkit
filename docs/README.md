# AgIR CV Toolkit Documentation

Welcome to the AgIR CV Toolkit! This toolkit provides a unified interface for querying agricultural image databases and running computer vision pipelines.

## 🚀 Getting Started

**New to the toolkit?** Start here:
- **[5-Minute Quickstart](query_quickstart.md)** - Get up and running fast with common examples

## 📚 Core Documentation

### Query System
- **[Query User Guide](db_query_usage.md)** - Complete guide to querying databases
  - Filtering and sampling strategies
  - CLI and Python API reference
  - Complete examples and best practices
  
- **[Query Specifications Guide](query_specs_quick_reference.md)** - Reproducibility and auditing
  - Understanding query_spec.json
  - Reproducing queries
  - Comparing and modifying queries

### Configuration
- **[Configuration Management](hydra_config_quick_ref.md)** - How Hydra configs work
  - Config file structure
  - Multi-stage workflows
  - Run folder organization

## 🎯 Quick Navigation

### I want to...

**Query the database:**
- [Simple filters](db_query_usage.md#simple-equality-filters) - Filter by species, state, etc.
- [Stratified sampling](db_query_usage.md#stratified-sampling) - Balanced datasets
- [Complex queries](db_query_usage.md#complex-filters) - Range filters and combinations

**Reproduce a query:**
- [Load query specs](query_specs_quick_reference.md#load-and-inspect)
- [Reproduce via CLI](query_specs_quick_reference.md#get-reproduction-command)
- [Reproduce programmatically](query_specs_quick_reference.md#reproduce-programmatically)

**Work with results:**
- [Output formats](db_query_usage.md#output-formats) - JSON, CSV, Parquet
- [Column selection](db_query_usage.md#column-selection)
- [Counting and preview](db_query_usage.md#counting--preview)

## 📖 Reference

### Python API
```python
from agir_cvtoolkit.core.db import AgirDB

# Connect and query
with AgirDB.connect("semif", sqlite_path="data/semif.db") as db:
    records = db.filter(state="NC").sample_stratified(
        by=["category_common_name"],
        per_group=10
    ).all()
```

### CLI
```bash
# Basic query
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --sample "stratified:by=category_common_name,per_group=10"
```

## 🏗️ Architecture & Design

For contributors and those interested in design decisions:
- [Repository Structure](repo_skeleton.md)
- [Roadmap](roadmap.md)
- [Architecture Decision Records](adr/0001-foundation.md)
- [Functional Requirements](FR-01.md)

## 💡 Common Workflows

### Workflow 1: Create a Balanced Training Dataset
```bash
# Query with stratified sampling
agir-cvtoolkit query --db semif \
  --sample "stratified:by=category_common_name,per_group=20" \
  --out csv

# Output: outputs/runs/{run_id}/query/query.csv
#         outputs/runs/{run_id}/query/query_spec.json
```

### Workflow 2: Reproduce a Previous Query
```bash
# Get the reproduction command
python -m agir_cvtoolkit.pipelines.utils.query_utils reproduce \
  outputs/runs/{run_id}/query/query_spec.json

# Copy and run the output command
```

### Workflow 3: Filter and Sample Complex Criteria
```python
from agir_cvtoolkit.core.db import AgirDB

with AgirDB.connect("semif", sqlite_path="data.db") as db:
    records = (
        db.filter(state="NC", category_common_name=["barley", "wheat"])
        .where("estimated_bbox_area_cm2 > 50")
        .sample_stratified(by=["category_common_name"], per_group=10)
        .all()
    )
```

## 📊 Output Structure

Every query creates a standardized output folder:
```
outputs/runs/{run_id}/
├── query/
│   ├── query.csv           # Query results
│   └── query_spec.json     # Query parameters (for reproducibility)
├── cfg.yaml                # Full configuration snapshot
├── metrics.json            # Summary statistics
└── logs/                   # Execution logs
```

## 🆘 Getting Help

### Common Issues

**"Where are my results?"**
- Results are in `outputs/runs/{run_id}/query/`
- The run_id is printed at the end of execution

**"How do I reproduce a query?"**
- See [Query Specifications Guide](query_specs_quick_reference.md#get-reproduction-command)

**"How do I filter by multiple values?"**
- CLI: `--filters "species=barley,wheat,rye"`
- Python: `filter(species=["barley", "wheat", "rye"])`

**"What's the difference between cfg.yaml and query_spec.json?"**
- `query_spec.json` - Permanent query parameters only
- `cfg.yaml` - Full Hydra config (overwritten by same project)
- Always use query_spec.json for reproducibility

### Need More Help?

- Check the [complete examples](db_query_usage.md#complete-examples)
- Review the [tips & best practices](db_query_usage.md#tips--best-practices)
- See [troubleshooting](query_specs_quick_reference.md#troubleshooting)

## 🔄 Version Information

Current documentation covers:
- Query system (v1.0)
- Query specifications and reproducibility
- Hydra configuration management

Coming soon:
- Segmentation inference (infer-seg) guide
- CVAT integration guide
- Training pipeline documentation