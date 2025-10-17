# Query Stage Examples Guide

A comprehensive collection of query examples for both SemiF and Field databases, ranging from simple to complex use cases.

---

## Table of Contents

- [Basic Queries](#basic-queries)
- [Filtering Examples](#filtering-examples)
- [Sampling Strategies](#sampling-strategies)
- [Complex Queries](#complex-queries)
- [Production Use Cases](#production-use-cases)
- [SemiF Database Examples](#semif-database-examples)
- [Field Database Examples](#field-database-examples)
- [Advanced Techniques](#advanced-techniques)

---

## Basic Queries

### Example 1: Get All Records (with limit)

**CLI:**
```bash
# Get first 100 records from SemiF
agir-cvtoolkit query --db semif --limit 100 --out csv

# Get first 50 records from Field
agir-cvtoolkit query --db field --limit 50 --out csv
```

**Python:**
```python
from agir_cvtoolkit.core.db import AgirDB

# SemiF
with AgirDB.connect(
    db_type="semif", 
    db_path="path/to/your/semif_db.db", 
    table="semif") as db:
    
    query = db.builder()
    query.preview(n=1)

# Field
with AgirDB.connect(
    db_type="field", 
    db_path="path/to/your/field_db.db", 
    table="field_data") as db:

    query = db.builder()
    query.preview(n=1)
```

---

### Example 2: Preview Records

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
from agir_cvtoolkit.core.db import AgirDB

with AgirDB.connect(
    db_type="semif", 
    db_path="path/to/your/semif_db.db", 
    table="semif") as db:

    query = db.builder()
    query.filter(state="NC").preview(10)
    query.preview(n=1)

with AgirDB.connect(
    db_type="field", 
    db_path="path/to/your/field_db.db", 
    table="field_data") as db:

    query = db.builder()
    query.filter(us_state="NC").preview(10)
    query.preview(n=1)
```

---

### Example 3: Count Records

**CLI:**
```bash
# Count all records
agir-cvtoolkit query --db semif --limit 0

# Count filtered records
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --limit 0
```

**Python:**
```python
from agir_cvtoolkit.core.db import AgirDB

with AgirDB.connect(
    db_type="semif", 
    db_path="path/to/your/semif_db.db", 
    table="semif") as db:
    
    query = db.builder()
    count = db.filter(state="NC").count()
    print(f"Count of records in NC: {count}")

with AgirDB.connect(
    db_type="field", 
    db_path="path/to/your/field_db.db", 
    table="field_data") as db:

    query = db.builder()
    count = db.filter(us_state="NC").count()
    print(f"Count of field records in NC: {count}")
```

---

## Filtering Examples

### Single Field Filters

#### Example 4: Filter by State

**CLI:**
```bash
# SemiF - Get North Carolina records
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --out csv

# Field - Get Texas records
agir-cvtoolkit query --db field \
  --filters "us_state=TX" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    nc_records = db.filter(state="NC").all()

# Field
with AgirDB.connect("field") as db:
    tx_records = db.filter(us_state="TX").all()
```

---

#### Example 5: Filter by Species

**CLI:**
```bash
# SemiF - Get barley records
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley" \
  --out csv

# Field - Get corn records
agir-cvtoolkit query --db field \
  --filters "common_name=corn" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    barley = db.filter(category_common_name="barley").all()

# Field
with AgirDB.connect("field") as db:
    corn = db.filter(common_name="corn").all()
```

---

#### Example 6: Filter by Date Range

**CLI:**
```bash
# SemiF - Records from 2024
agir-cvtoolkit query --db semif \
  --filters "datetime>=2024-01-01,datetime<2025-01-01" \
  --out csv

# Field - Specific month
agir-cvtoolkit query --db field \
  --filters "camera_datetime>=2024-05-01,camera_datetime<2024-06-01" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    records_2024 = db.where(
        "datetime >= '2024-01-01' AND datetime < '2025-01-01'"
    ).all()

# Field
with AgirDB.connect("field") as db:
    may_records = db.where(
        "camera_datetime >= '2024-05-01' AND camera_datetime < '2024-06-01'"
    ).all()
```

---

### Multiple Field Filters

#### Example 7: Combine Multiple Filters

**CLI:**
```bash
# SemiF - Barley in North Carolina
agir-cvtoolkit query --db semif \
  --filters "state=NC,category_common_name=barley" \
  --out csv

# Field - Wheat in Texas, specific growth stage
agir-cvtoolkit query --db field \
  --filters "us_state=TX,common_name=wheat,growth_stage=flowering" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    records = db.filter(
        state="NC",
        category_common_name="barley"
    ).all()

# Field
with AgirDB.connect("field") as db:
    records = db.filter(
        us_state="TX",
        common_name="wheat",
        growth_stage="flowering"
    ).all()
```

---

#### Example 8: Multiple Values for Single Field

**CLI:**
```bash
# SemiF - Multiple species
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley,wheat,rye" \
  --out csv

# Field - Multiple states
agir-cvtoolkit query --db field \
  --filters "us_state=NC,TX,CA" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    records = db.filter(
        category_common_name=["barley", "wheat", "rye"]
    ).all()

# Field
with AgirDB.connect("field") as db:
    records = db.filter(
        us_state=["NC", "TX", "CA"]
    ).all()
```

---

### Range and Comparison Filters

#### Example 9: Filter by Area/Size

**CLI:**
```bash
# SemiF - Large bounding boxes (>100 cm²)
agir-cvtoolkit query --db semif \
  --filters "estimated_bbox_area_cm2>100" \
  --out csv

# SemiF - Medium-sized objects (50-200 cm²)
agir-cvtoolkit query --db semif \
  --filters "estimated_bbox_area_cm2>=50,estimated_bbox_area_cm2<=200" \
  --out csv

# Field - Small size class
agir-cvtoolkit query --db field \
  --filters "size_class=small" \
  --out csv
```

**Python:**
```python
# SemiF - Large objects
with AgirDB.connect("semif") as db:
    large = db.where("estimated_bbox_area_cm2 > 100").all()

# SemiF - Medium objects
with AgirDB.connect("semif") as db:
    medium = db.where(
        "estimated_bbox_area_cm2 >= 50 AND estimated_bbox_area_cm2 <= 200"
    ).all()

# Field
with AgirDB.connect("field") as db:
    small = db.filter(size_class="small").all()
```

---

#### Example 10: Filter by Image Quality

**CLI:**
```bash
# SemiF - Low blur (sharp images)
agir-cvtoolkit query --db semif \
  --filters "blur_effect<50" \
  --out csv

# SemiF - High quality: sharp with good component count
agir-cvtoolkit query --db semif \
  --filters "blur_effect<30,num_components>5" \
  --out csv
```

**Python:**
```python
# SemiF - Sharp images
with AgirDB.connect("semif") as db:
    sharp = db.where("blur_effect < 50").all()

# High quality combo
with AgirDB.connect("semif") as db:
    quality = db.where(
        "blur_effect < 30 AND num_components > 5"
    ).all()
```

---

#### Example 11: Filter by Pixel Area

**CLI:**
```bash
# SemiF - Minimum pixel area (well-represented objects)
agir-cvtoolkit query --db semif \
  --filters "pixel_area>1000" \
  --out csv

# SemiF - Specific pixel area range
agir-cvtoolkit query --db semif \
  --filters "pixel_area>=500,pixel_area<=5000" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    records = db.where("pixel_area > 1000").all()
    
    # Or range
    records = db.where(
        "pixel_area >= 500 AND pixel_area <= 5000"
    ).all()
```

---

### Taxonomy Filters

#### Example 12: Filter by Taxonomic Classification

**CLI:**
```bash
# SemiF - All grasses (Poaceae family)
agir-cvtoolkit query --db semif \
  --filters "category_family=Poaceae" \
  --out csv

# SemiF - Specific genus
agir-cvtoolkit query --db semif \
  --filters "category_genus=Triticum" \
  --out csv

# Field - Taxonomic family
agir-cvtoolkit query --db field \
  --filters "taxonomic_family=Fabaceae" \
  --out csv
```

**Python:**
```python
# SemiF - Poaceae family
with AgirDB.connect("semif") as db:
    grasses = db.filter(category_family="Poaceae").all()

# Field - Fabaceae family
with AgirDB.connect("field") as db:
    legumes = db.filter(taxonomic_family="Fabaceae").all()
```

---

#### Example 13: Filter by USDA Symbol or EPPO Code

**CLI:**
```bash
# SemiF - Specific USDA symbol
agir-cvtoolkit query --db semif \
  --filters "category_usda_symbol=HORVU" \
  --out csv

# SemiF - EPPO code
agir-cvtoolkit query --db semif \
  --filters "category_eppo_code=HORVX" \
  --out csv

# Field - USDA symbol
agir-cvtoolkit query --db field \
  --filters "usda_symbol=TRIAE" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    records = db.filter(category_usda_symbol="HORVU").all()

# Field
with AgirDB.connect("field") as db:
    records = db.filter(usda_symbol="TRIAE").all()
```

---

### Boolean and Status Filters

#### Example 14: Filter by Mask Availability

**CLI:**
```bash
# SemiF - Only records with masks
agir-cvtoolkit query --db semif \
  --filters "has_masks=1" \
  --out csv

# SemiF - Records with cutouts
agir-cvtoolkit query --db semif \
  --filters "cutout_exists=1" \
  --out csv

# Field - Specific mask status
agir-cvtoolkit query --db field \
  --filters "mask_status=approved" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    with_masks = db.filter(has_masks=1).all()
    with_cutouts = db.filter(cutout_exists=1).all()

# Field
with AgirDB.connect("field") as db:
    approved = db.filter(mask_status="approved").all()
```

---

#### Example 15: Filter by Preprocessing Status

**CLI:**
```bash
# Field - Preprocessed images only
agir-cvtoolkit query --db field \
  --filters "is_preprocessed=1" \
  --out csv

# Field - Not preprocessed
agir-cvtoolkit query --db field \
  --filters "is_preprocessed=0" \
  --out csv
```

**Python:**
```python
# Field
with AgirDB.connect("field") as db:
    preprocessed = db.filter(is_preprocessed=1).all()
    not_preprocessed = db.filter(is_preprocessed=0).all()
```

---

## Sampling Strategies

### Random Sampling

#### Example 16: Simple Random Sample

**CLI:**
```bash
# SemiF - Random 200 records
agir-cvtoolkit query --db semif \
  --sample "random:n=200" \
  --out csv

# Field - Random 100 records
agir-cvtoolkit query --db field \
  --sample "random:n=100" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    sample = db.sample_random(200).all()

# Field
with AgirDB.connect("field") as db:
    sample = db.sample_random(100).all()
```

---

#### Example 17: Seeded Random Sample (Reproducible)

**CLI:**
```bash
# SemiF - Reproducible random sample
agir-cvtoolkit query --db semif \
  --sample "seeded:n=200,seed=42" \
  --out csv

# Field - Different seed
agir-cvtoolkit query --db field \
  --sample "seeded:n=150,seed=2024" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    sample = db.sample_seeded(n=200, seed=42).all()

# Field
with AgirDB.connect("field") as db:
    sample = db.sample_seeded(n=150, seed=2024).all()
```

---

### Stratified Sampling

#### Example 18: Stratify by Species

**CLI:**
```bash
# SemiF - 20 samples per species
agir-cvtoolkit query --db semif \
  --sample "stratified:by=category_common_name,per_group=20" \
  --out csv

# Field - 10 samples per species
agir-cvtoolkit query --db field \
  --sample "stratified:by=common_name,per_group=10" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    sample = db.sample_stratified(
        by=["category_common_name"],
        per_group=20
    ).all()

# Field
with AgirDB.connect("field") as db:
    sample = db.sample_stratified(
        by=["common_name"],
        per_group=10
    ).all()
```

---

#### Example 19: Stratify by Multiple Fields

**CLI:**
```bash
# SemiF - Balanced by state AND species
agir-cvtoolkit query --db semif \
  --sample "stratified:by=state+category_common_name,per_group=5" \
  --out csv

# Field - By state AND growth stage
agir-cvtoolkit query --db field \
  --sample "stratified:by=us_state+growth_stage,per_group=3" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    sample = db.sample_stratified(
        by=["state", "category_common_name"],
        per_group=5
    ).all()

# Field
with AgirDB.connect("field") as db:
    sample = db.sample_stratified(
        by=["us_state", "growth_stage"],
        per_group=3
    ).all()
```

---

#### Example 20: Stratify by Size Bins

**CLI:**
```bash
# SemiF - Equal samples across size bins
agir-cvtoolkit query --db semif \
  --sample "stratified:by=estimated_area_bin,per_group=25" \
  --out csv

# Field - By size class
agir-cvtoolkit query --db field \
  --sample "stratified:by=size_class,per_group=20" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    sample = db.sample_stratified(
        by=["estimated_area_bin"],
        per_group=25
    ).all()

# Field
with AgirDB.connect("field") as db:
    sample = db.sample_stratified(
        by=["size_class"],
        per_group=20
    ).all()
```

---

## Complex Queries

### Combining Filters and Sampling

#### Example 21: Filter Then Sample

**CLI:**
```bash
# SemiF - NC barley, stratified by size
agir-cvtoolkit query --db semif \
  --filters "state=NC,category_common_name=barley" \
  --sample "stratified:by=estimated_area_bin,per_group=15" \
  --out csv

# Field - TX crops, random sample
agir-cvtoolkit query --db field \
  --filters "us_state=TX,crop_or_fallow=crop" \
  --sample "random:n=100" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    sample = (
        db.filter(state="NC", category_common_name="barley")
        .sample_stratified(by=["estimated_area_bin"], per_group=15)
        .all()
    )

# Field
with AgirDB.connect("field") as db:
    sample = (
        db.filter(us_state="TX", crop_or_fallow="crop")
        .sample_random(100)
        .all()
    )
```

---

#### Example 22: Complex Filters with Range Constraints

**CLI:**
```bash
# SemiF - High-quality barley images with size constraints
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley,blur_effect<30,estimated_bbox_area_cm2>50,estimated_bbox_area_cm2<300" \
  --sample "random:n=200" \
  --out csv

# Field - Specific species, growth stage, and date range
agir-cvtoolkit query --db field \
  --filters "common_name=wheat,growth_stage=flowering,camera_datetime>=2024-05-01,camera_datetime<2024-06-01" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    sample = (
        db.filter(category_common_name="barley")
        .where("blur_effect < 30")
        .where("estimated_bbox_area_cm2 > 50 AND estimated_bbox_area_cm2 < 300")
        .sample_random(200)
        .all()
    )

# Field
with AgirDB.connect("field") as db:
    records = (
        db.filter(
            common_name="wheat",
            growth_stage="flowering"
        )
        .where("camera_datetime >= '2024-05-01' AND camera_datetime < '2024-06-01'")
        .all()
    )
```

---

#### Example 23: Multi-Species Balanced Dataset

**CLI:**
```bash
# SemiF - Create balanced dataset across multiple crops
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley,wheat,rye,oats" \
  --sample "stratified:by=category_common_name,per_group=50" \
  --out csv

# Field - Multiple species with quality filters
agir-cvtoolkit query --db field \
  --filters "common_name=corn,soybean,cotton,mask_status=approved" \
  --sample "stratified:by=common_name+us_state,per_group=10" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    sample = (
        db.filter(category_common_name=["barley", "wheat", "rye", "oats"])
        .sample_stratified(by=["category_common_name"], per_group=50)
        .all()
    )

# Field
with AgirDB.connect("field") as db:
    sample = (
        db.filter(
            common_name=["corn", "soybean", "cotton"],
            mask_status="approved"
        )
        .sample_stratified(
            by=["common_name", "us_state"],
            per_group=10
        )
        .all()
    )
```

---

### Column Selection and Sorting

#### Example 24: Select Specific Columns

**CLI:**
```bash
# SemiF - Only essential columns
agir-cvtoolkit query --db semif \
  --projection "cutout_id,category_common_name,state,bbox_area_cm2" \
  --limit 100 \
  --out csv

# Field - Minimal metadata
agir-cvtoolkit query --db field \
  --projection "cutout_name,common_name,us_state,camera_datetime" \
  --limit 100 \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    records = db.select(
        "cutout_id", "category_common_name", "state", "bbox_area_cm2"
    ).limit(100).all()

# Field
with AgirDB.connect("field") as db:
    records = db.select(
        "cutout_name", "common_name", "us_state", "camera_datetime"
    ).limit(100).all()
```

---

#### Example 25: Sort Results

**CLI:**
```bash
# SemiF - Sort by area (descending)
agir-cvtoolkit query --db semif \
  --sort "estimated_bbox_area_cm2:desc" \
  --limit 50 \
  --out csv

# SemiF - Sort by date (ascending) then area (descending)
agir-cvtoolkit query --db semif \
  --sort "datetime:asc,estimated_bbox_area_cm2:desc" \
  --limit 100 \
  --out csv

# Field - Sort by datetime
agir-cvtoolkit query --db field \
  --sort "camera_datetime:desc" \
  --limit 100 \
  --out csv
```

**Python:**
```python
# SemiF - Sort by area
with AgirDB.connect("semif") as db:
    records = db.sort_by("estimated_bbox_area_cm2", "desc").limit(50).all()

# Multiple sort fields
with AgirDB.connect("semif") as db:
    records = db.order_by(
        [("datetime", "asc"), ("estimated_bbox_area_cm2", "desc")]
    ).limit(100).all()
```

---

## Production Use Cases

### Use Case 1: Training Dataset Creation

**Scenario:** Create a balanced training dataset for multi-species segmentation

**CLI:**
```bash
# SemiF - Balanced species dataset with quality filters
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley,wheat,rye,oats,has_masks=1,blur_effect<50" \
  --sample "stratified:by=category_common_name+estimated_area_bin,per_group=30" \
  --out csv

# Result: 30 samples per species per size bin
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    training_data = (
        db.filter(
            category_common_name=["barley", "wheat", "rye", "oats"],
            has_masks=1
        )
        .where("blur_effect < 50")
        .sample_stratified(
            by=["category_common_name", "estimated_area_bin"],
            per_group=30
        )
        .all()
    )
    
    print(f"Training dataset: {len(training_data)} records")
```

---

### Use Case 2: Validation Set from Different Geography

**Scenario:** Create validation set from different states than training data

**CLI:**
```bash
# Training: NC and SC
agir-cvtoolkit query --db semif \
  --filters "state=NC,SC,category_common_name=barley,wheat" \
  --sample "stratified:by=category_common_name,per_group=100" \
  --out csv

# Validation: TX and CA
agir-cvtoolkit query --db semif \
  --filters "state=TX,CA,category_common_name=barley,wheat" \
  --sample "stratified:by=category_common_name,per_group=30" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    # Training set
    train = (
        db.filter(
            state=["NC", "SC"],
            category_common_name=["barley", "wheat"]
        )
        .sample_stratified(by=["category_common_name"], per_group=100)
        .all()
    )
    
    # Validation set
    val = (
        db.filter(
            state=["TX", "CA"],
            category_common_name=["barley", "wheat"]
        )
        .sample_stratified(by=["category_common_name"], per_group=30)
        .all()
    )
```

---

### Use Case 3: Temporal Data Split

**Scenario:** Use older data for training, recent data for validation

**CLI:**
```bash
# Training: 2023 data
agir-cvtoolkit query --db semif \
  --filters "datetime>=2023-01-01,datetime<2024-01-01,category_common_name=barley" \
  --sample "stratified:by=estimated_area_bin,per_group=50" \
  --out csv

# Validation: 2024 data
agir-cvtoolkit query --db semif \
  --filters "datetime>=2024-01-01,category_common_name=barley" \
  --sample "stratified:by=estimated_area_bin,per_group=20" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    # Training: 2023
    train = (
        db.filter(category_common_name="barley")
        .where("datetime >= '2023-01-01' AND datetime < '2024-01-01'")
        .sample_stratified(by=["estimated_area_bin"], per_group=50)
        .all()
    )
    
    # Validation: 2024
    val = (
        db.filter(category_common_name="barley")
        .where("datetime >= '2024-01-01'")
        .sample_stratified(by=["estimated_area_bin"], per_group=20)
        .all()
    )
```

---

### Use Case 4: Quality-Filtered Annotation Batch

**Scenario:** Select high-quality images for human annotation

**CLI:**
```bash
# SemiF - High quality images needing annotation
agir-cvtoolkit query --db semif \
  --filters "category_common_name=wheat,blur_effect<30,num_components>5,pixel_area>1000,has_masks=0" \
  --sample "stratified:by=estimated_area_bin,per_group=40" \
  --out csv

# Field - Ready for annotation
agir-cvtoolkit query --db field \
  --filters "common_name=corn,mask_status=pending,is_preprocessed=1" \
  --sample "random:n=200" \
  --out csv
```

**Python:**
```python
# SemiF
with AgirDB.connect("semif") as db:
    annotation_batch = (
        db.filter(
            category_common_name="wheat",
            has_masks=0  # Not yet annotated
        )
        .where("blur_effect < 30 AND num_components > 5 AND pixel_area > 1000")
        .sample_stratified(by=["estimated_area_bin"], per_group=40)
        .all()
    )

# Field
with AgirDB.connect("field") as db:
    annotation_batch = (
        db.filter(
            common_name="corn",
            mask_status="pending",
            is_preprocessed=1
        )
        .sample_random(200)
        .all()
    )
```

---

### Use Case 5: Hard Negative Mining

**Scenario:** Find challenging examples (small objects, edge cases)

**CLI:**
```bash
# SemiF - Small, complex objects
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley,estimated_bbox_area_cm2<30,num_components>3,extends_border=1" \
  --out csv

# Field - Edge cases
agir-cvtoolkit query --db field \
  --filters "common_name=wheat,size_class=small,final_mask_issue_tag=occlusion" \
  --out csv
```

**Python:**
```python
# SemiF - Hard examples
with AgirDB.connect("semif") as db:
    hard_examples = (
        db.filter(
            category_common_name="barley",
            extends_border=1
        )
        .where("estimated_bbox_area_cm2 < 30 AND num_components > 3")
        .all()
    )

# Field
with AgirDB.connect("field") as db:
    edge_cases = db.filter(
        common_name="wheat",
        size_class="small",
        final_mask_issue_tag="occlusion"
    ).all()
```

---

## SemiF Database Examples

### Geographic Distribution Analysis

#### Example 26: Query by State

**CLI:**
```bash
# All NC records
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --out csv

# Multiple states
agir-cvtoolkit query --db semif \
  --filters "state=NC,TX,CA" \
  --sample "stratified:by=state+category_common_name,per_group=20" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    # Single state
    nc_records = db.filter(state="NC").all()
    
    # Multi-state balanced sample
    sample = db.filter(state=["NC", "TX", "CA"]).sample_stratified(
        by=["state", "category_common_name"],
        per_group=20
    ).all()
```

---

### Camera and Image Quality

#### Example 27: Filter by Lens Model

**CLI:**
```bash
# Specific camera
agir-cvtoolkit query --db semif \
  --filters "lens_model=SIGMA 150-600mm F5-6.3 DG OS HSM | Contemporary 015" \
  --out csv

# Multiple lens models
agir-cvtoolkit query --db semif \
  --filters "lens_model=SIGMA 150-600mm F5-6.3 DG OS HSM | Contemporary 015,Canon EF 70-200mm f/2.8L IS III USM" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    records = db.filter(
        lens_model="SIGMA 150-600mm F5-6.3 DG OS HSM | Contemporary 015"
    ).all()
```

---

#### Example 28: Image Quality Metrics

**CLI:**
```bash
# Sharp images only
agir-cvtoolkit query --db semif \
  --filters "blur_effect<40" \
  --sample "random:n=500" \
  --out csv

# High component count (well-segmented)
agir-cvtoolkit query --db semif \
  --filters "num_components>8" \
  --out csv

# Combined quality filters
agir-cvtoolkit query --db semif \
  --filters "blur_effect<30,num_components>5,pixel_area>2000" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    # Sharp images
    sharp = db.where("blur_effect < 40").sample_random(500).all()
    
    # High quality combo
    quality = db.where(
        "blur_effect < 30 AND num_components > 5 AND pixel_area > 2000"
    ).all()
```

---

### Bounding Box and Spatial Filters

#### Example 29: Border-Extending Objects

**CLI:**
```bash
# Objects extending to image border
agir-cvtoolkit query --db semif \
  --filters "extends_border=1" \
  --out csv

# Non-border objects only
agir-cvtoolkit query --db semif \
  --filters "extends_border=0" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    border_objects = db.filter(extends_border=1).all()
    non_border = db.filter(extends_border=0).all()
```

---

#### Example 30: Area-Based Selection

**CLI:**
```bash
# Very large objects
agir-cvtoolkit query --db semif \
  --filters "estimated_bbox_area_cm2>500" \
  --out csv

# Specific size range
agir-cvtoolkit query --db semif \
  --filters "estimated_bbox_area_cm2>=100,estimated_bbox_area_cm2<=200" \
  --out csv

# By estimated area bin
agir-cvtoolkit query --db semif \
  --filters "estimated_area_bin=medium" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    # Large objects
    large = db.where("estimated_bbox_area_cm2 > 500").all()
    
    # Size range
    range_objs = db.where(
        "estimated_bbox_area_cm2 >= 100 AND estimated_bbox_area_cm2 <= 200"
    ).all()
    
    # Size bin
    medium = db.filter(estimated_area_bin="medium").all()
```

---

### Batch and Season Filters

#### Example 31: Query by Batch

**CLI:**
```bash
# Specific batch
agir-cvtoolkit query --db semif \
  --filters "batch_id=batch_2024_05_NC_barley" \
  --out csv

# Multiple batches
agir-cvtoolkit query --db semif \
  --filters "batch_id=batch_001,batch_002,batch_003" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    batch = db.filter(batch_id="batch_2024_05_NC_barley").all()
    multiple = db.filter(batch_id=["batch_001", "batch_002"]).all()
```

---

#### Example 32: Season-Based Queries

**CLI:**
```bash
# Spring season
agir-cvtoolkit query --db semif \
  --filters "season=spring" \
  --out csv

# Multiple seasons
agir-cvtoolkit query --db semif \
  --filters "season=spring,summer" \
  --sample "stratified:by=season+category_common_name,per_group=25" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    spring = db.filter(season="spring").all()
    
    # Balanced across seasons and species
    sample = db.filter(season=["spring", "summer"]).sample_stratified(
        by=["season", "category_common_name"],
        per_group=25
    ).all()
```

---

### Path and Storage Queries

#### Example 33: Query by Storage Location

**CLI:**
```bash
# Specific NFS path prefix
agir-cvtoolkit query --db semif \
  --filters "ncsu_nfs=/mnt/storage/images/2024/" \
  --out csv

# Check cutout paths
agir-cvtoolkit query --db semif \
  --filters "cutout_path=/path/to/cutouts/,cutout_exists=1" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    # By NFS path (use LIKE for prefix matching)
    records = db.where("ncsu_nfs LIKE '/mnt/storage/images/2024/%'").all()
    
    # Existing cutouts
    cutouts = db.filter(cutout_exists=1).where(
        "cutout_path LIKE '/path/to/cutouts/%'"
    ).all()
```

---

## Field Database Examples

### Crop Classification

#### Example 34: Crop vs Fallow

**CLI:**
```bash
# Crop fields only
agir-cvtoolkit query --db field \
  --filters "crop_or_fallow=crop" \
  --out csv

# Fallow fields
agir-cvtoolkit query --db field \
  --filters "crop_or_fallow=fallow" \
  --out csv

# Cover crops by family
agir-cvtoolkit query --db field \
  --filters "cover_crop_family=Fabaceae" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("field") as db:
    crops = db.filter(crop_or_fallow="crop").all()
    fallow = db.filter(crop_or_fallow="fallow").all()
    legume_cover = db.filter(cover_crop_family="Fabaceae").all()
```

---

#### Example 35: Crop Type and Variety

**CLI:**
```bash
# Primary crop type
agir-cvtoolkit query --db field \
  --filters "common_name=cotton" \
  --out csv

# Secondary crop type
agir-cvtoolkit query --db field \
  --filters "crop_type_secondary=winter_wheat" \
  --out csv

# Specific cotton variety
agir-cvtoolkit query --db field \
  --filters "cotton_variety=Delta Pine 1646" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("field") as db:
    cotton = db.filter(common_name="cotton").all()
    winter_wheat = db.filter(crop_type_secondary="winter_wheat").all()
    variety = db.filter(cotton_variety="Delta Pine 1646").all()
```

---

### Growth Stage Analysis

#### Example 36: Filter by Growth Stage

**CLI:**
```bash
# Flowering stage
agir-cvtoolkit query --db field \
  --filters "growth_stage=flowering" \
  --out csv

# Multiple growth stages
agir-cvtoolkit query --db field \
  --filters "growth_stage=seedling,vegetative,flowering" \
  --sample "stratified:by=growth_stage+common_name,per_group=15" \
  --out csv

# Specific phenology
agir-cvtoolkit query --db field \
  --filters "flower_fruit_or_seeds=1" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("field") as db:
    flowering = db.filter(growth_stage="flowering").all()
    
    # Multi-stage balanced
    sample = db.filter(
        growth_stage=["seedling", "vegetative", "flowering"]
    ).sample_stratified(
        by=["growth_stage", "common_name"],
        per_group=15
    ).all()
    
    # With reproductive structures
    reproductive = db.filter(flower_fruit_or_seeds=1).all()
```

---

### Field Conditions

#### Example 37: Ground Cover and Residue

**CLI:**
```bash
# High ground cover
agir-cvtoolkit query --db field \
  --filters "ground_cover=high" \
  --out csv

# Specific residue type
agir-cvtoolkit query --db field \
  --filters "ground_residue=corn_stalks" \
  --out csv

# Combined conditions
agir-cvtoolkit query --db field \
  --filters "ground_cover=medium,ground_residue=wheat_stubble" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("field") as db:
    high_cover = db.filter(ground_cover="high").all()
    corn_residue = db.filter(ground_residue="corn_stalks").all()
    
    # Combined
    conditions = db.filter(
        ground_cover="medium",
        ground_residue="wheat_stubble"
    ).all()
```

---

#### Example 38: Weather Conditions

**CLI:**
```bash
# Cloud cover
agir-cvtoolkit query --db field \
  --filters "cloud_cover=clear" \
  --out csv

# Various cloud conditions
agir-cvtoolkit query --db field \
  --filters "cloud_cover=partly_cloudy,overcast" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("field") as db:
    clear_sky = db.filter(cloud_cover="clear").all()
    cloudy = db.filter(cloud_cover=["partly_cloudy", "overcast"]).all()
```

---

### Mask and Annotation Status

#### Example 39: Mask Review Status

**CLI:**
```bash
# Approved masks
agir-cvtoolkit query --db field \
  --filters "mask_status=approved" \
  --out csv

# Pending review
agir-cvtoolkit query --db field \
  --filters "mask_status=pending" \
  --out csv

# By reviewer
agir-cvtoolkit query --db field \
  --filters "mask_reviewer=john.doe@example.com,mask_status=approved" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("field") as db:
    approved = db.filter(mask_status="approved").all()
    pending = db.filter(mask_status="pending").all()
    
    # By reviewer
    johns_masks = db.filter(
        mask_reviewer="john.doe@example.com",
        mask_status="approved"
    ).all()
```

---

#### Example 40: Issue Tags

**CLI:**
```bash
# Initial mask issues
agir-cvtoolkit query --db field \
  --filters "initial_mask_issue_tag=occlusion" \
  --out csv

# Final mask issues
agir-cvtoolkit query --db field \
  --filters "final_mask_issue_tag=edge_artifacts" \
  --out csv

# No issues
agir-cvtoolkit query --db field \
  --filters "final_mask_issue_tag=none" \
  --sample "random:n=300" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("field") as db:
    occlusion = db.filter(initial_mask_issue_tag="occlusion").all()
    edge_issues = db.filter(final_mask_issue_tag="edge_artifacts").all()
    clean = db.filter(final_mask_issue_tag="none").sample_random(300).all()
```

---

### Detection and Prediction Confidence

#### Example 41: High Confidence Detections

**CLI:**
```bash
# High detection confidence
agir-cvtoolkit query --db field \
  --filters "det_pred_conf>0.9" \
  --out csv

# Detection confidence range
agir-cvtoolkit query --db field \
  --filters "det_pred_conf>=0.7,det_pred_conf<0.9" \
  --out csv

# Has matching prediction
agir-cvtoolkit query --db field \
  --filters "has_mat_pred=1,has_mat_pred_conf>0.8" \
  --out csv
```

**Python:**
```python
with AgirDB.connect("field") as db:
    high_conf = db.where("det_pred_conf > 0.9").all()
    
    medium_conf = db.where(
        "det_pred_conf >= 0.7 AND det_pred_conf < 0.9"
    ).all()
    
    matching_preds = db.filter(has_mat_pred=1).where(
        "has_mat_pred_conf > 0.8"
    ).all()
```

---

## Advanced Techniques

### Custom SQL Filters

#### Example 42: Complex WHERE Clauses

**CLI:**
```bash
# Complex logic with OR
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley,state=NC" \
  --out csv
# Note: CLI filters are AND-ed. For OR logic, use Python API

# Range with negation (use Python for NOT)
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    # OR logic
    records = db.where(
        "category_common_name = 'barley' OR category_common_name = 'wheat'"
    ).filter(state="NC").all()
    
    # Complex combination
    records = db.where(
        "(estimated_bbox_area_cm2 > 100 OR pixel_area > 5000) AND blur_effect < 40"
    ).all()
    
    # NOT operator
    records = db.where(
        "category_common_name = 'barley' AND NOT extends_border = 1"
    ).all()
```

---

#### Example 43: String Pattern Matching

**Python:**
```python
with AgirDB.connect("semif") as db:
    # LIKE for pattern matching
    wheat_varieties = db.where(
        "category_common_name LIKE '%wheat%'"
    ).all()
    
    # Starts with
    spring_crops = db.where(
        "season LIKE 'spring%'"
    ).all()
    
    # Field database - batch patterns
with AgirDB.connect("field") as db:
    nc_batches = db.where(
        "batch_id LIKE '%_NC_%'"
    ).all()
```

---

### Pagination and Offset

#### Example 44: Paginated Queries

**CLI:**
```bash
# Page 1 (records 0-99)
agir-cvtoolkit query --db semif \
  --limit 100 \
  --offset 0 \
  --out csv

# Page 2 (records 100-199)
agir-cvtoolkit query --db semif \
  --limit 100 \
  --offset 100 \
  --out csv

# Page 3 (records 200-299)
agir-cvtoolkit query --db semif \
  --limit 100 \
  --offset 200 \
  --out csv
```

**Python:**
```python
with AgirDB.connect("semif") as db:
    page_size = 100
    
    # Page 1
    page1 = db.limit(page_size).offset(0).all()
    
    # Page 2
    page2 = db.limit(page_size).offset(page_size).all()
    
    # Or use helper
    for page_num in range(5):
        page = db.limit(page_size).offset(page_num * page_size).all()
        print(f"Page {page_num + 1}: {len(page)} records")
```

---

### Combining Multiple Query Objects

#### Example 45: Reusable Query Components

**Python:**
```python
with AgirDB.connect("semif") as db:
    # Base query for high quality
    base_quality = db.where("blur_effect < 40 AND pixel_area > 1000")
    
    # Different species on same quality base
    barley_hq = base_quality.filter(category_common_name="barley").all()
    wheat_hq = base_quality.filter(category_common_name="wheat").all()
    
    # Or combine with different sampling
    sample1 = base_quality.filter(state="NC").sample_random(100).all()
    sample2 = base_quality.filter(state="TX").sample_random(100).all()
```

---

### Export and Data Processing

#### Example 46: Export to Different Formats

**CLI:**
```bash
# JSON format (default)
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --out json

# CSV format (recommended for Excel)
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --out csv

# Parquet format (efficient for large datasets)
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --out parquet
```

**Python:**
```python
import pandas as pd
from agir_cvtoolkit.core.db import AgirDB

with AgirDB.connect("semif") as db:
    records = db.filter(state="NC").all()
    
    # Convert to DataFrame
    df = pd.DataFrame([r.model_dump() for r in records])
    
    # Save to various formats
    df.to_csv("output.csv", index=False)
    df.to_parquet("output.parquet")
    df.to_json("output.json", orient="records")
```

---

## Query Reproducibility

### Example 47: Save and Load Query Specs

**Workflow:**
```bash
# 1. Run a query
agir-cvtoolkit query --db semif \
  --filters "state=NC,category_common_name=barley" \
  --sample "stratified:by=estimated_area_bin,per_group=20" \
  --out csv

# This creates: outputs/runs/{run_id}/query/query_spec.json

# 2. Reproduce the query later
python -m agir_cvtoolkit.pipelines.utils.query_utils reproduce \
  outputs/runs/{run_id}/query/query_spec.json

# 3. Copy and run the output command
```

**Python:**
```python
from agir_cvtoolkit.core.db.types import QuerySpec

# Load previous query
spec = QuerySpec.from_json("outputs/runs/abc123/query/query_spec.json")

# Reproduce
with AgirDB.connect(spec.database) as db:
    records = spec.execute(db).all()
    
# Modify and run
spec.filters["state"] = "TX"  # Change state
with AgirDB.connect(spec.database) as db:
    new_records = spec.execute(db).all()
```

---

## Best Practices Summary

### 1. Start Simple
- Begin with basic filters
- Add complexity incrementally
- Use `--preview` to test before full query

### 2. Use Stratified Sampling
- For balanced training datasets
- Prevents class imbalance
- Ensures geographic/temporal diversity

### 3. Filter Before Sampling
- Reduces data to relevant subset first
- More efficient than sampling then filtering
- Better statistical properties

### 4. Save Query Specs
- Every query creates `query_spec.json`
- Use for reproducibility
- Share with team for consistency

### 5. Select Only Needed Columns
- Use `--projection` for large queries
- Reduces memory usage
- Faster data transfer

### 6. Use Appropriate Output Format
- CSV: Human-readable, Excel-compatible
- JSON: Structured, nested data
- Parquet: Large datasets, efficient storage

---

## Common Issues

### Issue 1: "No records found"
**Solution:** Remove filters one-by-one to identify which is too restrictive

### Issue 2: "Ambiguous column name"
**Solution:** Check schema to ensure field exists in that database

### Issue 3: "Sampling returned fewer records than requested"
**Solution:** Not enough records in each stratification group

### Issue 4: "Query too slow"
**Solutions:**
- Add `--limit` to restrict results
- Use more specific filters
- Select fewer columns with `--projection`

---

## Additional Resources

- **Query User Guide**: `docs/db_query_usage.md`
- **Query Specs Guide**: `docs/query_specs_quick_reference.md`
- **Schema Documentation**: See database schema files
- **Python API Reference**: Check docstrings in `agir_cvtoolkit.core.db`

---

**Last Updated:** October 2025
