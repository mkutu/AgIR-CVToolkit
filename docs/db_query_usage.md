### Reproducing a Query

To reproduce a query from a saved specification:

**Using the CLI utility:**

```bash
# Show summary of what was queried
python -m agir_cvtoolkit.pipelines.utils.query_utils summary \
  outputs/runs/{run_id}/query/query_spec.json

# Get the exact CLI command to reproduce
python -m agir_cvtoolkit.pipelines.utils.query_utils reproduce \
  outputs/runs/{run_id}/query/query_spec.json

# Compare two query specs
python -m agir_cvtoolkit.pipelines.utils.query_utils compare \
  outputs/runs/run1/query/query_spec.json \
  outputs/runs/run2/query/query_spec.json
```

**Output example:**

```
$ python -m agir_cvtoolkit.pipelines.utils.query_utils summary query_spec.json

Run ID: query_semif_h=a1b2c3d4
Timestamp: 2025-01-15T14:30:45

Database: semif
Table: semif

Filters:
  - state = NC
  - category_common_name IN ['barley', 'wheat']

Sampling: Stratified (10 per group by category_common_name)
Limit: 100 records
Output: JSON
```

**Using Python:**

```python
from pathlib import Path
from agir_cvtoolkit.pipelines.utils.query_utils import (
    load_query_spec,
    query_spec_to_cli_args,
    query_spec_summary,
)

# Load spec
spec = load_query_spec("outputs/runs/{run_id}/query/query_spec.json")

# Get summary
print(query_spec_summary(spec))

# Get CLI args
args = query_spec_to_cli_args(spec)
print("agir-cvtoolkit query", " ".join(args))

# Programmatic reproduction
from agir_cvtoolkit.core.db import AgirDB

db_info = spec["database"]
params = spec["query_parameters"]["filters"]["parsed"]

with AgirDB.connect(db_info["type"], sqlite_path=db_info["sqlite_path"]) as db:
    query = db.builder()
    for key, value in params.items():
        if key != "$raw":
            query = query.filter(**{key: value})
    
    records = query.all()
```# AgirDB Documentation

AgirDB provides a unified, fluent interface for querying the AgIR CV Toolkit databases (SemiF and Field).

## Quick Start

### Python API

```python
from agir_cvtoolkit.core.db import AgirDB

# Connect to database
db = AgirDB.connect("semif", sqlite_path="data/semif.db")

# Simple query
records = db.filter(category_common_name="barley").limit(10).all()

# Close connection when done
db.close()

# Or use context manager (auto-closes)
with AgirDB.connect("semif", sqlite_path="data.db") as db:
    records = db.filter(state="NC").all()
```

### CLI

```bash
# Basic query
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley" \
  --limit 10

# Output to CSV
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --out csv
```

---

## Filtering

### Simple Equality Filters

**Python:**
```python
# Single filter
records = db.filter(state="NC").all()

# Multiple filters (AND logic)
records = db.filter(
    state="NC",
    category_common_name="barley"
).all()

# List of values (IN clause)
records = db.filter(
    category_common_name=["barley", "wheat", "rye"]
).all()
```

**CLI:**
```bash
# Single filter
--filters "state=NC"

# Multiple values (comma-separated)
--filters "category_common_name=barley,wheat,rye"

# Multiple filter flags (AND logic)
--filters "state=NC" --filters "category_common_name=barley"
```

### Range & Comparison Filters

**Python:**
```python
# Use where() for SQL-like expressions
records = db.where("estimated_bbox_area_cm2 > 100").all()

records = db.where("estimated_bbox_area_cm2 BETWEEN 50 AND 200").all()

# Combine with regular filters
records = (
    db.filter(state="NC")
    .where("estimated_bbox_area_cm2 > 100")
    .all()
)
```

**CLI:**
```bash
# Comparison operators
--filters "estimated_bbox_area_cm2>=50"
--filters "estimated_bbox_area_cm2<=200"

# Combine multiple
--filters "state=NC" \
--filters "estimated_bbox_area_cm2>=50" \
--filters "estimated_bbox_area_cm2<=200"
```

### Complex Filters

**Python:**
```python
# Multiple WHERE clauses
records = (
    db.where("estimated_bbox_area_cm2 > 50")
    .where("estimated_bbox_area_cm2 < 200")
    .filter(category_common_name=["barley", "wheat"])
    .all()
)

# NULL checks
records = db.where("mask_path IS NOT NULL").all()
```

**CLI:**
```bash
# Multiple expressions
--filters "estimated_bbox_area_cm2>=50" \
--filters "estimated_bbox_area_cm2<=200" \
--filters "category_common_name=barley,wheat"
```

---

## Sampling Strategies

### Random Sampling

Get a random sample of N records (after applying filters).

**Python:**
```python
# Simple random sample
records = db.sample_random(200).all()

# With filters
records = (
    db.filter(state="NC")
    .sample_random(100)
    .all()
)
```

**CLI:**
```bash
agir-cvtoolkit query --db semif \
  --sample "random:n=200"

# With filters
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --sample "random:n=100"
```

### Seeded Sampling

Deterministic pseudo-random sampling (same seed = same results).

**Python:**
```python
# Reproducible random sample
records = db.sample_seeded(200, seed=42).all()

# With filters
records = (
    db.filter(category_common_name=["barley", "wheat"])
    .sample_seeded(100, seed=42)
    .all()
)
```

**CLI:**
```bash
agir-cvtoolkit query --db semif \
  --sample "seeded:n=200,seed=42"
```

### Stratified Sampling

Get N records per group (grouped by one or more columns).

**Python:**
```python
# 10 records per species
records = db.sample_stratified(
    by=["category_common_name"],
    per_group=10
).all()

# 5 records per (species, area_bin) combination
records = db.sample_stratified(
    by=["category_common_name", "area_bin"],
    per_group=5
).all()

# With pre-filtering
records = (
    db.filter(state="NC")
    .sample_stratified(
        by=["category_common_name", "area_bin"],
        per_group=10
    )
    .all()
)
```

**CLI:**
```bash
# Single grouping column
agir-cvtoolkit query --db semif \
  --sample "stratified:by=category_common_name,per_group=10"

# Multiple grouping columns
agir-cvtoolkit query --db semif \
  --sample "stratified:by=category_common_name|area_bin,per_group=5"

# With filters
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --sample "stratified:by=category_common_name,per_group=10"
```

---

## Sorting & Pagination

### Sorting

**Python:**
```python
# Single sort
records = db.sort("datetime", "desc").limit(10).all()

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
    .all()
)
```

**CLI:**
```bash
# Single sort (asc/desc)
--sort "datetime:desc"

# Multiple sorts
--sort "category_common_name:asc,estimated_bbox_area_cm2:desc"
```

### Pagination

**Python:**
```python
# First 100 records
page1 = db.filter(state="NC").limit(100).all()

# Next 100 records
page2 = db.filter(state="NC").limit(100).offset(100).all()

# Combining with sort
page = (
    db.filter(state="NC")
    .sort("datetime", "desc")
    .limit(50)
    .offset(100)
    .all()
)
```

**CLI:**
```bash
# Limit
--limit 100

# Limit + offset
--limit 100 --offset 100
```

---

## Column Selection

Select specific columns to return (default: all columns).

**Python:**
```python
# Select specific columns
records = db.select(
    "cutout_id",
    "category_common_name",
    "estimated_bbox_area_cm2"
).all()

# Combine with filters
records = (
    db.select("cutout_id", "category_common_name")
    .filter(state="NC")
    .limit(10)
    .all()
)
```

**CLI:**
```bash
# Comma-separated column names
--projection "cutout_id,category_common_name,estimated_bbox_area_cm2"
```

---

## Counting & Preview

### Count Records

**Python:**
```python
# Count all records
total = db.builder().count()

# Count with filters
count = db.filter(state="NC").count()

# Count with complex filters
count = (
    db.filter(category_common_name=["barley", "wheat"])
    .where("estimated_bbox_area_cm2 > 50")
    .count()
)
```

### Preview

**Python:**
```python
# Quick preview (first 10 records)
preview = db.filter(state="NC").preview(n=5)

# Get first matching record
first = db.filter(category_common_name="wheat").first()

# Get by ID
record = db.get("cutout_12345")
```

**CLI:**
```bash
# Preview first N records
--preview 10
```

---

## Output Files

### Query Results

**JSON Output:**
```
outputs/runs/{run_id}/query/
├── query.json          # Query results
├── query_spec.json     # Query specification (reproducibility)
└── ...
```

**CSV/Parquet Output:**
```
outputs/runs/{run_id}/query/
├── query.csv           # Query results
├── query_spec.json     # Query specification
└── ...
```

### Query Specification File

Every query automatically saves a `query_spec.json` file containing all parameters used:

```json
{
  "query_metadata": {
    "run_id": "query_semif_h=a1b2c3d4",
    "timestamp": "2025-01-15T14:30:45",
    "user": "mkutuga",
    "host": "gpu-server-01",
    "git_commit": "a1b2c3d"
  },
  "database": {
    "type": "semif",
    "sqlite_path": "/path/to/AgIR_DB_v1_0_202509.db",
    "table": "semif"
  },
  "query_parameters": {
    "filters": {
      "raw": ["state=NC", "category_common_name=barley,wheat"],
      "parsed": {
        "state": "NC",
        "category_common_name": ["barley", "wheat"]
      }
    },
    "projection": ["cutout_id", "category_common_name", "estimated_bbox_area_cm2"],
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
    "preview_count": 0,
    "output_format": "json"
  }
}
```

**Benefits:**
- **Reproducibility**: Exact parameters saved with results
- **Transparency**: See exactly what was queried
- **Reusability**: Recreate the same query later
- **Auditing**: Track what queries were run

### Reproducing a Query

To reproduce a query from a saved specification:

```python
import json
from pathlib import Path

# Load query spec
with open("outputs/runs/{run_id}/query/query_spec.json") as f:
    spec = json.load(f)

# Extract parameters
params = spec["query_parameters"]
filters = params["filters"]["raw"]
sample = params["sample"]["raw"]

# Reproduce query
# (Use the raw CLI arguments from the spec)
```

Or via CLI:
```bash
# Read the query_spec.json and reconstruct the command
cat outputs/runs/{run_id}/query/query_spec.json | jq '.query_parameters'

# Then run with those parameters
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --filters "category_common_name=barley,wheat" \
  --sample "stratified:by=category_common_name,per_group=10"
```

---

## Output Formats

### JSON

**CLI:**
```bash
# JSON output (default)
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --out json

# Output written to: outputs/runs/{run_id}/query/query.json
```

### CSV

**CLI:**
```bash
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --out csv

# Output written to: outputs/runs/{run_id}/query/query.csv
```

### Parquet

**CLI:**
```bash
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --out parquet

# Output written to: outputs/runs/{run_id}/query/query.parquet
```

---

## Complete Examples

### Example 1: Balanced Dataset Creation

Get 20 records per species for training:

**Python:**
```python
with AgirDB.connect("semif", sqlite_path="data/semif.db") as db:
    records = db.sample_stratified(
        by=["category_common_name"],
        per_group=20
    ).all()
    
    print(f"Total records: {len(records)}")
    
    # Group by species
    from collections import Counter
    species_counts = Counter(r.extras["category_common_name"] for r in records)
    for species, count in species_counts.items():
        print(f"  {species}: {count}")
```

**CLI:**
```bash
agir-cvtoolkit query --db semif \
  --sample "stratified:by=category_common_name,per_group=20" \
  --out csv
```

### Example 2: Filtered Stratified Sample

Get 10 records per (species, area_bin) for NC only:

**Python:**
```python
with AgirDB.connect("semif", sqlite_path="data/semif.db") as db:
    records = (
        db.filter(state="NC")
        .sample_stratified(
            by=["category_common_name", "area_bin"],
            per_group=10
        )
        .all()
    )
```

**CLI:**
```bash
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --sample "stratified:by=category_common_name|area_bin,per_group=10" \
  --out csv
```

### Example 3: Large Objects Only

Get large bbox areas, sorted by size:

**Python:**
```python
with AgirDB.connect("semif", sqlite_path="data/semif.db") as db:
    records = (
        db.where("estimated_bbox_area_cm2 > 200")
        .sort("estimated_bbox_area_cm2", "desc")
        .limit(100)
        .all()
    )
```

**CLI:**
```bash
agir-cvtoolkit query --db semif \
  --filters "estimated_bbox_area_cm2>=200" \
  --sort "estimated_bbox_area_cm2:desc" \
  --limit 100 \
  --out json
```

### Example 4: Multi-Species Analysis

Get specific species with area constraints:

**Python:**
```python
with AgirDB.connect("semif", sqlite_path="data/semif.db") as db:
    records = (
        db.filter(category_common_name=["barley", "wheat", "rye"])
        .where("estimated_bbox_area_cm2 BETWEEN 50 AND 150")
        .select("cutout_id", "category_common_name", "estimated_bbox_area_cm2")
        .sort("category_common_name", "asc")
        .all()
    )
```

**CLI:**
```bash
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley,wheat,rye" \
  --filters "estimated_bbox_area_cm2>=50" \
  --filters "estimated_bbox_area_cm2<=150" \
  --projection "cutout_id,category_common_name,estimated_bbox_area_cm2" \
  --sort "category_common_name:asc" \
  --out csv
```

---

## Database-Specific Notes

### SemiF Database

- **Primary key:** `cutout_id`
- **Common filters:** `category_common_name`, `state`, `area_bin`, `estimated_bbox_area_cm2`
- **Default table:** `semif`

```python
db = AgirDB.connect("semif", sqlite_path="data/semif.db")
```

### Field Database

- **Primary key:** `id`
- **Common filters:** `plant_type`, `common_name`
- **Default table:** `records`

```python
db = AgirDB.connect("field", sqlite_path="data/field.db")
```

---

## Advanced Usage

### Building Queries Programmatically

When building queries conditionally, always start with `.builder()`:

```python
db = AgirDB.connect("semif", sqlite_path="data.db")

# Start with builder
query = db.builder()

# Add filters conditionally
if filter_by_state:
    query = query.filter(state="NC")

if filter_by_species:
    query = query.filter(category_common_name=species_list)

if use_sampling:
    query = query.sample_stratified(by=["category_common_name"], per_group=10)
else:
    query = query.limit(100)

# Execute
records = query.all()
```

### Chaining Operations

All fluent methods return a `QueryBuilder`, allowing unlimited chaining:

```python
records = (
    db.filter(state="NC")
    .where("estimated_bbox_area_cm2 > 50")
    .where("estimated_bbox_area_cm2 < 200")
    .filter(category_common_name=["barley", "wheat"])
    .select("cutout_id", "category_common_name", "estimated_bbox_area_cm2")
    .sort("estimated_bbox_area_cm2", "desc")
    .limit(50)
    .all()
)
```

### Iterator vs List

For large result sets, use `.execute()` (returns iterator) instead of `.all()` (returns list):

```python
# Memory efficient - processes one record at a time
for record in db.filter(state="NC").execute():
    process(record)

# Loads all into memory at once
records = db.filter(state="NC").all()
```

---

## API Reference Summary

### Connection
- `AgirDB.connect(db_type, sqlite_path, table=None)` - Create connection

### Query Building
- `.builder()` - Start empty query
- `.filter(**kwargs)` - Add equality filters
- `.where(expr)` - Add raw SQL expression
- `.select(*columns)` - Select specific columns
- `.sort(column, direction)` - Add sort order
- `.limit(n)` - Limit results
- `.offset(n)` - Skip N results

### Sampling
- `.sample_random(n)` - Random sample
- `.sample_seeded(n, seed)` - Deterministic random sample
- `.sample_stratified(by, per_group, seed=None)` - Per-group sampling

### Execution
- `.execute()` - Returns iterator
- `.all()` - Returns list
- `.first()` - Returns first record or None
- `.count()` - Count matching records
- `.preview(n=10)` - Quick preview

### Utilities
- `.get(record_id)` - Get single record by ID
- `.close()` - Close connection

---

## Tips & Best Practices

1. **Use context managers** for automatic cleanup:
   ```python
   with AgirDB.connect("semif", sqlite_path="data.db") as db:
       records = db.filter(state="NC").all()
   ```

2. **Use `.execute()` for large queries** to avoid loading everything into memory

3. **Start with `.builder()`** when building queries conditionally

4. **Use stratified sampling** for balanced datasets across categories

5. **Apply filters before sampling** for best performance

6. **Use `.count()` first** to check result size before fetching

7. **Combine filters with sampling** for targeted, balanced datasets