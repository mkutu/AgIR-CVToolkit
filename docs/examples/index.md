---
layout: default
title: Image Gallery
nav_order: 4
has_children: true
---

# Image Gallery & Examples
{: .no_toc }

Visual showcase of the AgIR dataset with example species across all plant categories.
{: .fs-6 .fw-300 }

---

## Data Products Overview

Each record in the AgIR dataset includes **four distinct data products** along with [DB metadata](../dataset/index.html) :

<div class="image-comparison-grid" markdown="0">
  <div class="image-panel">
    <div class="image-panel-label">1. Original Image</div>
    <div class="image-panel-content">
      <a href="../assets/images/examples/barley_original.jpg" class="glightbox" data-title="Barley - Original Field Image" data-description="Full resolution field capture. NC, Nov 2022. Image ID: NC_1668004918">
          <img src="../assets/images/examples/barley_original.jpg" alt="Barley original field image" style="width: 100%; height: 100%; object-fit: cover; cursor: pointer;">
        </a>
    </div>
  </div>
  
  <div class="image-panel">
    <div class="image-panel-label">2. Bounding Box Overlay</div>
    <div class="image-panel-content">
      <a href="../assets/images/examples/barley_bbox.jpg" class="glightbox" data-title="Barley - Bounding Box Overlay" data-description="Detection box overlay showing plant location. Area: 1,756 cm²">
          <img src="../assets/images/examples/barley_bbox.jpg" alt="Barley with bounding box overlay" style="width: 100%; height: 100%; object-fit: cover; cursor: pointer;">
        </a>
    </div>
  </div>
  
  <div class="image-panel">
    <div class="image-panel-label">3. Segmentation Mask</div>
    <div class="image-panel-content">
      <a href="../assets/images/examples/barley_mask.png" class="glightbox" data-title="Barley - Segmentation Mask" data-description="Binary pixel-level mask. Human-verified through QC workflow.">
          <img src="../assets/images/examples/barley_mask.png" alt="Barley segmentation mask" style="width: 100%; height: 100%; object-fit: cover; cursor: pointer;">
        </a>
    </div>
  </div>
  
  <div class="image-panel">
    <div class="image-panel-label">4. Plant Cutout</div>
    <div class="image-panel-content">
      <a href="../assets/images/examples/barley_cutout.png" class="glightbox" data-title="Barley - Plant Cutout" data-description="Isolated plant extracted from bounding box. Ready for ML training.">
          <img src="../assets/images/examples/barley_cutout.png" alt="Barley plant cutout" style="width: 100%; height: 100%; object-fit: cover; cursor: pointer;">
        </a>
    </div>
  </div>
</div>

---

## Browse by Plant Category

<div class="gallery-nav" markdown="0">
  <a href="cover-crops.html" class="gallery-nav-btn">
    <span class="gallery-nav-icon">🌱</span>
    <span class="gallery-nav-title">Cover Crops</span>
    <span class="gallery-nav-desc">Barley, winter pea, triticale</span>
  </a>
  
  <a href="weeds.html" class="gallery-nav-btn">
    <span class="gallery-nav-icon">🌿</span>
    <span class="gallery-nav-title">Weeds</span>
    <span class="gallery-nav-desc">Palmer amaranth, jimson weed</span>
  </a>
  
  <a href="cash-crops.html" class="gallery-nav-btn">
    <span class="gallery-nav-icon">🌾</span>
    <span class="gallery-nav-title">Cash Crops</span>
    <span class="gallery-nav-desc">Cotton, corn, soybeans</span>
  </a>
</div>

---

## What You'll Find

### For Each Species

Every species example includes:

**Four data products** - Original, bbox, mask, cutout  
**Taxonomic information** - Including scientific name, family, USDA codes  
**Size characteristics** - Area measurements and bins  

### Species Coverage

<div class="stats-grid" markdown="1">

<div class="stat-card">
<span class="stat-number">40+</span>
<span class="stat-label">Cover Crop Species</span>
</div>

<div class="stat-card">
<span class="stat-number">80+</span>
<span class="stat-label">Weed Species</span>
</div>

<div class="stat-card">
<span class="stat-number">30+</span>
<span class="stat-label">Cash Crop Varieties</span>
</div>

<div class="stat-card">
<span class="stat-number">150+</span>
<span class="stat-label">Total Species</span>
</div>

</div>

---

## Data Products Explained

### 1. Original Image
High-resolution field capture showing the plant in natural context.

- **Format**: JPG
- **Resolution**: 64 or 133 megapixels
- **Content**: Full field view with multiple plants

### 2. Bounding Box Overlay
Detection box drawn over the original image.

- **Format**: Coordinates [x, y, width, height]
- **Purpose**: Object detection training
- **Precision**: Tight fit around plant canopy
- **Overlaps**: Tracked via `overlapping_cutout_ids`

### 3. Segmentation Mask
Binary mask showing exact plant pixels.

- **Format**: PNG (binary or multi-class)
- **Precision**: Pixel-level accuracy
- **Use**: Semantic segmentation, instance segmentation

### 4. Plant Cutout
Cropped image of individual plant from bounding box.

- **Format**: PNG
- **Content**: Single plant, minimal background
- **Size**: Variable based on plant area
- **Use**: Synthetic image generation

---
<!-- 
## Example Use Cases

<div class="feature-grid" markdown="1">

<div class="feature-card" markdown="1">

**🤖 Train Detection Models**  
Use original images + bboxes for YOLO, Faster R-CNN, etc.

</div>

<div class="feature-card" markdown="1">

**🎯 Train Segmentation Models**  
Use images + masks for U-Net, DeepLab, Mask R-CNN

</div>

<div class="feature-card" markdown="1">

**🏷️ Train Classifiers**  
Use cutouts for species identification CNNs

</div>

<div class="feature-card" markdown="1">

**📊 Analyze Diversity**  
Use masks to measure plant size, shape, coverage

</div>

<div class="feature-card" markdown="1">

**🌱 Study Phenology**  
Track growth stages across multiple captures

</div>

<div class="feature-card" markdown="1">

**🗺️ Map Distributions**  
Geographic and temporal pattern analysis

</div>

</div>

--- -->

## Browse Examples

Select a category to view detailed species examples:

- **[Cover Crops →](cover-crops.html)** - Soil health, nitrogen fixation, erosion control
- **[Weeds →](weeds.html)** - Target species for detection and management
- **[Cash Crops →](cash-crops.html)** - Primary agricultural commodities

---
<!-- 
## Understanding the Data

{: .tip }
> **New to agricultural computer vision?** Check out our [Data Products Guide](data-products.html) for a detailed explanation of how each data type is generated and used.

[Learn About Data Products →](data-products.html){: .btn .btn-primary } -->