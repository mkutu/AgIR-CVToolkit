---
layout: default
title: SEMIF Database
parent: Dataset
nav_order: 1
---

# SEMIF Database
{: .no_toc }

Semi-Automated Field Database - Optimized for machine learning training with precise bounding boxes and segmentation masks.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

<div class="db-card" markdown="1">

**Database Name:** SEMIF (Semi-Automated Field Database)

**Purpose:** Stores processed image cutouts/crops of individual plants with detailed bounding box annotations, taxonomy, and image characteristics. Optimized for machine learning training and object detection applications.

</div>

<div class="stats-grid" markdown="1">

<div class="stat-card">
<span class="stat-number">62</span>
<span class="stat-label">Attributes</span>
</div>

<div class="stat-card">
<span class="stat-number">50K+</span>
<span class="stat-label">Cutouts</span>
</div>

<div class="stat-card">
<span class="stat-number">150+</span>
<span class="stat-label">Species</span>
</div>

<div class="stat-card">
<span class="stat-number">98%</span>
<span class="stat-label">Quality</span>
</div>

</div>

---

<!-- ## Primary Use Cases

<div class="feature-grid" markdown="1">
 -->
<!-- <div class="feature-card" markdown="1"> -->
<!-- <div class="feature-icon">🤖</div> -->

<!-- **Machine Learning Training**  
Cutout images with precise bounding boxes for object detection models
</div> -->

<!-- <div class="feature-card" markdown="1"> -->
<!-- <div class="feature-icon">📊</div> -->

<!-- **Image Quality Analysis**  
Detailed metrics on blur, color characteristics, and component analysis
</div> -->

<!-- <div class="feature-card" markdown="1"> -->
<!-- <div class="feature-icon">🔍</div> -->

<!-- **Spatial Relationship Tracking**  
Overlap detection and management between multiple annotations
</div> -->

<!-- <div class="feature-card" markdown="1"> -->
<!-- <div class="feature-icon">🌿</div> -->

<!-- **Species-Level Identification**  
Taxonomic classification from cropped plant images
</div> -->

<!-- <div class="feature-card" markdown="1"> -->
<!-- <div class="feature-icon">🎯</div> -->

<!-- **Non-Target Weed Detection**  
Specialized classification with confidence scoring
</div> -->

<!-- <div class="feature-card" markdown="1"> -->
<!-- <div class="feature-icon">📐</div> -->

<!-- **Area Estimation**  
Multiple area metrics with categorical binning
</div> -->

<!-- </div> -->

---

## Key Features

{: .note }
> **What Makes SEMIF Special**: Comprehensive bounding box management, quality metrics, dual path storage, version control, and multiple area estimation methods.

- **Bounding Box Management**: Comprehensive coordinate tracking and overlap detection
- **Quality Metrics**: Blur detection, component counting, and RGB statistics  
- **Dual Path Storage**: Both `cropout_path` and `cutout_path` for redundancy
- **Version Control**: Tracked through `bbot_version`, `version`, and `batch_id` fields
- **Area Estimation**: Multiple area metrics (pixel, measured cm², estimated cm²) with binning

---

## Schema Documentation

### 1. Temporal & Batch Information

Track when and how data was processed.

| Field | Type | Description |
|:------|:-----|:------------|
| `season` | String | Growing season identifier |
| `datetime` | String | Timestamp of image capture |
| `bbot_version` | String | Version of the bounding box annotation tool used |
| `batch_id` | String | Identifier for the processing batch |
| `version` | Float | Dataset or annotation version number |

---

### 2. Image Metadata

Original source image information and camera settings.

| Field | Type | Description |
|:------|:-----|:------------|
| `image_id` | String | Unique identifier for the source image |
| `fullres_height` | Integer | Height of the full-resolution source image in pixels |
| `fullres_width` | Integer | Width of the full-resolution source image in pixels |
| `exif_meta` | String | EXIF metadata from the original image |
| `camera_info` | String | Camera model and settings information |
| `lens_model` | String | Camera lens model used for capture |

---

### 3. File Paths & Storage

Locations of images, masks, and metadata files.

| Field | Type | Description |
|:------|:-----|:------------|
| `ncsu_nfs` | String | NCSU network file system location |
| `image_path` | String | Path to the full source image |
| `mask_path` | String | Path to the segmentation mask file |
| `json_path` | String | Path to associated JSON metadata |
| `cutout_ncsu_nfs` | String | NCSU NFS location for cutout images |
| `cropout_path` | String | Path to the cropped/cutout image |
| `cutout_path` | String | Alternate path to cutout image |
| `cutout_mask_path` | String | Path to the cutout's segmentation mask |
| `cutout_json_path` | String | Path to cutout's JSON metadata |

{: .tip }
> **Storage Redundancy**: Both `cropout_path` and `cutout_path` are provided for system reliability.

---

### 4. Annotation & Detection

Bounding boxes, masks, and detection metadata.

| Field | Type | Description |
|:------|:-----|:------------|
| `has_masks` | Integer | Boolean flag indicating presence of segmentation masks (0/1) |
| `is_primary` | Integer | Boolean flag marking primary annotation in overlapping cases |
| `cutout_exists` | Float | Boolean flag indicating if cutout file exists |
| `cutout_id` | String | Unique identifier for this cutout |
| `bbox_xywh` | String | Bounding box coordinates in [x, y, width, height] format |
| `category_class_id` | Integer | Numeric class identifier for the category |
| `overlapping_cutout_ids` | String | IDs of other cutouts that overlap with this one |

**Example `bbox_xywh` format:**
```python
[245, 180, 120, 95] # [x_top_left, y_top_left, width, height]
```

---

### 5. Weed Classification

Non-target weed detection and confidence scoring.

| Field | Type | Description |
|:------|:-----|:------------|
| `non_target_weed` | Float | Boolean flag indicating if this is a non-target weed species |
| `non_target_weed_pred_conf` | Float | Confidence score for non-target weed prediction (0-1) |

{: .important }
> **Quality Filtering**: Use `non_target_weed_pred_conf` to filter predictions by confidence threshold.

---

### 6. Spatial Information

Geographic location and area measurements.

| Field | Type | Description |
|:------|:-----|:------------|
| `local_coordinates` | String | Coordinates within the image frame |
| `global_coordinates` | String | GPS or field-level coordinates |
| `pixel_area` | Float | Area in pixels |
| `bbox_area_cm2` | Float | Measured bounding box area in square centimeters |
| `estimated_bbox_area_cm2` | Float | Estimated bounding box area in square centimeters |
| `estimated_area_bin` | String | Categorical size bin for the estimated area |
| `state` | String | US state where image was captured |

**Area bins** typically include: `small`, `medium`, `large`, `extra_large`

---

### 7. Taxonomic Classification

Complete taxonomic hierarchy from kingdom to species.

| Field | Type | Description |
|:------|:-----|:------------|
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

**Example taxonomy:**
```
Common Name: Barley
USDA Symbol: HOVU
Family: Poaceae
Genus: Hordeum
Species: vulgare
```

---

### 8. Plant Characteristics

Growth and life cycle information.

| Field | Type | Description |
|:------|:-----|:------------|
| `category_growth_habit` | String | Growth habit (e.g., forb, grass, shrub, vine) |
| `category_duration` | String | Life cycle duration (annual, biennial, perennial) |

**Growth habits:**
- `forb` - Herbaceous flowering plant
- `grass` - Graminoid
- `shrub` - Woody plant
- `vine` - Climbing/trailing plant

---

### 9. Reference & Visualization

Links to external databases and display properties.

| Field | Type | Description |
|:------|:-----|:------------|
| `category_usda_link` | String | URL to USDA PLANTS database entry |
| `category_taxonomic_notes` | String | Additional taxonomic notes or clarifications |
| `category_hex` | String | Hexadecimal color code for visualization |
| `category_rgb` | String | RGB color values for visualization |
| `category_alias` | String | Alternative or simplified category name |

**Example color values:**
```
Hex: #4CAF50
RGB: (76, 175, 80)
```

---

### 10. Cutout Image Characteristics

Technical properties of the cropped image.

| Field | Type | Description |
|:------|:-----|:------------|
| `cutout_height` | Float | Height of the cutout image in pixels |
| `cutout_width` | Float | Width of the cutout image in pixels |
| `blur_effect` | Float | Quantitative measure of image blur |
| `num_components` | Float | Number of connected components in the segmentation |
| `cropout_rgb_mean` | String | Mean RGB values of the cutout image |
| `cropout_rgb_std` | String | Standard deviation of RGB values |
| `extends_border` | Float | Boolean flag indicating if cutout extends to image border |

{: .tip }
> **Quality Filtering**: Use `blur_effect < 50` for high-quality images. Filter by `num_components` to find clean single-plant images.

**Example quality thresholds:**
```python
# High quality images
blur_effect < 50

# Single plant detection
num_components <= 2

# Not extending to border
extends_border == 0
```

---

## External Integrations

<div class="feature-grid" markdown="1">

<div class="feature-card" markdown="1">

**USDA PLANTS Database**  
Access via `category_usda_symbol` and `category_usda_link`

[Visit USDA PLANTS →](https://plants.usda.gov/)
</div>

<div class="feature-card" markdown="1">

**EPPO Database**  
Access via `category_eppo_code`

[Visit EPPO →](https://www.eppo.int/)
</div>

<div class="feature-card" markdown="1">

**NCSU Network File System**  
Primary storage infrastructure

Fields: `ncsu_nfs`, `cutout_ncsu_nfs`
</div>

</div>

---

## Data Quality Indicators

Use these fields to filter for high-quality data:

| Indicator | Field | Recommended Value |
|:----------|:------|:------------------|
| **Mask Availability** | `has_masks` | `1` (masks exist) |
| **File Existence** | `cutout_exists` | `1` (file exists) |
| **Primary Annotation** | `is_primary` | `1` (primary in overlaps) |
| **Weed Confidence** | `non_target_weed_pred_conf` | `> 0.8` (high confidence) |
| **Image Quality** | `blur_effect` | `< 50` (sharp images) |

---

## Accessing the Data

{: .note }
> **Query this database** using the AgIR-CVToolkit. The toolkit provides powerful filtering, sampling, and export capabilities.

[Learn How to Query SEMIF →](https://github.com/yourusername/AgIR-CVToolkit/blob/main/docs/PIPELINE_STAGES/01_query/db_query_usage.md){: .btn .btn-primary }
[View Complete Query Guide →](../access/query-guide.html){: .btn .btn-primary }

---

## Version History

The SEMIF database includes version tracking:

- **`bbot_version`**: Annotation tool version
- **`version`**: Dataset version number  
- **`batch_id`**: Processing batch identifier

This enables reproducibility and tracking of data processing changes over time.

---

## Next Steps

<div class="feature-grid" markdown="1">

<div class="feature-card" markdown="1">

**📊 View Statistics**  
Explore species distribution and data characteristics

[Statistics →](../statistics/overview.html)
</div>

<div class="feature-card" markdown="1">

**🖼️ See Examples**  
Browse sample images and annotations

[Gallery →](../examples/gallery.html)
</div>

<div class="feature-card" markdown="1">

**🔧 Access the Data**  
Learn how to query with AgIR-CVToolkit

[Query Documentation →](https://github.com/yourusername/AgIR-CVToolkit/blob/main/docs/PIPELINE_STAGES/01_query/)
</div>

<div class="feature-card" markdown="1">

**📚 Compare with FIELD**  
See the Field observation database

[FIELD Database →](field.html)
</div>

</div>