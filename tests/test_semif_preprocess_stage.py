from __future__ import annotations

import json
import shutil
from pathlib import Path

from omegaconf import OmegaConf
from PIL import Image

from agir_cvtoolkit.pipelines.stages.preprocess import PreprocessStage
from agir_cvtoolkit.pipelines.utils.hydra_utils import finalize_cfg

FIXTURE_ROOT = Path(__file__).parent / "data" / "preprocess"


def _copy_fixtures(tmp_path: Path) -> tuple[Path, Path]:
    src_images = FIXTURE_ROOT / "images"
    src_masks = FIXTURE_ROOT / "masks"
    assert src_images.exists() and src_masks.exists(), "missing preprocess fixtures"

    work_images = tmp_path / "fixtures" / "images"
    work_masks = tmp_path / "fixtures" / "masks"
    shutil.copytree(src_images, work_images)
    shutil.copytree(src_masks, work_masks)
    return work_images, work_masks


def _build_cfg(
    tmp_path: Path,
    images_dir: Path,
    masks_dir: Path,
    *,
    resolve: bool,
    pad: bool,
    split: bool,
    stats: bool,
) -> OmegaConf:
    return OmegaConf.create(
        {
            "io": {"out_root": str(tmp_path / "outputs")},
            "train": {
                "seed": 7,
                "logger": {
                    "csv": {"save_dir": ""},
                    "wandb": {"save_dir": "", "name": ""},
                },
            },
            "preprocess": {
                "source": {
                    "type": "custom",
                    "db": None,
                    "tasks": None,
                    "custom_images_dir": str(images_dir),
                    "custom_masks_dir": str(masks_dir),
                },
                "resolve_images": {"enabled": resolve},
                "pad_gridcrop_resize": {
                    "enabled": pad,
                    "use_concurrency": False,
                    "num_workers": 1,
                    "size": {"height": 32, "width": 32},
                    "ignore_empty_data": False,
                    "remove_src": False,
                    "pad": {"enabled": True, "mode": "constant", "fill": 0},
                    "grid_crop": {"enabled": True, "stride": 16, "threshold": 2.0},
                    "resize": {
                        "enabled": True,
                        "interpolation": {"image": "BILINEAR", "mask": "NEAREST"},
                    },
                },
                "split": {
                    "enabled": split,
                    "use_concurrency": False,
                    "num_workers": 1,
                    "train": 0.5,
                    "val": 0.25,
                    "test": 0.25,
                    "remove_src": False,
                    "seed": 123,
                },
                "compute_data_stats": {
                    "enabled": stats,
                    "use_concurrency": False,
                    "num_workers": 1,
                },
            },
        }
    )


def _run_preprocess(
    tmp_path: Path,
    *,
    resolve: bool,
    pad: bool,
    split: bool,
    stats: bool,
):
    work_images, work_masks = _copy_fixtures(tmp_path)
    cfg = _build_cfg(
        tmp_path,
        work_images,
        work_masks,
        resolve=resolve,
        pad=pad,
        split=split,
        stats=stats,
    )
    cfg = finalize_cfg(cfg, stage="preprocess", dataset="train", cli_overrides=None)

    # Mirror the source images into run_root/images so resolve_images can find them.
    run_images_dir = Path(cfg.paths.images)
    for img in work_images.glob("*.jpg"):
        shutil.copy2(img, run_images_dir / img.name)

    PreprocessStage(cfg).run()
    metrics = json.loads(Path(cfg.paths.metrics_path).read_text())
    return cfg, metrics


def test_preprocess_resolve_images(tmp_path):
    cfg, metrics = _run_preprocess(
        tmp_path,
        resolve=True,
        pad=False,
        split=False,
        stats=False,
    )

    assert metrics["resolved_images"] == 3

    manifest_path = Path(cfg.paths.run_root) / "image_mask_manifest.txt"
    lines = [line for line in manifest_path.read_text().splitlines() if line.strip()]
    assert len(lines) == metrics["resolved_images"]


def test_preprocess_pad_gridcrop_resize(tmp_path):
    cfg, metrics = _run_preprocess(
        tmp_path,
        resolve=False,
        pad=True,
        split=False,
        stats=False,
    )

    preprocessed_images = Path(cfg.paths.preprocessed) / "images"
    files = sorted(preprocessed_images.glob("*.jpg"))
    assert files, "expected resized images to be written"
    for img_path in files:
        with Image.open(img_path) as img:
            assert img.size == (32, 32)
    assert metrics["preprocessed_images"] == len(files)


def test_preprocess_split(tmp_path):
    _, metrics = _run_preprocess(
        tmp_path,
        resolve=False,
        pad=False,
        split=True,
        stats=False,
    )

    assert metrics["train_samples"] == 1
    assert metrics["val_samples"] == 0
    assert metrics["test_samples"] == 2
    total = metrics["train_samples"] + metrics["val_samples"] + metrics["test_samples"]
    assert total == metrics["preprocessed_images"]


def test_preprocess_compute_data_stats(tmp_path):
    cfg, metrics = _run_preprocess(
        tmp_path,
        resolve=False,
        pad=False,
        split=True,
        stats=True,
    )

    stats_file = Path(cfg.paths.run_root) / "datastats" / "rgb_mean_std.json"
    stats = json.loads(stats_file.read_text())
    assert stats["mean"] == metrics["rgb_mean"]
    assert stats["std"] == metrics["rgb_std"]

    train_dir = Path(cfg.paths.run_root) / "train_val_test" / "train" / "images"
    assert train_dir.exists() and any(train_dir.iterdir())
