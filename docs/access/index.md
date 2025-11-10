---
layout: default
title: Access & Query
nav_order: 3
has_children: true
---

# Access the Dataset
{: .no_toc }

Multiple ways to query and access data from the AgIR dataset.
{: .fs-6 .fw-300 }

---

## Choose Your Access Method

### AgIR-CVToolkit (Recommended)

Python-based command-line tool for programmatic database access with filtering, sampling, and export capabilities.

**Best for:** Machine learning workflows, batch downloads, reproducible queries, CV pipelines

**Get Started:**
1. [Installation & Setup](installation.html) - Install the toolkit and configure databases
2. [Query Guide](query-tools.html) - Learn to filter, sample, and export data

### Direct Database Access

Download database files and query with standard SQLite tools or SQL clients.

**Best for:** Custom SQL queries, database exploration, advanced analytics

**Resources:**
- [SemiF Database Schema](../dataset/semif.html) - Field descriptions and structure
- [Field Database Schema](../dataset/field.html) - Field descriptions and structure

---

## Quick Examples

### AgIR-CVToolkit

```bash
# Get 100 barley images from North Carolina
agir-cv query --db semif \
  --filters "state=NC" \
  --filters "category_common_name=barley" \
  --limit 100

# Balanced dataset: 20 images per species
agir-cv query --db semif \
  --sample "stratified:by=category_common_name,per_group=20"
```

[See more examples →](query-tools.html)

### Direct SQL

```sql
-- Query SemiF database
SELECT cutout_id, category_common_name, state, estimated_bbox_area_cm2
FROM semif
WHERE state = 'NC' AND category_common_name = 'barley'
LIMIT 100;
```

---

## Documentation Map

| Documentation | Purpose |
|---------------|---------|
| [Installation & Setup](installation.html) | Install AgIR-CVToolkit and configure databases |
| [Query Guide](query-tools.html) | Filter, sample, and export data |
| [SemiF Schema](../dataset/semif.html) | Individual plant cutouts - 62 fields |
| [Field Schema](../dataset/field.html) | Field observations - 72 fields |
| [Full Toolkit Docs](https://github.com/your-org/AgIR-CVToolkit) | Complete pipeline (inference, annotation, training) |

---

## Need Help?

- **New Users**: Start with [Installation & Setup](installation.html)
- **Quick Start**: See [Query Guide examples](query-tools.html#common-query-patterns)
- **Schema Questions**: Check [SemiF](../dataset/semif.html) or [Field](../dataset/field.html) documentation
- **Issues**: [GitHub Issues](https://github.com/your-org/AgIR-CVToolkit/issues)
- **Support**: [support@example.com](mailto:support@example.com)