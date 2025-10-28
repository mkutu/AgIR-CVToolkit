---
layout: default
title: Home
nav_order: 1
description: "Agricultural Image Repository - Comprehensive field-level plant dataset"
permalink: /
---

<div class="hero-section" markdown="1">

# Agricultural Image Repository
{: .fs-9 .fw-700 }

Comprehensive field-level plant image dataset with precise segmentation masks, detailed taxonomic annotations, and agricultural context for computer vision research.
{: .fs-6 .fw-300 }

</div>

---

## Dataset at a Glance

<div class="stats-grid" markdown="1">

<div class="stat-card">
<span class="stat-number">50,000+</span>
<span class="stat-label">Plant Images</span>
</div>

<div class="stat-card">
<span class="stat-number">150+</span>
<span class="stat-label">Species</span>
</div>

<div class="stat-card">
<span class="stat-number">5</span>
<span class="stat-label">US States</span>
</div>

<div class="stat-card">
<span class="stat-number">98%</span>
<span class="stat-label">Human Verified</span>
</div>

</div>

---

## Two Complementary Databases

<div class="db-card" markdown="1">

### SEMIF - Semi-Automated Field Database
**Optimized for machine learning training**

- 62 attributes per record
- Precise bounding boxes and cutouts  
- Quality metrics (blur, area, components)
- Perfect for object detection & segmentation

[Explore SEMIF →](dataset/semif.html){: .btn .btn-primary }

</div>

<div class="db-card" markdown="1">

### FIELD - Field Observation Database
**Rich agricultural context**

- 72 attributes per record
- Crop types, phenology, field conditions
- Multi-stage quality control workflow
- Ideal for agricultural research

[Explore FIELD →](dataset/field.html){: .btn .btn-blue }

</div>

<!-- ---

## Key Features

<div class="feature-grid" markdown="1">

<div class="feature-card" markdown="1">
<div class="feature-icon">🎯</div>

### Precise Annotations
Pixel-perfect segmentation masks through multi-stage human verification
</div>

<div class="feature-card" markdown="1">
<div class="feature-icon">🌱</div>

### Rich Taxonomy
Complete classification with USDA/EPPO codes, common names, and growth characteristics
</div>

<div class="feature-card" markdown="1">
<div class="feature-icon">📊</div>

### Quality Metrics
Built-in blur detection, area measurements, confidence scores
</div>

<div class="feature-card" markdown="1">
<div class="feature-icon">🚜</div>

### Agricultural Context
Field conditions, crop types, phenology, environmental data
</div>

<div class="feature-card" markdown="1">
<div class="feature-icon">🗺️</div>

### Spatial Coverage
Multi-state collection with GPS coordinates
</div>

<div class="feature-card" markdown="1">
<div class="feature-icon">🔄</div>

### Temporal Data
Complete timestamps for temporal and phenological analysis
</div>

</div>

--- -->

<!-- ## Quick Access

Access the dataset using the AgIR-CVToolkit:
```bash
# Install the query toolkit
pip install agir-cvtoolkit

# Query SEMIF database
agir-cvtoolkit query --db semif \
  --filters "state=NC,category_common_name=barley" \
  --sample "stratified:by=area_bin,per_group=50"
```

[Full Query Guide →](access/query-guide.html){: .btn }

---

## Citation

{: .important }
If you use this dataset in your research, please cite our work.
```bibtex
@dataset{agir2025,
  title={Agricultural Image Repository: A Comprehensive Field-Level Plant Dataset},
  author={Your Name and Contributors},
  year={2025},
  publisher={Your Institution},
  url={https://github.com/yourusername/AgIR-CVToolkit}
}
``` -->

<!-- [More citation formats →](citation/how-to-cite.html) -->