---
layout: default
title: FIELD Database
parent: Dataset
nav_order: 2
---

# FIELD Database
{: .no_toc }

Field Observation Database - Comprehensive field observations with detailed agricultural context, phenology, and quality control workflows.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

<div class="db-card" markdown="1">

**Database Name:** FIELD (Field Observation Database)

**Purpose:** Comprehensive field observation database for plant specimens with detailed agricultural context, taxonomy, quality control workflows, and phenological tracking. Designed for agricultural research and monitoring applications.

</div>

<div class="stats-grid" markdown="1">

<div class="stat-card">
<span class="stat-number">72</span>
<span class="stat-label">Attributes</span>
</div>

<div class="stat-card">
<span class="stat-number">40K+</span>
<span class="stat-label">Observations</span>
</div>

<div class="stat-card">
<span class="stat-number">Multi-Stage</span>
<span class="stat-label">QC Workflow</span>
</div>

<div class="stat-card">
<span class="stat-number">5</span>
<span class="stat-label">US States</span>
</div>

</div>

---
<!-- 
## Primary Use Cases

<div class="feature-grid" markdown="1">

<div class="feature-card" markdown="1">
<div class="feature-icon">🚜</div>

**Agricultural Monitoring**  
Comprehensive field condition tracking with crop and ground cover data
</div>

<div class="feature-card" markdown="1">
<div class="feature-icon">🌱</div>

**Phenological Research**  
Detailed growth stage and reproductive structure tracking
</div>

<div class="feature-card" markdown="1">
<div class="feature-icon">✅</div>

**Quality Control Workflows**  
Multi-stage mask review and validation processes
</div>

<div class="feature-card" markdown="1">
<div class="feature-icon">🔗</div>

**Cross-Database Integration**  
Extensive linking with WIR (Weed Image Repository) system
</div>

<div class="feature-card" markdown="1">
<div class="feature-icon">🌤️</div>

**Field Context Analysis**  
Environmental conditions including cloud cover, residue, and ground conditions
</div>

<div class="feature-card" markdown="1">
<div class="feature-icon">📸</div>

**Dual Image Formats**  
Support for both RAW and JPG image pairs
</div>

</div>

--- -->

## Key Features

{: .note }
> **What Makes FIELD Special**: Rich agricultural context, multi-stage quality control, phenological data, dual image formats, and extensive external database linkage.

- **Comprehensive Agricultural Context**: Detailed crop variety, cover crop, and field condition tracking
- **Multi-Stage Quality Control**: Initial and final mask review with issue tagging and reviewer tracking
- **Rich Phenological Data**: Growth stage, reproductive structures, and plant characteristics
- **Dual Image Formats**: Support for both RAW and JPG image pairs
- **Extensive External Linkage**: Multiple WIR database rowkey references for cross-system integration
- **Temporal Tracking**: Multiple timestamps for capture, upload, insertion, and mask modification

---

## Schema Documentation

### 1. Core Identifiers

Unique identifiers and batch information.

| Field | Type | Description |
|:------|:-----|:------------|
| `id` | Integer | Primary key, unique record identifier |
| `alias` | String | Alternative or simplified identifier |
| `batch_id` | String | Processing batch identifier |
| `image_id` | String | Unique identifier for the image |
| `image_index` | Integer | Sequential index within a batch or collection |
| `cutout_name` | Float | Name of the associated cutout image |

---

### 2. Temporal Information

Complete timestamp tracking for all processing stages.

| Field | Type | Description |
|:------|:-----|:------------|
| `camera_datetime` | Date | Date and time when image was captured |
| `db_insert_datetime` | Date | Timestamp when record was inserted into database |
| `upload_datetime_utc` | Date | UTC timestamp of image upload |
| `mask_timestamp` | Float | Timestamp of mask creation or modification |

{: .tip }
> **Temporal Analysis**: Use these timestamps to analyze processing latency, seasonal patterns, and annotation workflow efficiency.

---

### 3. Geographic & Agricultural Context

Field-level environmental and crop information.

| Field | Type | Description |
|:------|:-----|:------------|
| `us_state` | String | US state where observation was made |
| `crop_or_fallow` | String | Field status: actively cropped or fallow |
| `crop_type_secondary` | String | Secondary crop type classification |
| `cotton_variety` | String | Specific cotton variety if applicable |
| `cover_crop_family` | String | Taxonomic family of cover crop |
| `cloud_cover` | String | Cloud cover conditions during capture |
| `ground_cover` | String | Description of ground cover conditions |
| `ground_residue` | String | Type and amount of residue on ground |

{: .important }
> **Agricultural Context**: This database excels at capturing field-level context that is minimal or absent in other plant databases.

**Example agricultural context:**
```
crop_or_fallow: "Cropped"
crop_type_secondary: "Cotton"
cotton_variety: "DP 1646 B2XF"
cover_crop_family: "Fabaceae"
ground_cover: "Moderate"
ground_residue: "High - cotton stalks"
cloud_cover: "Partly cloudy"
```

---

### 4. File Paths & Storage

Locations for images, masks, and various processing stages.

| Field | Type | Description |
|:------|:-----|:------------|
| `image_url` | String | URL or path to access the image |
| `developed_image_path` | String | Path to processed/developed image |
| `raw_image_path` | String | Path to raw unprocessed image |
| `cutout_image_path` | Float | Path to cutout/cropped image |
| `final_mask_path` | Float | Path to final approved segmentation mask |
| `final_cutout_path` | Float | Path to final cutout image |
| `extension` | String | File extension type |

{: .tip }
> **RAW + JPG Support**: Use `has_matching_jpg_and_raw` to find image pairs for high-quality analysis.

---

### 5. Image Technical Details

Camera metadata and image properties.

| Field | Type | Description |
|:------|:-----|:------------|
| `exif_meta` | String | EXIF metadata from camera |
| `height` | String | Image height dimension |
| `size_mib` | Float | File size in mebibytes (MiB) |
| `has_matching_jpg_and_raw` | Integer | Boolean flag for paired JPG and RAW files |
| `is_preprocessed` | Integer | Boolean flag indicating preprocessing status |

---

### 6. Detection & Classification

Model predictions and confidence scores.

| Field | Type | Description |
|:------|:-----|:------------|
| `class_id` | Integer | Numeric class identifier |
| `bbox_xywh` | Float | Bounding box coordinates [x, y, width, height] |
| `det_pred_conf` | Float | Detection prediction confidence score (0-1) |
| `app_species` | String | Application-level species identifier |
| `has_mat_pred` | Float | Boolean flag for material/mat prediction |
| `has_mat_pred_conf` | Float | Confidence score for material prediction |

**Confidence filtering:**
```python
# High confidence detections
det_pred_conf > 0.85

# Very high confidence
det_pred_conf > 0.95
```

---

### 7. Complete Taxonomic Information

Full taxonomic hierarchy with external database codes.

| Field | Type | Description |
|:------|:-----|:------------|
| `usda_symbol` | String | USDA PLANTS database symbol |
| `eppo` | String | EPPO code |
| `common_name` | String | Common name of the plant |
| `taxonomic_group` | String | High-level taxonomic group |
| `taxonomic_class` | String | Taxonomic class |
| `taxonomic_subclass` | String | Taxonomic subclass |
| `taxonomic_order` | String | Taxonomic order |
| `taxonomic_family` | String | Taxonomic family |
| `taxonomic_genus` | String | Taxonomic genus |
| `taxonomic_species_name` | String | Full species name |
| `taxonomic_authority` | String | Authority citation for taxonomy |
| `multi_species_USDA_symbol` | Float | Multiple species USDA symbols if applicable |

**Example taxonomy:**
```
common_name: "Palmer amaranth"
usda_symbol: "AMPA"
eppo: "AMAPA"
taxonomic_family: "Amaranthaceae"
taxonomic_genus: "Amaranthus"
taxonomic_species_name: "Amaranthus palmeri"
taxonomic_authority: "S. Watson"
```

---

### 8. Plant Characteristics & Phenology

Growth stages, reproductive structures, and morphology.

| Field | Type | Description |
|:------|:-----|:------------|
| `plant_type` | String | General plant type classification |
| `growth_habit` | String | Growth habit (forb, grass, shrub, vine, tree) |
| `duration` | String | Life cycle duration (annual, biennial, perennial) |
| `growth_stage` | String | Current phenological growth stage |
| `flower_fruit_or_seeds` | Integer | Boolean flag for presence of reproductive structures |
| `stem` | String | Stem characteristics description |
| `size_class` | String | Categorical size classification |

{: .note }
> **Phenological Research**: These fields enable detailed growth stage tracking and reproductive phenology studies.

**Growth stages** may include:
- Seedling / Cotyledon
- Vegetative
- Bolting
- Flowering
- Seed set
- Senescence

**Example phenological data:**
```
growth_stage: "Flowering"
flower_fruit_or_seeds: 1
duration: "Annual"
growth_habit: "Forb"
size_class: "Large"
```

---

### 9. Quality Control & Review

Multi-stage annotation workflow tracking.

| Field | Type | Description |
|:------|:-----|:------------|
| `mask_status` | Float | Status of mask review/approval |
| `mask_reviewer` | Float | Identifier of person who reviewed mask |
| `initial_mask_issue_tag` | Float | Tag for issues found in initial mask |
| `final_mask_issue_tag` | Float | Tag for issues in final mask |
| `refine_params` | Float | Parameters used for mask refinement |
| `processing_note` | Float | Notes about processing steps or issues |
| `tags` | Float | General tags for categorization or flagging |
| `category_note` | Float | Notes specific to category assignment |

{: .important }
> **Quality Workflow**: The FIELD database implements a comprehensive 5-stage quality control pipeline (see below).

---

### 10. Reference IDs & External Links

Integration with WIR (Weed Image Repository) system.

| Field | Type | Description |
|:------|:-----|:------------|
| `wirmaster_ref_id` | String | Reference ID to master WIR database |
| `wirmastermeta_rowkey` | String | Row key for WIR master metadata table |
| `wircovercropsmeta_rowkey` | String | Row key for WIR cover crops metadata |
| `wircropsmeta_rowkey` | String | Row key for WIR crops metadata |
| `wirimagerefs_rowkey` | String | Row key for WIR image references |
| `wirweedsmeta_rowkey` | String | Row key for WIR weeds metadata |
| `link` | String | General reference link or URL |

**WIR Integration** provides cross-references to:
- Master metadata records
- Crop-specific information
- Cover crop details
- Weed species data
- Image references

---

### 11. Visualization

Display properties for rendering.

| Field | Type | Description |
|:------|:-----|:------------|
| `rgb` | String | RGB color values for visualization |

---

## Quality Control Workflow

The FIELD database supports a comprehensive quality control pipeline:

<div class="db-card" markdown="1">

### Stage 1: Initial Processing
- **Field**: `is_preprocessed`
- **Notes**: `processing_note`
- **Action**: Basic image processing and validation

</div>

<div class="db-card" markdown="1">

### Stage 2: Initial Mask Review
- **Field**: `initial_mask_issue_tag`
- **Reviewer**: `mask_reviewer`
- **Action**: First pass quality check and issue identification

</div>

<div class="db-card" markdown="1">

### Stage 3: Mask Refinement
- **Field**: `refine_params`
- **Action**: Adjustment tracking and parameter tuning

</div>

<div class="db-card" markdown="1">

### Stage 4: Final Review
- **Field**: `final_mask_issue_tag`
- **Status**: `mask_status`
- **Action**: Final quality approval

</div>

<div class="db-card" markdown="1">

### Stage 5: Approval & Export
- **Fields**: `final_mask_path`, `final_cutout_path`
- **Action**: Generation of approved final outputs

</div>

---

## External Integrations

<div class="feature-grid" markdown="1">

<div class="feature-card" markdown="1">

**USDA PLANTS Database**  
Access via `usda_symbol`

[Visit USDA PLANTS →](https://plants.usda.gov/)
</div>

<div class="feature-card" markdown="1">

**EPPO Database**  
Access via `eppo` code

[Visit EPPO →](https://www.eppo.int/)
</div>

<div class="feature-card" markdown="1">

**WIR System**  
Extensive cross-database linking

Multiple rowkey references
</div>

</div>

---

## Data Quality Indicators

Use these fields to filter for high-quality data:

| Indicator | Field | Recommended Value |
|:----------|:------|:------------------|
| **Detection Confidence** | `det_pred_conf` | `> 0.85` (high confidence) |
| **Material Confidence** | `has_mat_pred_conf` | `> 0.8` (if applicable) |
| **Mask Status** | `mask_status` | Approved/completed |
| **Image Format** | `has_matching_jpg_and_raw` | `1` (paired formats) |
| **File Size** | `size_mib` | Check for reasonable values |
| **Reviewer** | `mask_reviewer` | Not null (human reviewed) |

---

## Agricultural Context Fields

{: .tip }
> **Unique Strength**: The FIELD database excels at capturing agricultural context that is minimal or absent in other plant databases.

### What's Captured:

✅ **Crop Information**
- Primary and secondary crop types
- Specific varieties (e.g., cotton varieties)
- Cover crop families

✅ **Field Status**
- Active cropping vs. fallow
- Crop rotation information

✅ **Environmental Conditions**
- Cloud cover during capture
- Ground cover descriptions
- Residue type and amount

✅ **Geographic Context**
- US state location
- Field-level coordinates

---

## Accessing the Data

{: .note }
> **Query this database** using the AgIR-CVToolkit. The toolkit supports filtering by crop type, phenology, quality metrics, and more.

[Learn How to Query FIELD →](https://github.com/yourusername/AgIR-CVToolkit/blob/main/docs/PIPELINE_STAGES/01_query/db_query_usage.md){: .btn .btn-primary }
[View Complete Query Guide →](../access/query-guide.html){: .btn .btn-primary }

---

## Comparison with SEMIF

| Feature | SEMIF | FIELD |
|:--------|:------|:------|
| **Focus** | ML training | Agricultural research |
| **Records** | Individual cutouts | Field specimens |
| **Attributes** | 62 | 72 |
| **Primary Use** | Object detection | Context analysis |
| **Annotations** | Bounding boxes | Phenology + context |
| **Quality Control** | Automated metrics | Multi-stage human review |
| **Agricultural Context** | Minimal | Extensive |
| **External Links** | USDA, EPPO | USDA, EPPO, WIR system |

{: .note }
> **When to Use**: Choose **SEMIF** for training object detection models. Choose **FIELD** for agricultural research requiring crop context and phenological data.

---

## Next Steps

<div class="feature-grid" markdown="1">

<div class="feature-card" markdown="1">

**📊 View Statistics**  
Explore phenological and geographic distributions

[Statistics →](../statistics/overview.html)
</div>

<div class="feature-card" markdown="1">

**🖼️ See Examples**  
Browse field observations with context

[Gallery →](../examples/gallery.html)
</div>

<div class="feature-card" markdown="1">

**🔧 Access the Data**  
Learn how to query with AgIR-CVToolkit

[Query Documentation →](https://github.com/yourusername/AgIR-CVToolkit/blob/main/docs/PIPELINE_STAGES/01_query/)
</div>

<div class="feature-card" markdown="1">

**🤖 Compare with SEMIF**  
See the ML-optimized database

[SEMIF Database →](semif.html)
</div>

</div>