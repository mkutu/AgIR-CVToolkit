from __future__ import annotations

import importlib.util
import json
import logging
import sys
import types
from pathlib import Path

import numpy as np
from omegaconf import OmegaConf
from typer.testing import CliRunner

from agir_cvtoolkit import cli as cli_mod
from agir_cvtoolkit.pipelines.utils.hydra_utils import finalize_cfg


def _module_available(name: str) -> bool:
    if name in sys.modules:
        return True
    spec = importlib.util.find_spec(name)
    return spec is not None


def _maybe_install_stub_modules() -> None:
    """Provide lightweight stand-ins for optional heavy deps absent in CI."""
    import types as _types

    if not _module_available("torch"):
        torch_stub = _types.ModuleType("torch")

        class _FakeTensor:
            def __init__(self, data=None):
                self.data = data
                self.shape = getattr(data, "shape", ())

            def detach(self):
                return self

            def cpu(self):
                return self

            def numpy(self):
                return self.data

            def unsqueeze(self, _):
                return self

            def float(self):
                return self

            def to(self, _device):
                return self

            def numel(self):
                return 0 if self.data is None else int(np.size(self.data))

            def __getitem__(self, _item):
                return self

        torch_stub.Tensor = _FakeTensor

        def _no_grad(fn=None):
            if fn is None:
                def decorator(func):
                    return func

                return decorator
            return fn

        class _FakeCuda:
            @staticmethod
            def is_available():
                return False

            @staticmethod
            def device_count():
                return 0

            @staticmethod
            def mem_get_info(_index=0):
                return (0, 0)

        torch_stub.no_grad = _no_grad
        torch_stub.cuda = _FakeCuda()
        torch_stub.device = lambda name: name
        torch_stub.from_numpy = lambda arr: _FakeTensor(arr)
        torch_stub.sigmoid = lambda tensor: tensor
        torch_stub.softmax = lambda tensor, dim=0: tensor
        sys.modules["torch"] = torch_stub

    if not _module_available("torchvision"):
        torchvision_stub = _types.ModuleType("torchvision")
        sys.modules["torchvision"] = torchvision_stub
    if not _module_available("torchvision.ops"):
        ops_stub = _types.ModuleType("torchvision.ops")
        def _fake_batched_nms(boxes, scores, labels, iou_threshold):
            if hasattr(scores, "shape"):
                length = int(scores.shape[0])
            elif isinstance(scores, (list, tuple)):
                length = len(scores)
            else:
                length = 0
            return np.arange(length)

        ops_stub.batched_nms = _fake_batched_nms
        sys.modules["torchvision.ops"] = ops_stub
        setattr(sys.modules["torchvision"], "ops", ops_stub)

    if not _module_available("cv2"):
        cv2_stub = _types.ModuleType("cv2")
        cv2_stub.FONT_HERSHEY_SIMPLEX = 0
        cv2_stub.LINE_AA = 0
        cv2_stub.getTextSize = lambda text, font, font_scale, thickness: (
            (int(len(text) * 10 * font_scale), int(20 * font_scale)),
            0,
        )
        cv2_stub.rectangle = lambda *args, **kwargs: None
        cv2_stub.addWeighted = lambda *args, **kwargs: None
        cv2_stub.putText = lambda *args, **kwargs: None
        cv2_stub.resize = lambda img, dsize, fx=1.0, fy=1.0: img
        cv2_stub.imwrite = lambda path, img: True
        sys.modules["cv2"] = cv2_stub

    if not _module_available("ultralytics"):
        ultralytics_stub = _types.ModuleType("ultralytics")

        class _FakeYOLO:
            def __init__(self, weights):
                self.weights = weights
                self.names = {0: "stub"}

            def to(self, device):
                self.device = device
                return self

            def predict(self, *args, **kwargs):
                return []

        ultralytics_stub.YOLO = _FakeYOLO

        engine_mod = _types.ModuleType("ultralytics.engine")
        results_mod = _types.ModuleType("ultralytics.engine.results")

        class _FakeResults:
            def __init__(self, boxes=None, orig_img=None, path="", names=None):
                self.boxes = boxes or _types.SimpleNamespace(
                    xyxy=np.zeros((0, 4)),
                    xywh=np.zeros((0, 4)),
                    xywhn=np.zeros((0, 4)),
                    conf=np.zeros(0),
                    cls=np.zeros(0),
                    shape=(0, 6),
                    detach=lambda: self,
                    cpu=lambda: self,
                    numpy=lambda: np.zeros((0, 4)),
                )
                self.orig_img = orig_img
                self.path = path
                self.names = names or {}

            def plot(self, **_kwargs):
                return np.zeros((4, 4, 3), dtype=np.uint8)

        results_mod.Results = _FakeResults

        data_mod = _types.ModuleType("ultralytics.data")
        data_build_mod = _types.ModuleType("ultralytics.data.build")
        data_loaders_mod = _types.ModuleType("ultralytics.data.loaders")

        def _check_source(paths):
            dummy = _types.SimpleNamespace(source_type="files")
            return dummy, False, False, False, False, False

        class _FakeDataset:
            def __init__(self, path, batch, channels):
                self._paths = path if isinstance(path, list) else [path]

            def __len__(self):
                return len(self._paths)

            def __iter__(self):
                for p in self._paths:
                    yield [p], [np.zeros((4, 4, 3), dtype=np.uint8)], None

        class _FakeSourceTypes(tuple):
            pass

        ultralytics_stub.engine = engine_mod
        ultralytics_stub.data = data_mod
        data_build_mod.check_source = _check_source
        data_loaders_mod.LoadImagesAndVideos = _FakeDataset
        data_loaders_mod.SourceTypes = _FakeSourceTypes

        sys.modules["ultralytics"] = ultralytics_stub
        sys.modules["ultralytics.engine"] = engine_mod
        sys.modules["ultralytics.engine.results"] = results_mod
        sys.modules["ultralytics.data"] = data_mod
        sys.modules["ultralytics.data.build"] = data_build_mod
        sys.modules["ultralytics.data.loaders"] = data_loaders_mod


_maybe_install_stub_modules()

from agir_cvtoolkit.pipelines.stages import det_infer as det_stage_mod  # noqa: E402


def _build_det_cfg(tmp_path: Path):
    weights = tmp_path / "model.pt"
    weights.write_text("stub")
    cfg = OmegaConf.create(
        {
            "io": {
                "out_root": str(tmp_path / "outputs"),
                "semif_storage_dir": str(tmp_path / "semif"),
                "field_storage_dir": str(tmp_path / "field"),
            },
            "train": {
                "logger": {
                    "csv": {"save_dir": ""},
                    "wandb": {"save_dir": "", "name": ""},
                }
            },
            "det_inference": {
                "source": {"type": "query_result", "db": "semif"},
                "model": {"weights": str(weights)},
                "multiscale": {
                    "scales": [1.0],
                    "base_imgsz": 32,
                    "per_scale_conf": 0.1,
                    "per_scale_iou": 0.5,
                    "per_scale_max_det": 5,
                },
                "fusion": {
                    "iou_thr": 0.5,
                    "skip_box_thr": 0.0,
                    "conf_type": "max",
                    "score_power": 1.0,
                },
                "post_fusion_nms": {"enabled": False, "iou": 0.4},
                "final_nms": {"conf": 0.25, "iou": 0.45, "max_det": 5},
                "edge_aware_filter": {
                    "edge_band_rel": 0.1,
                    "min_factor": 0.5,
                    "taper_rel": 0.2,
                },
                "output": {
                    "save_visualizations": False,
                    "save_txt": False,
                    "save_json": True,
                    "draw_labels": True,
                    "draw_boxes": True,
                    "draw_conf": True,
                },
                "gpu": {"exclude_ids": [], "min_free_gb": 0.0},
            },
        }
    )
    return finalize_cfg(cfg, stage="infer_det", dataset="semif", cli_overrides=None)


def _reset_logging_handlers():
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


def test_infer_det_cli_invokes_stage(monkeypatch, tmp_path):
    """infer-det should finalize the cfg and run DetectionInferenceStage once."""

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
                "det_inference": {
                    "source": {"type": "query_result", "db": "semif"},
                    "model": {"weights": str(tmp_path / "weights.pt")},
                },
            }
        )

    (tmp_path / "weights.pt").write_text("stub")
    monkeypatch.setattr(cli_mod, "_compose_cfg", _fake_compose)

    class DummyStage:
        instances: list["DummyStage"] = []
        run_calls = 0

        def __init__(self, cfg):
            self.cfg = cfg
            DummyStage.instances.append(self)

        def run(self):
            DummyStage.run_calls += 1

    fake_module = types.ModuleType("agir_cvtoolkit.pipelines.stages.det_infer")
    fake_module.DetectionInferenceStage = DummyStage
    monkeypatch.setitem(sys.modules, "agir_cvtoolkit.pipelines.stages.det_infer", fake_module)

    runner = CliRunner()
    result = runner.invoke(cli_mod.app, ["infer-det"])

    try:
        assert result.exit_code == 0, result.output
        assert DummyStage.run_calls == 1
        assert DummyStage.instances, "stage should be initialized"
        cfg = DummyStage.instances[0].cfg
        assert cfg.runtime.stage == "infer_det"
        assert Path(cfg.paths.run_root).exists()
        assert Path(cfg.paths.manifest_path).exists()
        assert Path(cfg.paths.metrics_path).exists()
        assert Path(cfg.paths.plots).exists()
        assert "Detection inference complete" in result.output
    finally:
        _reset_logging_handlers()


def test_detection_stage_run_invokes_detector(monkeypatch, tmp_path):
    """DetectionInferenceStage should construct and run YOLOMultiscaleDetector once."""

    cfg = _build_det_cfg(tmp_path)
    calls: list[str] = []

    class DummyDetector:
        def __init__(self, seen_cfg):
            calls.append(("init", seen_cfg))

        def run(self):
            calls.append(("run", None))

    monkeypatch.setattr(det_stage_mod, "YOLOMultiscaleDetector", DummyDetector)

    stage = det_stage_mod.DetectionInferenceStage(cfg)
    stage.run()

    assert calls == [("init", cfg), ("run", None)]


def test_save_results_writes_detections_and_summary(monkeypatch, tmp_path):
    """_save_results should emit detections.json and summary.json with correct counts."""

    cfg = _build_det_cfg(tmp_path)
    monkeypatch.setattr(
        det_stage_mod, "load_query_spec", lambda path: {"database": {"type": "semif"}}
    )
    monkeypatch.setattr(det_stage_mod, "pick_best_device", lambda **_: "cpu")

    class DummyYOLO:
        def __init__(self, weights):
            self.weights = weights
            self.names = {0: "class0"}

        def to(self, device):
            self.device = device
            return self

    monkeypatch.setattr(det_stage_mod, "YOLO", DummyYOLO)

    detector = det_stage_mod.YOLOMultiscaleDetector(cfg)
    results = [
        {
            "image_id": "img1",
            "image_path": "/tmp/img1.jpg",
            "xywh_detections": [[1, 2, 3, 4]],
            "xywhn_detections": [[0.1, 0.2, 0.3, 0.4]],
            "confidences": [0.9],
            "num_detections": 1,
        },
        {
            "image_id": "img2",
            "image_path": "/tmp/img2.jpg",
            "xywh_detections": [],
            "xywhn_detections": [],
            "confidences": [],
            "num_detections": 0,
        },
    ]

    detector._save_results(results)

    detections_file = Path(detector.save_dir) / "detections.json"
    summary_file = Path(detector.save_dir) / "summary.json"

    assert detections_file.exists()
    assert summary_file.exists()

    detections = json.loads(detections_file.read_text())
    summary = json.loads(summary_file.read_text())

    assert detections == results
    assert summary["total_images"] == 2
    assert summary["total_detections"] == 1
    assert summary["avg_detections_per_image"] == 0.5


def test_edge_aware_filter_relaxes_thresholds_near_edges():
    """edge_aware_filter should allow slightly lower scores near image edges."""

    boxes = np.array(
        [
            [1, 1, 21, 21],  # very close to edge
            [40, 40, 60, 60],  # centered
        ],
        dtype=np.float32,
    )
    scores = np.array([0.55, 0.55], dtype=np.float32)

    keep_mask, dyn_thr = det_stage_mod.edge_aware_filter(
        boxes,
        scores,
        img_wh=(100, 100),
        base_conf=0.6,
        edge_band_rel=0.2,
        min_factor=0.5,
        taper_rel=0.4,
    )

    assert keep_mask.dtype == bool
    assert bool(keep_mask[0]) is True  # lowered threshold keeps edge box
    assert bool(keep_mask[1]) is False  # center box must meet base conf
    assert dyn_thr[0] < dyn_thr[1]
