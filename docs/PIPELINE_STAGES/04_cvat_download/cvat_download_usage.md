# CVAT Download Stage Usage Guide

## Overview

The CVAT download stage allows you to download annotations and masks from CVAT with flexible filtering options. It integrates seamlessly with your existing pipeline architecture.

## Features

- **Status Filtering**: Only download tasks with specific status (e.g., "completed")
- **Task ID Filtering**: Download specific tasks by their IDs
- **Image Validation**: Only download masks for images that still exist in CVAT
- **Format Support**: Multiple export formats (COCO, YOLO, Segmentation mask, etc.)
- **Smart Caching**: Skip already-downloaded tasks unless overwrite is enabled

## Installation

The stage requires the CVAT SDK:

```bash
pip install cvat-sdk
```

## Configuration

### File Structure

Create a configuration file at `conf/cvat_download/default.yaml`:

```yaml
cvat_download:
  organization_slug: null
  project_id: null
  task_ids: null
  required_status: "completed"
  check_image_exists: true
  dataset_format: "COCO 1.0"
  include_images: false
  overwrite_existing: false
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `organization_slug` | str | null | CVAT organization (null for personal workspace) |
| `project_id` | int | null | Filter by project ID (null = all projects) |
| `task_ids` | list[int] | null | Specific task IDs to download (null = all tasks) |
| `required_status` | str | "completed" | Filter by task status (null = no filter) |
| `check_image_exists` | bool | true | Validate images exist before downloading |
| `dataset_format` | str | "COCO 1.0" | Export format |
| `include_images` | bool | false | Download images along with annotations |
| `overwrite_existing` | bool | false | Re-download even if already exists |

### Supported Formats

- `"CamVid 1.0"` - PNG segmentation masks
- `"Segmentation mask 1.1"` - PNG segmentation masks
- `"Ultralytics YOLO Segmentation 1.0"`
- `"Ultralytics YOLO Detection 1.0"`
- `"COCO 1.0"`
- `"YOLO 1.1"` - YOLO format
- `"PASCAL VOC 1.1"` - Pascal VOC format
- `"Datumaro 1.0"` - Datumaro format


### Task Statuses

- `"annotation"` - Task is being annotated
- `"validation"` - Task is in validation
- `"acceptance"` - Task is in acceptance
- `"completed"` - Task is completed

## Usage Examples

### Basic Usage

Download all completed tasks:

```bash
agir-cvtoolkit download-cvat
```

### Filter by Task IDs

Download specific tasks:

```bash
agir-cvtoolkit download-cvat -o cvat_download.task_ids=[101,102,103]
```

### Filter by Project

Download all tasks from a specific project:

```bash
agir-cvtoolkit download-cvat -o cvat_download.project_id=5
```

Download only completed tasks from a project:

```bash
agir-cvtoolkit download-cvat \
    -o cvat_download.project_id=5 \
    -o cvat_download.required_status=completed
```

Download all tasks from a project (any status):

```bash
agir-cvtoolkit download-cvat \
    -o cvat_download.project_id=5 \
    -o cvat_download.required_status=null
```

### Filter by Status

Download all annotation tasks (not yet completed):

```bash
agir-cvtoolkit download-cvat -o cvat_download.required_status=annotation
```

Download all tasks regardless of status:

```bash
agir-cvtoolkit download-cvat -o cvat_download.required_status=null
```

### Download Options

Include images along with annotations:

```bash
agir-cvtoolkit download-cvat -o cvat_download.include_images=true
```

Use YOLO format instead of COCO:

```bash
agir-cvtoolkit download-cvat -o cvat_download.dataset_format="YOLO 1.1"
```

Force re-download even if already exists:

```bash
agir-cvtoolkit download-cvat -o cvat_download.overwrite_existing=true
```

### Skip Image Validation

If you want to speed up downloads and trust that all images exist:

```bash
agir-cvtoolkit download-cvat -o cvat_download.check_image_exists=false
```

### Organization Workspace

Download from a specific organization:

```bash
agir-cvtoolkit download-cvat -o cvat_download.organization_slug=my-team
```

### Combined Options

Download specific completed tasks with images:

```bash
agir-cvtoolkit download-cvat \
    -o cvat_download.task_ids=[101,102,103] \
    -o cvat_download.required_status=completed \
    -o cvat_download.include_images=true
```

Download all completed tasks from a project with images:

```bash
agir-cvtoolkit download-cvat \
    -o cvat_download.project_id=5 \
    -o cvat_download.required_status=completed \
    -o cvat_download.include_images=true \
    -o cvat_download.dataset_format="COCO 1.0"
```

## Output Structure

Downloaded tasks are saved using their task names (sanitized for filesystem):

```
outputs/{run_id}/cvat_downloads/
├── barley_segmentation/
│   ├── annotations/
│   │   └── instances_default.json
│   └── images/  (if include_images=true)
├── wheat_annotation_batch_1/
│   └── annotations/
└── hairy_vetch_crops/
    └── annotations/
```

Task names are sanitized:
- Converted to lowercase
- Spaces replaced with underscores
- Special characters removed or replaced
- Limited to 200 characters

**Note**: If multiple tasks have the same name (after sanitization), they will use the same directory. The stage will skip re-downloading if `overwrite_existing: false` (default).

## Metrics

The stage tracks and saves metrics to `metrics.json`:

```json
{
  "total_tasks_found": 10,
  "tasks_downloaded": 8,
  "tasks_skipped": 1,
  "tasks_failed": 1,
  "images_filtered": 5,
  "project_id": 5,
  "task_ids_filter": null,
  "status_filter": "completed",
  "task_details": [
    {
      "task_id": 101,
      "task_name": "Barley Segmentation",
      "directory_name": "barley_segmentation",
      "status": "completed",
      "size": 150,
      "output_dir": "outputs/proj/cvat_downloads/barley_segmentation",
      "images_filtered": 2,
      "success": true
    }
  ]
}
```

## Logging

The stage provides detailed logging:

```
================================================================================
Starting CVAT Download Pipeline
================================================================================
Connecting to CVAT at https://app.cvat.ai...
Using organization: my-team
Project: Barley Annotation Project (ID: 5)
Project labels: ['barley', 'wheat', 'hairy_vetch']
Project has 12 total tasks
Successfully connected to CVAT
Dataset format: COCO 1.0
Include images: false
Check image exists: true
Project ID filter: 5
Required status: completed

Fetching all tasks from CVAT...
Found 12 total tasks
Filtering tasks by project_id: 5
Filtered out 4 tasks not in project 5
Filtering tasks with status: 'completed'
Filtered out 0 tasks not matching status
Will process 8 tasks
Downloads will be saved to: outputs/proj/cvat_downloads

Downloading tasks: 100%|████████████████████| 8/8 [00:45<00:00, 5.64s/it]

Processing task 101: Barley Segmentation
Downloading task 101: 'Barley Segmentation' (status: completed, size: 150)
Exporting dataset in format: COCO 1.0
Extracting dataset to outputs/proj/cvat_downloads/barley_segmentation
Successfully downloaded task 'Barley Segmentation' (ID: 101)
Filtered annotations: removed 2 deleted images and 5 annotations

================================================================================
CVAT Download Complete
================================================================================
Total tasks found: 12
Tasks downloaded: 8
Tasks skipped: 0
Tasks failed: 0
Images filtered: 2
Output directory: outputs/proj/cvat_downloads
Metrics saved to: outputs/proj/metrics.json
================================================================================
```

## Integration with Pipeline

### Sequential Pipeline

Download from CVAT, then process locally:

```bash
# 1. Download annotations from CVAT
agir-cvtoolkit download-cvat \
    -o cvat_download.required_status=completed

# 2. Use downloaded data for training
python train.py --data outputs/proj/cvat_downloads/task_101
```

### Programmatic Usage

```python
from omegaconf import DictConfig
from agir_cvtoolkit.pipelines.stages.cvat_download import CVATDownloadStage
from agir_cvtoolkit.pipelines.utils.hydra_utils import finalize_cfg

# Create config
cfg = DictConfig({
    "cvat_download": {
        "project_id": 5,  # Download all tasks from project 5
        "required_status": "completed",
        "check_image_exists": True,
        "dataset_format": "COCO 1.0",
    },
    "io": {
        "keys_file": "keys.yaml",
    },
    # ... other config
})

# Finalize config
cfg = finalize_cfg(cfg, stage="download_cvat", dataset="cvat", cli_overrides=[])

# Run stage
stage = CVATDownloadStage(cfg)
stage.run()

# Access metrics
print(f"Downloaded {stage.metrics['tasks_downloaded']} tasks from project {stage.metrics['project_id']}")
```

## Credentials

Credentials are read from your `keys.yaml` file:

```yaml
cvat:
  url: "https://app.cvat.ai"
  username: "your_username"
  password: "your_password"
```

For self-hosted CVAT:

```yaml
cvat:
  url: "http://localhost:8080"
  username: "admin"
  password: "admin123"
```

## Troubleshooting

### Authentication Errors

If you get authentication errors:
1. Check your credentials in `keys.yaml`
2. Verify the CVAT URL is correct
3. Test login in the CVAT web interface

### Task Not Found

If specific task IDs fail:
1. Verify the task IDs exist in CVAT
2. Check if you have permission to access them
3. Ensure you're using the correct organization slug

### Format Errors

If export format fails:
1. Check the format name spelling (case-sensitive)
2. Verify the format is available in your CVAT version
3. Try a different format like "COCO 1.0"

### Slow Downloads

To speed up downloads:
1. Set `check_image_exists: false` to skip validation
2. Set `include_images: false` if you don't need images
3. Use task ID filtering to download fewer tasks

## Best Practices

1. **Use Project Filtering**: Use `project_id` to organize downloads by project and avoid mixing data
2. **Use Status Filtering**: Always filter by status to avoid downloading incomplete tasks
3. **Enable Image Validation**: Keep `check_image_exists: true` to avoid issues with deleted images
4. **Cache Downloads**: Leave `overwrite_existing: false` to avoid re-downloading
5. **Monitor Metrics**: Check `metrics.json` to track download success rates
6. **Backup First**: Download to a test directory first before overwriting production data