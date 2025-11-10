from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
import types
from pathlib import Path

import numpy as np
from omegaconf import OmegaConf
from PIL import Image
from typer.testing import CliRunner

from agir_cvtoolkit import cli as cli_mod
from agir_cvtoolkit.pipelines.utils.hydra_utils import finalize_cfg


def _module_available(name: str) -> bool:
    if name in sys.modules:
        return True
    spec = importlib.util.find_spec(name)
    return spec is not None


def _maybe_install_stub_modules():
    """Provide lightweight stand-ins for heavy optional deps that aren't installed in CI."""
    import types as _types

    if not _module_available("torch"):
        class _FakeTensor:
            def __init__(self, data=None):
                self.data = data

            def unsqueeze(self, _):
                return self

            def float(self):
                return self

            def to(self, _device):
                return self

            def cpu(self):
                return self

            def numpy(self):
                return self.data

            def __getitem__(self, _item):
                return self

        torch_stub = _types.ModuleType("torch")
        torch_stub.Tensor = _FakeTensor
        torch_stub.cuda = _types.SimpleNamespace(is_available=lambda: False)
        torch_stub.device = lambda name: name
        torch_stub.no_grad = lambda: (lambda fn: fn)
        torch_stub.from_numpy = lambda arr: _FakeTensor(arr)
        torch_stub.sigmoid = lambda tensor: tensor
        torch_stub.softmax = lambda tensor, dim=0: tensor

        def _load(*_args, **_kwargs):
            return {"state_dict": {}}

        torch_stub.load = _load
        torch_stub.nn = _types.SimpleNamespace(Module=object)
        sys.modules["torch"] = torch_stub

    if not _module_available("segmentation_models_pytorch"):
        smp_stub = _types.ModuleType("segmentation_models_pytorch")

        class _FakeModel:
            def eval(self):
                return self

            def to(self, _device):
                return self

        def _factory(*_args, **_kwargs):
            return _FakeModel()

        smp_stub.Unet = _factory
        smp_stub.DeepLabV3Plus = _factory
        smp_stub.Segformer = _factory
        sys.modules["segmentation_models_pytorch"] = smp_stub

    if not _module_available("GPUtil"):
        gputil_stub = _types.ModuleType("GPUtil")

        def _available(**_kwargs):
            return [0]

        gputil_stub.getAvailable = _available
        sys.modules["GPUtil"] = gputil_stub

    if not _module_available("cv2"):
        cv2_stub = _types.ModuleType("cv2")
        sys.modules["cv2"] = cv2_stub

    if not _module_available("matplotlib") or not _module_available("matplotlib.pyplot"):
        matplotlib_stub = _types.ModuleType("matplotlib")
        pyplot_stub = _types.ModuleType("matplotlib.pyplot")

        class _FakeFigure:
            def tight_layout(self):
                return None

            def savefig(self, *_args, **_kwargs):
                return None

        class _FakeAxes:
            def imshow(self, *_args, **_kwargs):
                return None

            def axis(self, *_args, **_kwargs):
                return None

            def set_title(self, *_args, **_kwargs):
                return None

        def _subplots(*_args, **_kwargs):
            return _FakeFigure(), [_FakeAxes()]

        def _close(*_args, **_kwargs):
            return None

        pyplot_stub.subplots = _subplots
        pyplot_stub.close = _close
        matplotlib_stub.pyplot = pyplot_stub
        sys.modules["matplotlib"] = matplotlib_stub
        sys.modules["matplotlib.pyplot"] = pyplot_stub

    if not _module_available("pandas"):
        pandas_stub = _types.ModuleType("pandas")

        def _notna(value):
            return value is not None

        class _Errors:
            EmptyDataError = Exception

        pandas_stub.notna = _notna
        pandas_stub.errors = _Errors()
        pandas_stub.DataFrame = object  # type: ignore[attr-defined]
        pandas_stub.concat = lambda *args, **kwargs: None
        pandas_stub.read_csv = lambda *args, **kwargs: None
        sys.modules["pandas"] = pandas_stub


_maybe_install_stub_modules()

from agir_cvtoolkit.pipelines.utils.seg_utils import load_image_from_record  # noqa: E402


class ManifestColumn:
    def __init__(self, ids: list[str]):
        self._ids = ids

    def unique(self) -> list[str]:
        return list(self._ids)


class ManifestStub:
    def __init__(self):
        self._ids: list[str] = []

    def __getitem__(self, key: str):
        if key != "record_id":
            raise KeyError(key)
        return ManifestColumn(self._ids)


def _build_seg_cfg(tmp_path: Path) -> OmegaConf:
    ckpt_path = tmp_path / "model.ckpt"
    ckpt_path.write_text("stub")
    cfg = OmegaConf.create(
        {
            "io": {
                "out_root": str(tmp_path / "outputs"),
                "semif_storage_dir": str(tmp_path / "storage"),
                "field_storage_dir": str(tmp_path / "storage_field"),
            },
            "db": {"semif": {"db_path": str(tmp_path / "semif.db"), "table": "semif"}},
            "train": {
                "logger": {
                    "csv": {"save_dir": ""},
                    "wandb": {"save_dir": "", "name": ""},
                }
            },
            "seg_inference": {
                "source": {
                    "type": "query_result",
                    "db": "semif",
                    "image_mode": "cutout",
                },
                "tile": {
                    "height": 16,
                    "width": 16,
                    "overlap": 0.0,
                    "pad_mode": "reflect",
                },
                "model": {
                    "arch": "unet",
                    "encoder_name": "resnet18",
                    "in_channels": 3,
                    "num_classes": 1,
                    "encoder_weights": "imagenet",
                    "ckpt_path": str(ckpt_path),
                    "pad_divisor": 16,
                    "normalization": {"mean": [0, 0, 0], "std": [1, 1, 1]},
                    "strict_load": True,
                },
                "post_process": {
                    "threshold": 0.5,
                    "min_area": 0,
                    "edge_occupancy_threshold": 0.9,
                },
                "visualization": {"enabled": False, "overlay_alpha": 0.5},
                "output": {
                    "save_masks": True,
                    "save_images": True,
                    "save_cutouts": True,
                    "save_viz": False,
                    "save_colorized_masks": False,
                    "colorize_brightness": 6.5,
                    "cutout_use_rgba": False,
                },
                "gpu": {"max_gpus": 1, "exclude_ids": []},
            },
        }
    )
    return finalize_cfg(cfg, stage="infer_seg", dataset="semif", cli_overrides=None)


def test_infer_seg_cli_invokes_stage(monkeypatch, tmp_path):
    """infer-seg should finalize the cfg and run SegmentationInferenceStage once."""
    out_root = tmp_path / "outputs"

    def _fake_compose(config: str, overrides):
        return OmegaConf.create(
            {
                "io": {"out_root": str(out_root)},
                "train": {
                    "logger": {
                        "csv": {"save_dir": ""},
                        "wandb": {"save_dir": "", "name": ""},
                    }
                },
                "seg_inference": {
                    "source": {"type": "query_result", "db": "semif"},
                },
            }
        )

    monkeypatch.setattr(cli_mod, "_compose_cfg", _fake_compose)

    class DummyStage:
        instances: list["DummyStage"] = []
        run_calls = 0

        def __init__(self, cfg):
            self.cfg = cfg
            DummyStage.instances.append(self)

        def run(self):
            DummyStage.run_calls += 1

    fake_module = types.ModuleType("agir_cvtoolkit.pipelines.stages.seg_infer")
    fake_module.SegmentationInferenceStage = DummyStage
    monkeypatch.setitem(sys.modules, "agir_cvtoolkit.pipelines.stages.seg_infer", fake_module)

    runner = CliRunner()
    result = runner.invoke(cli_mod.app, ["infer-seg"])

    try:
        assert result.exit_code == 0, result.output
        assert DummyStage.run_calls == 1
        assert DummyStage.instances, "stage should be initialized"
        cfg = DummyStage.instances[0].cfg
        assert cfg.runtime.stage == "infer_seg"
        manifest_path = Path(cfg.paths.manifest_path)
        metrics_path = Path(cfg.paths.metrics_path)
        assert manifest_path.name == "manifest.csv"
        assert manifest_path.exists()
        assert metrics_path.exists()
        assert Path(cfg.paths.images).exists()
        assert Path(cfg.paths.masks).exists()
        assert "Segmentation inference complete" in result.output
    finally:
        # Clean up logging handlers so later tests don't hit closed streams
        root = logging.getLogger()
        for handler in list(root.handlers):
            try:
                handler.flush()
            except Exception:
                pass
            try:
                handler.close()
            except Exception:
                pass
            root.removeHandler(handler)


def test_load_image_from_record_prefers_cropout_and_applies_bbox(tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    crop_dir = storage / "cropouts"
    crop_dir.mkdir()
    full_dir = storage / "full"
    full_dir.mkdir()

    crop_img = Image.new("RGB", (4, 4), color=(128, 64, 32))
    crop_path = crop_dir / "crop.png"
    crop_img.save(crop_path)

    full_arr = np.arange(4 * 4 * 3, dtype=np.uint8).reshape(4, 4, 3)
    full_path = full_dir / "full.png"
    Image.fromarray(full_arr, mode="RGB").save(full_path)

    cfg = OmegaConf.create(
        {"io": {"semif_storage_dir": str(storage), "field_storage_dir": str(storage)}}
    )

    record_cropout = {
        "cropout_path": f"{crop_dir.name}/{crop_path.name}",
        "cutout_ncsu_nfs": "",
        "image_path": f"{full_dir.name}/{full_path.name}",
        "ncsu_nfs": "",
    }
    crop_arr = load_image_from_record(record_cropout, cfg)
    assert crop_arr.shape == (4, 4, 3)
    assert np.all(crop_arr == np.array(crop_img))

    record_bbox = {
        "cropout_path": None,
        "image_path": f"{full_dir.name}/{full_path.name}",
        "ncsu_nfs": "",
        "bbox_xywh": str([1, 1, 2, 2]),
    }
    bbox_arr = load_image_from_record(record_bbox, cfg)
    assert bbox_arr.shape == (2, 2, 3)
    expected = full_arr[1:3, 1:3]
    assert np.array_equal(bbox_arr, expected)

    record_missing = {
        "cropout_path": "missing.png",
        "cutout_ncsu_nfs": "",
    }
    assert load_image_from_record(record_missing, cfg) is None


def test_process_record_writes_outputs_with_stubbed_stage(monkeypatch, tmp_path):
    cfg = _build_seg_cfg(tmp_path)
    import sys as _sys

    if "agir_cvtoolkit.pipelines.stages.seg_infer" in _sys.modules:
        del _sys.modules["agir_cvtoolkit.pipelines.stages.seg_infer"]

    seg_stage_mod = importlib.import_module("agir_cvtoolkit.pipelines.stages.seg_infer")

    class DummySegModel:
        loaded_ckpt: Path | None = None

        def __init__(self, **_kwargs):
            pass

        def load_checkpoint(self, ckpt_path: Path, device, strict: bool):
            DummySegModel.loaded_ckpt = Path(ckpt_path)

    class DummyTiledInference:
        def __init__(self, **_kwargs):
            pass

        def predict(self, img_rgb_u8, model, device):
            h, w = img_rgb_u8.shape[:2]
            return np.ones((h, w), dtype=np.uint8) * 255

    class DummyPostProcessor:
        def __init__(self, **_kwargs):
            pass

        def process(self, mask, class_id: int):
            return mask, 0.1

    monkeypatch.setattr(seg_stage_mod, "select_available_gpus", lambda *args, **kwargs: [0])
    monkeypatch.setattr(seg_stage_mod, "SegModel", DummySegModel)
    monkeypatch.setattr(seg_stage_mod, "TiledInference", DummyTiledInference)
    monkeypatch.setattr(seg_stage_mod, "SegPostProcessor", DummyPostProcessor)
    monkeypatch.setattr(
        seg_stage_mod,
        "load_image_from_record",
        lambda record, cfg, image_mode="cutout": np.full((4, 4, 3), 100, dtype=np.uint8),
    )

    stage = seg_stage_mod.SegmentationInferenceStage(cfg)
    assert DummySegModel.loaded_ckpt == Path(cfg.seg_inference.model.ckpt_path)

    record = {"cutout_id": "rec123", "category_common_name": "rye"}
    manifest = ManifestStub()
    result = stage._process_record(
        record=record,
        manifest=manifest,
        save_mask=True,
        save_image=True,
        save_cutout=True,
        save_viz=False,
        save_colorized=False,
    )

    assert result is not None
    mask_path = Path(result["mask_path"])
    cutout_path = Path(result["cutout_path"])
    image_path = Path(result["image_path"])
    assert mask_path.exists()
    assert cutout_path.exists()
    assert image_path.exists()
    assert stage.metrics["processed"] >= 1
