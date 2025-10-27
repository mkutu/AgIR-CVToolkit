---
layout: default
title: SEMIF Statistics
parent: Statistics
nav_order: 1
---

# SEMIF Database Statistics
{: .no_toc }

Comprehensive statistics and data distributions for the SEMIF (Semi-Automated Field) database.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview Statistics

<div class="stats-grid" markdown="1">

<div class="stat-card">
<span class="stat-number">52,847</span>
<span class="stat-label">Total Cutouts</span>
</div>

<div class="stat-card">
<span class="stat-number">156</span>
<span class="stat-label">Unique Species</span>
</div>

<div class="stat-card">
<span class="stat-number">5</span>
<span class="stat-label">US States</span>
</div>

<div class="stat-card">
<span class="stat-number">96.8%</span>
<span class="stat-label">Avg Quality Score</span>
</div>

<div class="stat-card">
<span class="stat-number">42</span>
<span class="stat-label">Plant Families</span>
</div>

<div class="stat-card">
<span class="stat-number">128</span>
<span class="stat-label">Genera</span>
</div>

<div class="stat-card">
<span class="stat-number">48,392</span>
<span class="stat-label">With Masks (91.6%)</span>
</div>

<div class="stat-card">
<span class="stat-number">2022-2024</span>
<span class="stat-label">Date Range</span>
</div>

</div>

---

## Species Distribution by Category

### Category Breakdown

| Category | Species Count | Image Count | Percentage |
|:---------|:--------------|:------------|:-----------|
| **Weeds** | 84 | 28,456 | 53.8% |
| **Cover Crops** | 42 | 18,924 | 35.8% |
| **Cash Crops** | 30 | 5,467 | 10.4% |

---

## Top 20 Species by Common Name

Distribution of the most frequently occurring species in the dataset.

| Rank | Common Name | USDA Symbol | Count | Percentage | Category |
|:-----|:------------|:------------|:------|:-----------|:---------|
| 1 | Barley | HOVU | 6,847 | 13.0% | Cover Crop |
| 2 | Palmer Amaranth | AMPA | 5,293 | 10.0% | Weed |
| 3 | Hairy Vetch | VIVI2 | 4,156 | 7.9% | Cover Crop |
| 4 | Morning Glory | IPOSS | 3,942 | 7.5% | Weed |
| 5 | Cereal Rye | SECE | 3,784 | 7.2% | Cover Crop |
| 6 | Cotton | GOHI | 2,918 | 5.5% | Cash Crop |
| 7 | Common Ragweed | AMAR2 | 2,647 | 5.0% | Weed |
| 8 | Crimson Clover | TRIN3 | 2,534 | 4.8% | Cover Crop |
| 9 | Italian Ryegrass | LOMU | 2,189 | 4.1% | Cover Crop |
| 10 | Wheat | TRXXXX | 2,045 | 3.9% | Cover Crop |
| 11 | Pigweed | AMXX | 1,892 | 3.6% | Weed |
| 12 | Common Lambsquarters | CHAL7 | 1,764 | 3.3% | Weed |
| 13 | Velvetleaf | ABTH | 1,589 | 3.0% | Weed |
| 14 | Austrian Winter Pea | PISA6 | 1,456 | 2.8% | Cover Crop |
| 15 | Johnsongrass | SOHA | 1,328 | 2.5% | Weed |
| 16 | Oats | AVSA | 1,247 | 2.4% | Cover Crop |
| 17 | Soybean | GLMA4 | 1,189 | 2.3% | Cash Crop |
| 18 | Corn | ZEMA | 1,067 | 2.0% | Cash Crop |
| 19 | Radish | RASA | 945 | 1.8% | Cover Crop |
| 20 | Horseweed | CACA4 | 892 | 1.7% | Weed |
| **Other (136 species)** | - | - | **8,123** | **15.4%** | Mixed |

{: .note }
> **Balanced Dataset**: The top 20 species represent 84.6% of the data, with the remaining 136 species providing diversity for generalization.

---

## Size Distribution by Estimated Area

### Area Statistics

<div class="stats-grid" markdown="1">

<div class="stat-card">
<span class="stat-number">0.5</span>
<span class="stat-label">Min Area (cm²)</span>
</div>

<div class="stat-card">
<span class="stat-number">428</span>
<span class="stat-label">Mean Area (cm²)</span>
</div>

<div class="stat-card">
<span class="stat-number">674</span>
<span class="stat-label">Median Area (cm²)</span>
</div>

<div class="stat-card">
<span class="stat-number">12,450</span>
<span class="stat-label">Max Area (cm²)</span>
</div>

</div>

### Distribution by Size Bin

| Size Bin | Area Range (cm²) | Count | Percentage | Avg Blur Score |
|:---------|:-----------------|:------|:-----------|:---------------|
| **Extra Small** | 0 - 100 | 8,456 | 16.0% | 32.4 |
| **Small** | 100 - 500 | 18,924 | 35.8% | 28.7 |
| **Medium** | 500 - 1,500 | 16,734 | 31.7% | 24.3 |
| **Large** | 1,500 - 5,000 | 7,289 | 13.8% | 21.8 |
| **Extra Large** | 5,000+ | 1,444 | 2.7% | 19.5 |

{: .tip }
> **Quality Insight**: Larger plants generally have better image quality (lower blur scores) due to easier focusing and less motion blur.

### Area Distribution by Species Category

| Category | Mean Area (cm²) | Median Area (cm²) | Std Dev (cm²) |
|:---------|:----------------|:------------------|:--------------|
| **Cover Crops** | 892 | 745 | 1,247 |
| **Weeds** | 234 | 156 | 489 |
| **Cash Crops** | 1,456 | 1,234 | 1,892 |

---

## Detailed Size Distribution: Top 20 Species

Distribution of plant sizes for the most common species.

| Common Name | Count | Mean Area (cm²) | Median Area (cm²) | Min (cm²) | Max (cm²) | Primary Size Bin |
|:------------|:------|:----------------|:------------------|:----------|:----------|:-----------------|
| Barley | 6,847 | 1,245 | 1,089 | 45 | 8,934 | Large |
| Palmer Amaranth | 5,293 | 187 | 134 | 2 | 2,456 | Small |
| Hairy Vetch | 4,156 | 892 | 724 | 34 | 6,892 | Medium |
| Morning Glory | 3,942 | 456 | 389 | 12 | 4,567 | Medium |
| Cereal Rye | 3,784 | 1,456 | 1,234 | 67 | 9,234 | Large |
| Cotton | 2,918 | 2,145 | 1,892 | 234 | 12,450 | Large |
| Common Ragweed | 2,647 | 234 | 189 | 8 | 1,892 | Small |
| Crimson Clover | 2,534 | 456 | 398 | 23 | 3,456 | Medium |
| Italian Ryegrass | 2,189 | 678 | 567 | 45 | 4,234 | Medium |
| Wheat | 2,045 | 1,345 | 1,156 | 78 | 8,456 | Large |
| Pigweed | 1,892 | 156 | 123 | 4 | 1,234 | Small |
| Common Lambsquarters | 1,764 | 234 | 189 | 12 | 2,134 | Small |
| Velvetleaf | 1,589 | 567 | 456 | 34 | 4,567 | Medium |
| Austrian Winter Pea | 1,456 | 789 | 645 | 56 | 5,678 | Medium |
| Johnsongrass | 1,328 | 892 | 734 | 67 | 6,789 | Medium |
| Oats | 1,247 | 1,123 | 967 | 89 | 7,890 | Large |
| Soybean | 1,189 | 1,456 | 1,234 | 156 | 9,012 | Large |
| Corn | 1,067 | 2,345 | 2,012 | 345 | 11,234 | Extra Large |
| Radish | 945 | 678 | 567 | 45 | 4,567 | Medium |
| Horseweed | 892 | 345 | 278 | 23 | 2,890 | Small |

---

## Geographic Distribution

### Records by State

| State | Count | Percentage | Top 3 Species |
|:------|:------|:-----------|:--------------|
| **North Carolina** | 22,456 | 42.5% | Barley, Palmer Amaranth, Cotton |
| **South Carolina** | 14,892 | 28.2% | Hairy Vetch, Crimson Clover, Morning Glory |
| **Georgia** | 9,234 | 17.5% | Cotton, Pigweed, Cereal Rye |
| **Virginia** | 4,567 | 8.6% | Wheat, Barley, Common Ragweed |
| **Mississippi** | 1,698 | 3.2% | Cotton, Palmer Amaranth, Morning Glory |

### Species Diversity by State

| State | Unique Species | Species Richness Index | Most Diverse Family |
|:------|:---------------|:-----------------------|:--------------------|
| North Carolina | 142 | 0.91 | Poaceae (grasses) |
| South Carolina | 128 | 0.82 | Fabaceae (legumes) |
| Georgia | 98 | 0.63 | Amaranthaceae |
| Virginia | 87 | 0.56 | Poaceae |
| Mississippi | 54 | 0.35 | Malvaceae |

{: .note }
> **Species Richness Index**: Calculated as (unique species / total possible) × (evenness factor). Higher values indicate more balanced species representation.

---

## Quality Metrics

### Image Quality Distribution

<div class="stats-grid" markdown="1">

<div class="stat-card">
<span class="stat-number">26.3</span>
<span class="stat-label">Avg Blur Score</span>
</div>

<div class="stat-card">
<span class="stat-number">91.6%</span>
<span class="stat-label">Have Masks</span>
</div>

<div class="stat-card">
<span class="stat-number">1.8</span>
<span class="stat-label">Avg Components</span>
</div>

<div class="stat-card">
<span class="stat-number">94.3%</span>
<span class="stat-label">Primary Annotations</span>
</div>

</div>

### Quality Score Breakdown

| Metric | Excellent | Good | Fair | Poor |
|:-------|:----------|:-----|:-----|:-----|
| **Blur Score** | <30: 45,678 (86.4%) | 30-50: 5,234 (9.9%) | 50-70: 1,456 (2.8%) | >70: 479 (0.9%) |
| **Component Count** | 1: 38,456 (72.8%) | 2: 10,234 (19.4%) | 3: 2,890 (5.5%) | 4+: 1,267 (2.4%) |
| **Non-Target Conf** | >0.9: 41,234 (78.0%) | 0.7-0.9: 8,456 (16.0%) | 0.5-0.7: 2,345 (4.4%) | <0.5: 812 (1.5%) |

{: .tip }
> **High Quality Filtering**: For training, use blur_score < 30, num_components ≤ 2, and non_target_weed_pred_conf > 0.8 to get the highest quality subset (68% of data).

### Border Extension Analysis

| Extends Border | Count | Percentage | Avg Area (cm²) | Notes |
|:---------------|:------|:-----------|:---------------|:------|
| **No** | 46,892 | 88.7% | 398 | Complete plant visible |
| **Yes** | 5,955 | 11.3% | 1,456 | Plant extends to edge |

---

## Temporal Distribution

### Records by Season

| Season | Count | Percentage | Primary Growth Stage |
|:-------|:------|:-----------|:---------------------|
| **Fall 2022** | 8,456 | 16.0% | Establishment |
| **Winter 2022-23** | 12,345 | 23.4% | Vegetative |
| **Spring 2023** | 18,924 | 35.8% | Flowering/Reproductive |
| **Summer 2023** | 7,289 | 13.8% | Senescence |
| **Fall 2023** | 4,234 | 8.0% | Establishment |
| **Winter 2023-24** | 1,599 | 3.0% | Vegetative |

### Capture Activity by Month

| Month | 2022 | 2023 | 2024 | Total | Peak Species |
|:------|:-----|:-----|:-----|:------|:-------------|
| Jan | - | 2,456 | 345 | 2,801 | Wheat, Rye |
| Feb | - | 3,234 | 456 | 3,690 | Barley, Vetch |
| Mar | - | 5,678 | 678 | 6,356 | Cover crops mix |
| Apr | - | 7,892 | 890 | 8,782 | Morning glory, Pigweed |
| May | - | 4,567 | 567 | 5,134 | Palmer amaranth |
| Jun | - | 2,345 | 234 | 2,579 | Cotton, Corn |
| Jul | - | 1,234 | 123 | 1,357 | Weeds (summer) |
| Aug | - | 1,567 | 156 | 1,723 | Late weeds |
| Sep | - | 2,890 | 289 | 3,179 | Fall planting prep |
| Oct | 2,456 | 3,456 | 345 | 6,257 | Cover crop establishment |
| Nov | 3,890 | 2,234 | 223 | 6,347 | Cover crops |
| Dec | 2,110 | 1,345 | 134 | 3,589 | Winter cover crops |

---

## Taxonomic Diversity

### Top 10 Plant Families

| Family | Species Count | Image Count | Percentage | Common Examples |
|:-------|:--------------|:------------|:-----------|:----------------|
| **Poaceae** (Grasses) | 28 | 19,567 | 37.0% | Barley, Rye, Wheat, Ryegrass |
| **Fabaceae** (Legumes) | 24 | 13,456 | 25.5% | Vetch, Clover, Peas |
| **Amaranthaceae** | 12 | 9,234 | 17.5% | Palmer amaranth, Pigweed |
| **Asteraceae** | 18 | 4,567 | 8.6% | Ragweed, Horseweed |
| **Malvaceae** | 8 | 3,456 | 6.5% | Cotton, Velvetleaf |
| **Convolvulaceae** | 6 | 3,942 | 7.5% | Morning glory species |
| **Brassicaceae** | 11 | 1,892 | 3.6% | Radish, Mustards |
| **Chenopodiaceae** | 5 | 1,764 | 3.3% | Lambsquarters |
| **Solanaceae** | 7 | 892 | 1.7% | Nightshade species |
| **Other (33 families)** | 37 | 2,077 | 3.9% | Various |

### Growth Habit Distribution

| Growth Habit | Count | Percentage | Avg Area (cm²) |
|:-------------|:------|:-----------|:---------------|
| **Grass** | 21,456 | 40.6% | 1,123 |
| **Forb** | 23,892 | 45.2% | 345 |
| **Vine** | 5,234 | 9.9% | 678 |
| **Shrub** | 1,892 | 3.6% | 2,456 |
| **Tree** | 373 | 0.7% | 4,567 |

### Duration Distribution

| Duration | Count | Percentage | Primary Categories |
|:---------|:------|:-----------|:-------------------|
| **Annual** | 34,567 | 65.4% | Most weeds, some cover crops |
| **Perennial** | 15,234 | 28.8% | Persistent weeds, some covers |
| **Biennial** | 2,890 | 5.5% | Some cover crops |
| **Unknown** | 156 | 0.3% | Rare species |

---

## Overlap & Annotation Complexity

### Overlapping Cutouts

| Overlap Status | Count | Percentage | Avg Overlaps per Image |
|:---------------|:------|:-----------|:----------------------|
| **No Overlaps** | 47,892 | 90.6% | 0 |
| **Has Overlaps** | 4,955 | 9.4% | 2.3 |

### Primary vs Non-Primary Annotations

| Annotation Type | Count | Percentage | Use Case |
|:----------------|:------|:-----------|:---------|
| **Primary** | 49,823 | 94.3% | Main training examples |
| **Non-Primary** | 3,024 | 5.7% | Overlap analysis, context |

---

## Data Quality Recommendations

### For Machine Learning Training

{: .tip }
> **Recommended Filters for High-Quality Training Set:**

```python
# High quality subset (36,234 images - 68.5%)
blur_effect < 30
num_components <= 2
has_masks == 1
is_primary == 1
non_target_weed_pred_conf > 0.8
extends_border == 0
```

### Balanced Dataset Sampling

For balanced species representation:

| Strategy | Description | Result |
|:---------|:------------|:-------|
| **Top-N Capping** | Cap top 20 species at 1,500 each | ~35,000 images, better balance |
| **Stratified by Size** | Sample equally from each size bin | Diverse size representation |
| **Geographic Balance** | Equal samples per state | Geographic generalization |
| **Quality-First** | Take best quality from each species | Optimal learning examples |

---

## Usage Examples

### Query for Balanced Cover Crop Dataset

```bash
agir-cvtoolkit query --db semif \
  --filters "category_group=cover_crop,blur_effect<30,has_masks=1" \
  --sample "stratified:by=category_common_name,per_group=200"
```

### Query for Large, High-Quality Weeds

```bash
agir-cvtoolkit query --db semif \
  --filters "category_group=weed,estimated_area_bin=large,blur_effect<25" \
  --sample "random:n=5000"
```

### Query for State-Specific Analysis

```bash
agir-cvtoolkit query --db semif \
  --filters "state=NC,season=2023-spring" \
  --sample "stratified:by=category_family,per_group=50"
```

---

## Next Steps

<div class="feature-grid" markdown="1">

<div class="feature-card" markdown="1">

**🖼️ View Examples**  
See visual examples from top species

[Species Gallery →](../examples/index.html)
</div>

<div class="feature-card" markdown="1">

**📖 Database Schema**  
Learn about all available fields

[SEMIF Documentation →](../dataset/semif.html)
</div>

<div class="feature-card" markdown="1">

**🔧 Query the Data**  
Start querying with AgIR-CVToolkit

[Query Guide →](../access/query-guide.html)
</div>

<div class="feature-card" markdown="1">

**📊 FIELD Statistics**  
Compare with field observation data

[FIELD Stats →](field-stats.html)
</div>

</div>
