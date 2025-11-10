# Integration Guide: Adding Detection Inference to AgIR-CVToolkit

This guide shows you how to add the multiscale detection inference feature to your AgIR-CVToolkit.

## File Structure

After integration, your project should have these new/modified files:

```
agir-cvtoolkit/
├── src/agir_cvtoolkit/
│   ├── cli.py                          # MODIFIED: Add infer-det command
│   └── pipelines/
│       └── stages/
│           └── det_infer.py            # NEW: Detection inference stage
│
└── conf/
    └── det_inference/
        └── default.yaml                # NEW: Detection config
```

## Step-by-Step Integration

### Step 1: Add the Detection Inference Stage

Copy the `det_infer.py` file to your stages directory:

```bash
cp det_infer.py src/agir_cvtoolkit/pipelines/stages/
```

Or place the content in: `src/agir_cvtoolkit/pipelines/stages/det_infer.py`

### Step 2: Add the Configuration File

Create the configuration directory and file:

```bash
mkdir -p conf/det_inference
cp default_det_inference_config.yaml conf/det_inference/default.yaml
```

Or place the content in: `conf/det_inference/default.yaml`

### Step 3: Add the CLI Command

Open `src/agir_cvtoolkit/cli.py` and add this command function (place it after the other command definitions):

```python
@app.command("infer-det")
def infer_det(
    config: str = typer.Option("config", help="Hydra config name (without .yaml)"),
    override: List[str] = typer.Option(None, "--override", "-o", help="Hydra overrides"),
):
    """Run detection inference pipeline with multiscale processing."""
    cfg = _compose_cfg(config, override)
    cfg = finalize_cfg(
        cfg,
        stage="infer_det",
        dataset=cfg.get("det_inference", {}).get("source", {}).get("db", "semif"), 
        cli_overrides=override
    )

    setup_logging(cfg)
    from agir_cvtoolkit.pipelines.stages.det_infer import DetectionInferenceStage
    DetectionInferenceStage(cfg).run()
    
    typer.echo(
        f"Detection inference complete\n"
        f"run_id: {cfg['runtime']['run_id']}\n"
        f"run_root: {cfg['paths']['run_root']}"
    )
```

### Step 4: Verify Installation

Test that the command is available:

```bash
agir-cvtoolkit --help
```

You should see `infer-det` in the list of available commands.

### Step 5: Test the Feature

Run a simple test:

```bash
# Query some images
agir-cvtoolkit query --db semif --limit 5

# Run detection
agir-cvtoolkit infer-det \
  -o det_inference.model.weights=yolov8n.pt \
  -o det_inference.multiscale.scales=[1.0]
```

## Configuration Customization

### Creating Custom Configs

You can create custom detection configs for different scenarios:

```bash
# Create a config for small object detection
conf/det_inference/small_objects.yaml

# Create a config for large image processing
conf/det_inference/large_images.yaml

# Use custom config
agir-cvtoolkit infer-det --config det_inference/small_objects
```

### Example Custom Config

`conf/det_inference/small_objects.yaml`:

```yaml
# Optimized for small object detection
defaults:
  - default

det_inference:
  multiscale:
    scales: [1.0, 1.25, 1.5, 1.75, 2.0]
    base_imgsz: 1280
    per_scale_conf: 0.0005
  
  final_nms:
    conf: 0.2
    iou: 0.3
```

## Dependencies

Make sure you have these packages installed:

```bash
pip install ultralytics torch torchvision opencv-python omegaconf hydra-core
```

Or add to your `requirements.txt`:

```
ultralytics>=8.0.0
torch>=2.0.0
torchvision>=0.15.0
opencv-python>=4.8.0
omegaconf>=2.3.0
hydra-core>=1.3.0
```

## Testing

### Unit Test Template

Create `tests/test_det_infer.py`:

```python
import pytest
from pathlib import Path
from omegaconf import DictConfig, OmegaConf
from agir_cvtoolkit.pipelines.stages.det_infer import DetectionInferenceStage

def test_detection_inference_stage(tmp_path):
    """Test detection inference stage initialization."""
    cfg = OmegaConf.create({
        "det_inference": {
            "model": {"weights": "yolov8n.pt"},
            "multiscale": {
                "scales": [1.0],
                "base_imgsz": 640,
            },
        },
        "paths": {
            "query": str(tmp_path / "query"),
            "plots": str(tmp_path / "plots"),
        }
    })
    
    stage = DetectionInferenceStage(cfg)
    assert stage.cfg is not None

def test_multiscale_detector_init(tmp_path):
    """Test YOLOMultiscaleDetector initialization."""
    from agir_cvtoolkit.pipelines.stages.det_infer import YOLOMultiscaleDetector
    
    cfg = OmegaConf.create({
        "det_inference": {
            "model": {"weights": "yolov8n.pt"},
            "multiscale": {
                "scales": [0.75, 1.0, 1.25],
                "base_imgsz": 640,
            },
            "gpu": {"exclude_ids": []},
        },
        "paths": {"plots": str(tmp_path / "plots")},
    })
    
    detector = YOLOMultiscaleDetector(cfg)
    assert detector.model is not None
    assert len(detector.scales) == 3
```

Run tests:

```bash
pytest tests/test_det_infer.py -v
```

## Troubleshooting

### ImportError: No module named 'ultralytics'

```bash
pip install ultralytics
```

### FileNotFoundError: Model weights not found

Either:
1. Download YOLOv8 weights: `yolo detect predict model=yolov8n.pt source='https://ultralytics.com/images/bus.jpg'`
2. Specify correct path: `-o det_inference.model.weights=/path/to/model.pt`

### RuntimeError: CUDA out of memory

Try:
```bash
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.scales=[1.0] \
  -o det_inference.multiscale.base_imgsz=480
```

### AttributeError: 'DictConfig' object has no attribute 'det_inference'

Make sure the config file is properly loaded. Check that `conf/det_inference/default.yaml` exists.

## Quick Start Script

Here's a complete script to get started quickly:

```bash
#!/bin/bash
# quick_start_detection.sh

# Step 1: Query images
echo "Step 1: Querying images..."
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --sample "random:n=50" \
  --out csv

# Step 2: Run multiscale detection
echo "Step 2: Running multiscale detection..."
agir-cvtoolkit infer-det \
  -o det_inference.model.weights=yolov8n.pt \
  -o det_inference.multiscale.scales=[0.75,1.0,1.25]

echo "Detection complete! Check outputs/runs/ for results."
```

Make it executable and run:

```bash
chmod +x quick_start_detection.sh
./quick_start_detection.sh
```

## Next Steps

After successful integration:

1. **Test with your data**: Run on a small batch of your images
2. **Tune parameters**: Adjust scales and thresholds for your use case
3. **Train custom model**: Use your labeled data to train a YOLO model
4. **Integrate with CVAT**: Extend to upload detections for refinement (like infer-seg does)

## Support

For issues or questions:
- Check the USAGE_GUIDE.md for detailed examples
- Review the original ms_inferencing.py for reference
- Consult Ultralytics documentation: https://docs.ultralytics.com/

## Summary

You've successfully integrated multiscale detection inference into AgIR-CVToolkit! The new `infer-det` command follows the same patterns as other pipeline stages and provides powerful multiscale object detection capabilities.

**Key Features:**
✅ Multiscale inference with configurable scales
✅ Weighted boxes fusion for improved accuracy
✅ GPU device selection and memory management
✅ Configurable confidence and NMS thresholds
✅ Automatic integration with query stage
✅ Visualization and JSON output
✅ Follows existing CLI patterns
