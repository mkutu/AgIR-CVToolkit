# SEMIF Database Documentation

## Overview

**Database Name:** SEMIF (Semi-Automated Field Database)

**Purpose:** Stores processed image cutouts/crops of individual plants with detailed bounding box annotations, taxonomy, and image characteristics. Optimized for machine learning training and object detection applications.

**Record Count:** Variable (sample: 10 rows)  
**Column Count:** 62

---

## Schema Documentation

### 1. Temporal & Batch Information

| Field | Type | Description |
|-------|------|-------------|
| `season` | String | Growing season identifier |
| `datetime` | String | Timestamp of image capture |
| `bbot_version` | String | Version of the bounding box annotation tool used |
| `batch_id` | String | Identifier for the processing batch |
| `version` | Float | Dataset or annotation version number |

### 2. Image Metadata

| Field | Type | Description |
|-------|------|-------------|
| `image_id` | String | Unique identifier for the source image |
| `fullres_height` | Integer | Height of the full-resolution source image in pixels |
| `fullres_width` | Integer | Width of the full-resolution source image in pixels |
| `exif_meta` | String | EXIF metadata from the original image |
| `camera_info` | String | Camera model and settings information |
| `lens_model` | String | Camera lens model used for capture |

### 3. File Paths & Storage

| Field | Type | Description |
|-------|------|-------------|
| `ncsu_nfs` | String | NCSU network file system location |
| `image_path` | String | Path to the full source image |
| `mask_path` | String | Path to the segmentation mask file |
| `json_path` | String | Path to associated JSON metadata |
| `cutout_ncsu_nfs` | String | NCSU NFS location for cutout images |
| `cropout_path` | String | Path to the cropped/cutout image |
| `cutout_path` | String | Alternate path to cutout image |
| `cutout_mask_path` | String | Path to the cutout's segmentation mask |
| `cutout_json_path` | String | Path to cutout's JSON metadata |

### 4. Annotation & Detection

| Field | Type | Description |
|-------|------|-------------|
| `has_masks` | Integer | Boolean flag indicating presence of segmentation masks (0/1) |
| `is_primary` | Integer | Boolean flag marking primary annotation in overlapping cases |
| `cutout_exists` | Float | Boolean flag indicating if cutout file exists |
| `cutout_id` | String | Unique identifier for this cutout |
| `bbox_xywh` | String | Bounding box coordinates in [x, y, width, height] format |
| `category_class_id` | Integer | Numeric class identifier for the category |
| `overlapping_cutout_ids` | String | IDs of other cutouts that overlap with this one |

### 5. Weed Classification

| Field | Type | Description |
|-------|------|-------------|
| `non_target_weed` | Float | Boolean flag indicating if this is a non-target weed species |
| `non_target_weed_pred_conf` | Float | Confidence score for non-target weed prediction (0-1) |

### 6. Spatial Information

| Field | Type | Description |
|-------|------|-------------|
| `local_coordinates` | String | Coordinates within the image frame |
| `global_coordinates` | String | GPS or field-level coordinates |
| `pixel_area` | Float | Area in pixels |
| `bbox_area_cm2` | Float | Measured bounding box area in square centimeters |
| `estimated_bbox_area_cm2` | Float | Estimated bounding box area in square centimeters |
| `estimated_area_bin` | String | Categorical size bin for the estimated area |
| `state` | String | US state where image was captured |

### 7. Taxonomic Classification

| Field | Type | Description |
|-------|------|-------------|
| `category_usda_symbol` | String | USDA PLANTS database symbol code |
| `category_eppo_code` | String | European and Mediterranean Plant Protection Organization code |
| `category_group` | String | High-level taxonomic or functional group |
| `category_class` | String | Taxonomic class |
| `category_subclass` | String | Taxonomic subclass |
| `category_order` | String | Taxonomic order |
| `category_family` | String | Taxonomic family |
| `category_genus` | String | Taxonomic genus |
| `category_species` | String | Taxonomic species name |
| `category_common_name` | String | Common name of the plant |
| `category_authority` | String | Taxonomic authority citation |
| `category_multispecies` | String | Flag or notes for multi-species annotations |

### 8. Plant Characteristics

| Field | Type | Description |
|-------|------|-------------|
| `category_growth_habit` | String | Growth habit (e.g., forb, grass, shrub, vine) |
| `category_duration` | String | Life cycle duration (annual, biennial, perennial) |

### 9. Reference & Visualization

| Field | Type | Description |
|-------|------|-------------|
| `category_usda_link` | String | URL to USDA PLANTS database entry |
| `category_taxonomic_notes` | String | Additional taxonomic notes or clarifications |
| `category_hex` | String | Hexadecimal color code for visualization |
| `category_rgb` | String | RGB color values for visualization |
| `category_alias` | String | Alternative or simplified category name |

### 10. Cutout Image Characteristics

| Field | Type | Description |
|-------|------|-------------|
| `cutout_height` | Float | Height of the cutout image in pixels |
| `cutout_width` | Float | Width of the cutout image in pixels |
| `blur_effect` | Float | Quantitative measure of image blur |
| `num_components` | Float | Number of connected components in the segmentation |
| `cropout_rgb_mean` | String | Mean RGB values of the cutout image |
| `cropout_rgb_std` | String | Standard deviation of RGB values |
| `extends_border` | Float | Boolean flag indicating if cutout extends to image border |

---

## Primary Use Cases

- **Machine Learning Training**: Cutout images with precise bounding boxes for object detection models
- **Image Quality Analysis**: Detailed metrics on blur, color characteristics, and component analysis
- **Spatial Relationship Tracking**: Overlap detection and management between multiple annotations
- **Species-Level Identification**: Taxonomic classification from cropped plant images
- **Non-Target Weed Detection**: Specialized classification with confidence scoring

---

## Key Features

- **Bounding Box Management**: Comprehensive coordinate tracking and overlap detection
- **Quality Metrics**: Blur detection, component counting, and RGB statistics
- **Dual Path Storage**: Both cropout_path and cutout_path for redundancy
- **Version Control**: Tracked through bbot_version, version, and batch_id fields
- **Area Estimation**: Multiple area metrics (pixel, measured cm², estimated cm²) with binning

---

## External Integrations

- **USDA PLANTS Database**: Via `category_usda_symbol` and `category_usda_link`
- **EPPO Database**: Via `category_eppo_code`
- **NCSU Network File System**: Primary storage infrastructure

---

## Data Quality Indicators

- **has_masks**: Confirms segmentation mask availability
- **cutout_exists**: Validates cutout file presence
- **is_primary**: Resolves overlapping annotation priority
- **non_target_weed_pred_conf**: Prediction confidence for quality assessment
- **blur_effect**: Image quality metric for filtering low-quality samples