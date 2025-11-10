# Training Pipeline Usage Guide

## Overview

The AgIR-CVToolkit training pipeline provides end-to-end model training for semantic segmentation tasks using PyTorch Lightning.

## Features

- **Flexible Architecture**: Support for multiple encoder-decoder architectures via `segmentation_models_pytorch`
- **Rich Augmentations**: Comprehensive spatial and pixel-level augmentations
- **Batch Augmentations**: MixUp, CutMix, and Mosaic for improved generalization
- **Reproducibility**: Full configuration tracking with Hydra
- **Monitoring**: Built-in support for CSV and W&B logging
- **Visualization**: Dataset and augmentation visualizers

## Prerequisites

```bash
# Install training dependencies
pip install pytorch-lightning segmentation-models-pytorch torchmetrics wandb
```

## Quick Start

### 1. Prepare Your Data

Organize your data in the following structure:

```
data/
├── train/
│   ├── images/
│   │   ├── img_001.jpg
│   │   └── ...
│   └── masks/
│       ├── img_001_mask.png
│       └── ...
└── val/
    ├── images/
    └── masks/
```

**Important**: Mask files must start with the corresponding image filename (e.g., `img_001.jpg` → `img_001_mask.png`).

### 2. Configure Paths

Create or update your project configuration:

```yaml
# conf/paths/default.yaml
train_images_dir: /path/to/data/train/images
train_masks_dir: /path/to/data/train/masks
val_images_dir: /path/to/data/val/images
val_masks_dir: /path/to/data/val/masks
```

### 3. Run Training

```bash
# Basic training with defaults
agir-cvtoolkit train

# With custom configuration
agir-cvtoolkit train -o train.max_epochs=50 -o train.batch_size=16
```

## Configuration

### Model Architecture

Configure model architecture in `conf/train/default.yaml`:

```yaml
model:
  arch_name: "Unet"  # Unet, FPN, PSPNet, DeepLabV3Plus, etc.
  encoder_name: "resnet34"  # resnet34, efficientnet-b0, etc.
  encoder_weights: "imagenet"
  in_channels: 3
  classes: 1  # Binary segmentation
```

Supported architectures:
- **Unet**: Classic U-Net architecture
- **UnetPlusPlus**: U-Net++ with nested skip connections
- **FPN**: Feature Pyramid Network
- **PSPNet**: Pyramid Scene Parsing Network
- **DeepLabV3Plus**: DeepLab v3+ with atrous convolution
- **MAnet**: Multi-scale Attention Network

Supported encoders (via `timm`):
- ResNet family: `resnet18`, `resnet34`, `resnet50`, `resnet101`
- EfficientNet family: `efficientnet-b0` through `efficientnet-b7`
- MobileNet: `mobilenet_v2`
- DenseNet: `densenet121`, `densenet169`, `densenet201`
- And many more...

### Training Hyperparameters

```yaml
train:
  seed: 42
  max_epochs: 100
  batch_size: 8
  num_workers: 4
  
  optimizer:
    _target_: torch.optim.Adam
    lr: 0.001
    weight_decay: 0.0001
  
  scheduler:
    _target_: torch.optim.lr_scheduler.ReduceLROnPlateau
    mode: "min"
    factor: 0.5
    patience: 5
```

### Augmentations

Configure augmentations in `conf/augment/default.yaml`:

```yaml
train:
  img_size:
    height: 512
    width: 512
  
  spatial:
    enable: true
    horizontal_flip:
      enable: true
      p: 0.5
    random_rotate90:
      enable: true
      p: 0.5
  
  pixel:
    enable: true
    random_brightness_contrast:
      enable: true
      p: 0.5
```

## Advanced Usage

### Multi-GPU Training

Enable multi-GPU training:

```bash
agir-cvtoolkit train \
  -o train.use_multi_gpu=true \
  -o train.gpu.max_gpus=2 \
  -o train.gpu.exclude_ids=[0]
```

### Weights & Biases Integration

Enable W&B logging:

```bash
agir-cvtoolkit train \
  -o train.logger.wandb.enable=true \
  -o train.logger.wandb.project="my-project"
```

### Visualization

Enable dataset and augmentation visualizations:

```bash
agir-cvtoolkit train \
  -o train.dataloader_visualizer.enabled=true \
  -o train.augmentation_visualizer.enabled=true
```

### Custom Augmentation Pipeline

You can enable/disable individual augmentations:

```bash
# Enable batch-level MixUp
agir-cvtoolkit train \
  -o augment.train.batch.mixup.enable=true \
  -o augment.train.batch.mixup.p=0.5

# Disable color jitter
agir-cvtoolkit train \
  -o augment.train.pixel.color_jitter.enable=false
```

### Resume from Checkpoint

```bash
agir-cvtoolkit train \
  -o train.resume_from_checkpoint=/path/to/checkpoint.ckpt
```

## Output Structure

Training creates the following output structure:

```
outputs/runs/{run_id}/
├── checkpoints/
│   ├── epoch=00-step=100-val_loss=0.12.ckpt
│   ├── epoch=01-step=200-val_loss=0.10.ckpt
│   └── last.ckpt
├── model/
│   └── epoch=01-step=200-val_loss=0.10.pth  # Exported weights
├── csv_logs/
│   ├── metrics.csv
│   └── version_0/
├── image_logs/  # If visualization enabled
│   ├── batch_visualization_image.png
│   ├── batch_visualization_mask.png
│   └── aug_visualization.png
├── cfg.yaml
├── metrics.json
└── logs/
    └── {timestamp}.log
```

## Metrics

The pipeline tracks the following metrics:

- **Loss**: Binary Cross-Entropy with Logits
- **IoU** (Intersection over Union): Measures overlap between prediction and ground truth
- **Dice** (F1 Score): Harmonic mean of precision and recall

All metrics are logged per epoch for both training and validation sets.

## Best Practices

### 1. Data Preparation

- **Ensure proper pairing**: Mask filenames must start with image filenames
- **Check mask format**: Masks should be single-channel (grayscale) with binary values (0 or 255)
- **Validate data**: Run with visualization enabled first to check data loading

### 2. Model Selection

- **Start simple**: Begin with `resnet34` encoder, it's fast and effective
- **Scale up**: Use `resnet50` or `efficientnet-b3` for better accuracy
- **Memory constraints**: Use smaller encoders like `mobilenet_v2` for limited GPU memory

### 3. Hyperparameter Tuning

- **Learning rate**: Start with `0.001`, reduce if loss oscillates
- **Batch size**: Use largest batch size that fits in memory (4, 8, 16, 32)
- **Augmentation strength**: Start conservative, increase if overfitting

### 4. Monitoring Training

- **Check metrics regularly**: Monitor IoU and Dice scores
- **Early stopping**: Default patience is 10 epochs, adjust based on dataset size
- **Learning rate schedule**: ReduceLROnPlateau works well for most cases

### 5. Avoiding Overfitting

- **Use augmentations**: Enable spatial and pixel augmentations
- **Add regularization**: Increase `weight_decay` in optimizer
- **Early stopping**: Let early stopping prevent overfitting
- **Batch augmentations**: Consider enabling MixUp or CutMix

## Troubleshooting

### Out of Memory (OOM)

```bash
# Reduce batch size
agir-cvtoolkit train -o train.batch_size=4

# Reduce image size
agir-cvtoolkit train \
  -o augment.train.img_size.height=256 \
  -o augment.train.img_size.width=256

# Use smaller encoder
agir-cvtoolkit train -o train.model.encoder_name="resnet18"
```

### Slow Training

```bash
# Increase workers
agir-cvtoolkit train -o train.num_workers=8

# Enable pin_memory
agir-cvtoolkit train -o train.pin_memory=true

# Use mixed precision (if supported)
agir-cvtoolkit train -o train.trainer.precision="16-mixed"
```

### Poor Performance

- **Check data quality**: Enable visualizations to inspect inputs
- **Increase augmentation**: Add more spatial/pixel augmentations
- **Try different architecture**: Experiment with encoder/decoder combinations
- **Adjust learning rate**: Try different optimizers (Adam, AdamW, SGD)
- **Train longer**: Increase `max_epochs` if loss is still decreasing

## Integration with Pipeline

### Full Pipeline Example

```bash
# 1. Query database
agir-cvtoolkit query --db semif \
  --filters "category_common_name=barley" \
  --sample "stratified:by=area_bin,per_group=100" \
  --out csv

# 2. Run segmentation inference
agir-cvtoolkit infer-seg

# 3. Upload to CVAT for refinement
agir-cvtoolkit upload-cvat

# 4. After annotation, download refined masks
agir-cvtoolkit download-cvat

# 5. Prepare training data (preprocess stage - to be implemented)
# agir-cvtoolkit preprocess --split-ratio 0.8

# 6. Train model
agir-cvtoolkit train

# 7. Use trained model for inference
agir-cvtoolkit infer-seg \
  -o seg_inference.model.ckpt_path=outputs/runs/train_xxx/model/best.pth
```

## Examples

### Example 1: Quick Training Run

```bash
agir-cvtoolkit train \
  -o train.max_epochs=10 \
  -o train.batch_size=8
```

### Example 2: Production Training

```bash
agir-cvtoolkit train \
  -o train.max_epochs=100 \
  -o train.batch_size=16 \
  -o train.model.encoder_name="resnet50" \
  -o train.logger.wandb.enable=true \
  -o augment.train.batch.mixup.enable=true
```

### Example 3: Fast Experimentation

```bash
agir-cvtoolkit train \
  -o train.max_epochs=5 \
  -o train.batch_size=4 \
  -o augment.train.img_size.height=256 \
  -o augment.train.img_size.width=256 \
  -o train.dataloader_visualizer.enabled=true
```

## API Reference

### Python API

For programmatic use:

```python
from omegaconf import DictConfig
from agir_cvtoolkit.pipelines.stages.train import TrainingStage
from agir_cvtoolkit.pipelines.utils.hydra_utils import finalize_cfg

# Create config
cfg = DictConfig({
    "train": {
        "max_epochs": 50,
        "batch_size": 8,
        # ... other settings
    },
    "paths": {
        "train_images_dir": "/path/to/train/images",
        # ... other paths
    }
})

# Finalize config
cfg = finalize_cfg(cfg, stage="train", dataset="field", cli_overrides=[])

# Run training
stage = TrainingStage(cfg)
stage.run()
```

## FAQ

**Q: Can I use my own model architecture?**  
A: Yes, modify `LitSegmentation` class in `train_utils.py` to use custom models.

**Q: How do I use a pretrained checkpoint?**  
A: Set `train.model.encoder_weights=/path/to/checkpoint.pth` or load in code.

**Q: Can I train on multi-class segmentation?**  
A: Yes, change `train.model.classes` to the number of classes and adjust loss function.

**Q: How do I export model for deployment?**  
A: Best model is automatically exported as `.pth` file in `model/` directory.

**Q: Can I use different augmentation libraries?**  
A: Currently uses Albumentations. Extend `get_train_transforms()` to use others.

## Resources

- **segmentation_models_pytorch**: https://github.com/qubvel/segmentation_models.pytorch
- **PyTorch Lightning**: https://lightning.ai/docs/pytorch/stable/
- **Albumentations**: https://albumentations.ai/docs/
- **Weights & Biases**: https://docs.wandb.ai/

## Support

For issues or questions:
1. Check this documentation
2. Review configuration files
3. Enable visualizations to debug data issues
4. Check PyTorch Lightning documentation for training issues