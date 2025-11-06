# Detection Inference with Multiscale - AgIR-CVToolkit

This package adds multiscale object detection capabilities to the AgIR-CVToolkit, following the same patterns as the existing `query` and `infer-seg` tasks.

## 📦 Package Contents

This implementation includes:

1. **det_infer.py** - Main detection inference stage with multiscale processing
2. **default_det_inference_config.yaml** - Default configuration template
3. **cli_command.py** - CLI command to add to your cli.py
4. **USAGE_GUIDE.md** - Comprehensive usage documentation with examples
5. **INTEGRATION_GUIDE.md** - Step-by-step integration instructions
6. **README.md** - This file

## ✨ Features

- **Multiscale Inference**: Process images at multiple scales for better detection
- **Weighted Boxes Fusion**: Intelligently merge detections across scales
- **GPU Management**: Automatic device selection with memory monitoring
- **Configurable Parameters**: Full control over scales, thresholds, and fusion
- **Pipeline Integration**: Seamlessly works with query stage outputs
- **CLI Consistency**: Follows the same patterns as other AgIR-CVToolkit commands

## 🚀 Quick Start

### 1. Integration (5 minutes)

Follow the [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md) to add the feature to your toolkit.

### 2. Basic Usage

```bash
# Query images from database
agir-cvtoolkit query --db semif \
  --filters "state=NC" \
  --sample "random:n=100"

# Run multiscale detection
agir-cvtoolkit infer-det
```

### 3. View Results

Results are saved to:
- **Visualizations**: `outputs/runs/{run_id}/plots/`
- **Detections**: `outputs/runs/{run_id}/plots/detections.json`
- **Summary**: `outputs/runs/{run_id}/plots/summary.json`

## 📚 Documentation

- **[INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)** - How to add this to your toolkit
- **[USAGE_GUIDE.md](./USAGE_GUIDE.md)** - Complete usage documentation with examples

## 🎯 Key Concepts

### Multiscale Inference

Instead of processing images at a single resolution, multiscale inference:

1. Processes each image at multiple scales (e.g., 50%, 75%, 100%, 125%, 150%)
2. Detects objects at each scale with permissive thresholds
3. Fuses overlapping detections using weighted boxes fusion
4. Applies final NMS to remove remaining duplicates

**Benefits:**
- Better small object detection (using larger scales)
- Better large object detection (using smaller scales)
- Improved localization accuracy
- Higher confidence scores

### Weighted Boxes Fusion

A technique to combine multiple overlapping bounding boxes:

1. Cluster boxes with high IoU
2. Weight box coordinates by confidence scores
3. Compute fused confidence (average or max)
4. Output single refined box per cluster

## 🛠 Configuration Examples

### Fast Detection (Fewer Scales)

```bash
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.scales=[0.75,1.0,1.25] \
  -o det_inference.multiscale.base_imgsz=640
```

### High Accuracy (More Scales)

```bash
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.scales=[0.5,0.67,0.83,1.0,1.2,1.4,1.6] \
  -o det_inference.multiscale.base_imgsz=1280
```

### Small Object Focus

```bash
agir-cvtoolkit infer-det \
  -o det_inference.multiscale.scales=[1.0,1.25,1.5,1.75,2.0] \
  -o det_inference.final_nms.conf=0.2
```

### Custom Model

```bash
agir-cvtoolkit infer-det \
  -o det_inference.model.weights=models/my_yolo_model.pt
```

## 📊 Performance Tips

### Speed Optimization

- Use fewer scales: `[0.75, 1.0, 1.25]`
- Reduce base image size: `base_imgsz=480`
- Disable visualizations: `output.save_visualizations=false`

### Accuracy Optimization

- Use more scales: `[0.5, 0.67, 0.83, 1.0, 1.2, 1.4, 1.6]`
- Increase base image size: `base_imgsz=1280`
- Lower confidence threshold: `final_nms.conf=0.1`

### Memory Management

- Exclude busy GPUs: `gpu.exclude_ids=[0]`
- Reduce max detections: `per_scale_max_det=200`
- Process in smaller batches

## 🔧 Customization

The implementation is designed to be easily customizable:

### Custom Fusion Strategy

Edit the `weighted_boxes_fusion()` function in `det_infer.py` to implement your own fusion logic.

### Custom Post-processing

Modify the `_postprocess_det()` method to add custom filtering or transformation.

### Custom Output Format

Extend the `_save_results()` method to support additional output formats (COCO, YOLO txt, etc.).

## 📋 Requirements

```bash
pip install ultralytics torch torchvision opencv-python omegaconf hydra-core
```

Or add to `requirements.txt`:
```
ultralytics>=8.0.0
torch>=2.0.0
torchvision>=0.15.0
opencv-python>=4.8.0
omegaconf>=2.3.0
hydra-core>=1.3.0
```

## 🎬 Complete Workflow Example

```bash
# Step 1: Query a balanced dataset
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley" \
  --sample "stratified:by=area_bin,per_group=50"

# Step 2: Run multiscale detection
agir-cvtoolkit infer-det \
  -o det_inference.model.weights=models/my_detector.pt \
  -o det_inference.multiscale.scales=[0.75,1.0,1.25]

# Step 3: Check results
ls outputs/runs/*/plots/
cat outputs/runs/*/plots/summary.json
```

## 🤝 Consistency with AgIR-CVToolkit

This implementation follows all AgIR-CVToolkit patterns:

✅ Same CLI command structure as `infer-seg`
✅ Uses Hydra configuration system
✅ Integrates with `finalize_cfg()` and `setup_logging()`
✅ Reads from query stage outputs automatically
✅ Saves to standard output directory structure
✅ Provides same style of completion messages
✅ Follows same code organization as other stages

## 🔍 Differences from Original

Compared to the uploaded `ms_inferencing.py`:

**Removed:**
- Evaluation/metrics computation
- Ground truth comparison
- Side-by-side visualization
- CVAT-related functionality

**Kept:**
- Multiscale inference logic
- Weighted boxes fusion
- GPU device selection
- Configuration system
- Visualization generation

**Added:**
- AgIR-CVToolkit pipeline integration
- CLI command following toolkit patterns
- Automatic query results reading
- Standard output directory structure

## 📖 Reference

For more details on multiscale inference and weighted boxes fusion:
- [Weighted Boxes Fusion Paper](https://arxiv.org/abs/1910.13302)
- [Test-Time Augmentation for Object Detection](https://arxiv.org/abs/1902.08795)
- [Ultralytics YOLO Documentation](https://docs.ultralytics.com/)

## 🐛 Troubleshooting

### Common Issues

1. **Model not found**: Download YOLO weights or specify correct path
2. **CUDA OOM**: Reduce scales or base image size
3. **Too many detections**: Increase confidence threshold
4. **Missing detections**: Decrease confidence threshold or add more scales

See the [USAGE_GUIDE.md](./USAGE_GUIDE.md) for detailed troubleshooting.

## 📄 License

This implementation follows the same license as AgIR-CVToolkit.

## 🙏 Acknowledgments

Based on the multiscale inferencing implementation from the uploaded `ms_inferencing.py` file, adapted to fit the AgIR-CVToolkit pipeline patterns.

---

**Need help?** Check the comprehensive [USAGE_GUIDE.md](./USAGE_GUIDE.md) for detailed examples and troubleshooting tips.
