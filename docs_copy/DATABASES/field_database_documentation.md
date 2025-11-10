# FIELD Database Documentation

## Overview

**Database Name:** FIELD (Field Observation Database)

**Purpose:** Comprehensive field observation database for plant specimens with detailed agricultural context, taxonomy, quality control workflows, and phenological tracking. Designed for agricultural research and monitoring applications.

**Record Count:** Variable (sample: 10 rows)  
**Column Count:** 72

---

## Schema Documentation

### 1. Core Identifiers

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key, unique record identifier |
| `alias` | String | Alternative or simplified identifier |
| `batch_id` | String | Processing batch identifier |
| `image_id` | String | Unique identifier for the image |
| `image_index` | Integer | Sequential index within a batch or collection |
| `cutout_name` | Float | Name of the associated cutout image |

### 2. Temporal Information

| Field | Type | Description |
|-------|------|-------------|
| `camera_datetime` | Date | Date and time when image was captured |
| `db_insert_datetime` | Date | Timestamp when record was inserted into database |
| `upload_datetime_utc` | Date | UTC timestamp of image upload |
| `mask_timestamp` | Float | Timestamp of mask creation or modification |

### 3. Geographic & Agricultural Context

| Field | Type | Description |
|-------|------|-------------|
| `us_state` | String | US state where observation was made |
| `crop_or_fallow` | String | Field status: actively cropped or fallow |
| `crop_type_secondary` | String | Secondary crop type classification |
| `cotton_variety` | String | Specific cotton variety if applicable |
| `cover_crop_family` | String | Taxonomic family of cover crop |
| `cloud_cover` | String | Cloud cover conditions during capture |
| `ground_cover` | String | Description of ground cover conditions |
| `ground_residue` | String | Type and amount of residue on ground |

### 4. File Paths & Storage

| Field | Type | Description |
|-------|------|-------------|
| `image_url` | String | URL or path to access the image |
| `developed_image_path` | String | Path to processed/developed image |
| `raw_image_path` | String | Path to raw unprocessed image |
| `cutout_image_path` | Float | Path to cutout/cropped image |
| `final_mask_path` | Float | Path to final approved segmentation mask |
| `final_cutout_path` | Float | Path to final cutout image |
| `extension` | String | File extension type |

### 5. Image Technical Details

| Field | Type | Description |
|-------|------|-------------|
| `exif_meta` | String | EXIF metadata from camera |
| `height` | String | Image height dimension |
| `size_mib` | Float | File size in mebibytes (MiB) |
| `has_matching_jpg_and_raw` | Integer | Boolean flag for paired JPG and RAW files |
| `is_preprocessed` | Integer | Boolean flag indicating preprocessing status |

### 6. Detection & Classification

| Field | Type | Description |
|-------|------|-------------|
| `class_id` | Integer | Numeric class identifier |
| `bbox_xywh` | Float | Bounding box coordinates [x, y, width, height] |
| `det_pred_conf` | Float | Detection prediction confidence score (0-1) |
| `app_species` | String | Application-level species identifier |
| `has_mat_pred` | Float | Boolean flag for material/mat prediction |
| `has_mat_pred_conf` | Float | Confidence score for material prediction |

### 7. Complete Taxonomic Information

| Field | Type | Description |
|-------|------|-------------|
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

### 8. Plant Characteristics & Phenology

| Field | Type | Description |
|-------|------|-------------|
| `plant_type` | String | General plant type classification |
| `growth_habit` | String | Growth habit (forb, grass, shrub, vine, tree) |
| `duration` | String | Life cycle duration (annual, biennial, perennial) |
| `growth_stage` | String | Current phenological growth stage |
| `flower_fruit_or_seeds` | Integer | Boolean flag for presence of reproductive structures |
| `stem` | String | Stem characteristics description |
| `size_class` | String | Categorical size classification |

### 9. Quality Control & Review

| Field | Type | Description |
|-------|------|-------------|
| `mask_status` | Float | Status of mask review/approval |
| `mask_reviewer` | Float | Identifier of person who reviewed mask |
| `initial_mask_issue_tag` | Float | Tag for issues found in initial mask |
| `final_mask_issue_tag` | Float | Tag for issues in final mask |
| `refine_params` | Float | Parameters used for mask refinement |
| `processing_note` | Float | Notes about processing steps or issues |
| `tags` | Float | General tags for categorization or flagging |
| `category_note` | Float | Notes specific to category assignment |

### 10. Reference IDs & External Links

| Field | Type | Description |
|-------|------|-------------|
| `wirmaster_ref_id` | String | Reference ID to master WIR database |
| `wirmastermeta_rowkey` | String | Row key for WIR master metadata table |
| `wircovercropsmeta_rowkey` | String | Row key for WIR cover crops metadata |
| `wircropsmeta_rowkey` | String | Row key for WIR crops metadata |
| `wirimagerefs_rowkey` | String | Row key for WIR image references |
| `wirweedsmeta_rowkey` | String | Row key for WIR weeds metadata |
| `link` | String | General reference link or URL |

### 11. Visualization

| Field | Type | Description |
|-------|------|-------------|
| `rgb` | String | RGB color values for visualization |

---

## Primary Use Cases

- **Agricultural Monitoring**: Comprehensive field condition tracking with crop and ground cover data
- **Phenological Research**: Detailed growth stage and reproductive structure tracking
- **Quality Control Workflows**: Multi-stage mask review and validation processes
- **Cross-Database Integration**: Extensive linking with WIR (Weed Image Repository) system
- **Field Context Analysis**: Environmental conditions including cloud cover, residue, and ground conditions

---

## Key Features

- **Comprehensive Agricultural Context**: Detailed crop variety, cover crop, and field condition tracking
- **Multi-Stage Quality Control**: Initial and final mask review with issue tagging and reviewer tracking
- **Rich Phenological Data**: Growth stage, reproductive structures, and plant characteristics
- **Dual Image Formats**: Support for both RAW and JPG image pairs
- **Extensive External Linkage**: Multiple WIR database rowkey references for cross-system integration
- **Temporal Tracking**: Multiple timestamps for capture, upload, insertion, and mask modification

---

## External Integrations

- **USDA PLANTS Database**: Via `usda_symbol`
- **EPPO Database**: Via `eppo` code
- **WIR (Weed Image Repository) System**: 
  - Master metadata (`wirmastermeta_rowkey`)
  - Cover crops metadata (`wircovercropsmeta_rowkey`)
  - Crops metadata (`wircropsmeta_rowkey`)
  - Image references (`wirimagerefs_rowkey`)
  - Weeds metadata (`wirweedsmeta_rowkey`)

---

## Quality Control Workflow

The database supports a comprehensive quality control pipeline:

1. **Initial Processing**: `is_preprocessed` flag and `processing_note`
2. **Initial Mask Review**: `initial_mask_issue_tag` and `mask_reviewer`
3. **Mask Refinement**: `refine_params` for adjustment tracking
4. **Final Review**: `final_mask_issue_tag` and `mask_status`
5. **Approval**: `final_mask_path` and `final_cutout_path` generation

---

## Data Quality Indicators

- **det_pred_conf**: Detection confidence for filtering low-quality predictions
- **has_mat_pred_conf**: Material prediction confidence
- **mask_status**: Current state in review workflow
- **has_matching_jpg_and_raw**: Validates paired image formats
- **size_mib**: File size tracking for quality assessment
- **mask_reviewer**: Traceability of review process

---

## Agricultural Context Fields

This database excels at capturing field-level context that is minimal or absent in other plant databases:

- Crop type and variety tracking (cotton_variety, crop_type_secondary)
- Cover crop family information
- Field status (crop_or_fallow)
- Environmental conditions (cloud_cover, ground_cover, ground_residue)
- Geographic location (us_state)