# src/agir_cvtoolkit/pipeline/hydra_utils.py
from __future__ import annotations
from pathlib import Path
from omegaconf import DictConfig, OmegaConf, MISSING
from datetime import datetime
import hashlib, json, socket, getpass, subprocess
import yaml


VOLATILE_KEYS = {"working_dir", "runtime", "paths"}  # don't hash these    

def read_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)
    
def _to_resolved_dict(cfg: DictConfig) -> dict:
    """Resolve all interpolations and convert to plain dict."""
    return OmegaConf.to_container(cfg, resolve=True, enum_to_str=True)  # type: ignore

def _material_cfg_dict(resolved: dict) -> dict:
    """Strip volatile/runtime keys before hashing to get a stable 'behavior' hash."""
    def _strip(d: dict) -> dict:
        out = {}
        for k, v in d.items():
            if k in VOLATILE_KEYS:
                continue
            if isinstance(v, dict):
                out[k] = _strip(v)
            else:
                out[k] = v
        return out
    return _strip(resolved)

def _config_hash(material: dict, n: int = 8) -> str:
    s = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return hashlib.md5(s.encode()).hexdigest()[:n]

def _git_commit() -> str | None:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode().strip()
    except Exception:
        return None
    
def _make_run_id(proj_dir: str, sub_proj_dir: str, dataset: str, cfg_hash: str, seed: int | None) -> str:

    if proj_dir and sub_proj_dir:
        return f"{proj_dir}/{sub_proj_dir}"
    
    elif proj_dir:
        return f"{proj_dir}"
    else:
        tail = f"seed{seed}" if seed is not None else f"h={cfg_hash}"
        return f"{tail}"

def _prune_nulls(obj):
    """Recursively drop keys whose value is None or MISSING so they don't overwrite prior values."""
    if isinstance(obj, DictConfig):
        obj = OmegaConf.to_container(obj, resolve=False)
    if isinstance(obj, dict):
        return {k: _prune_nulls(v)
                for k, v in obj.items()
                if v is not None and v is not MISSING}
    elif isinstance(obj, list):
        return [_prune_nulls(v) for v in obj if v is not None and v is not MISSING]
    else:
        return obj

def load_cfg_if_exists(path: Path) -> DictConfig | None:
    if path.exists():
        return OmegaConf.load(path)
    return None

def merge_preserving_existing(old_cfg: DictConfig, new_cfg: DictConfig) -> DictConfig:
    """
    Merge new_cfg INTO old_cfg, but ignore null/MISSING values from new_cfg so they don't wipe old values.
    Returns a fresh DictConfig.
    """
    pruned_new = _prune_nulls(new_cfg)
    # OmegaConf.merge returns a new cfg; order matters: later args override earlier ones
    merged = OmegaConf.merge(old_cfg, pruned_new)
    return merged


def finalize_cfg(cfg: DictConfig, *, stage: str, dataset: str, cli_overrides: list[str] | None) -> DictConfig:
    """
    Enrich cfg with:
      - runtime: user, host, timestamps, git_commit, cli_overrides
      - paths: out_root, run_root, subdirs, cfg_path
      - hash: config hash (sans volatile keys)
      - run_id: canonical run identifier
    """
    # Ensure required io keys exist
    out_root = Path(str(cfg.get("io", {}).get("out_root", "./outputs"))).expanduser()
    out_root.mkdir(parents=True, exist_ok=True)

    resolved = _to_resolved_dict(cfg)
    material = _material_cfg_dict(resolved)
    cfg_hash = _config_hash(material)

    # Seed: look in common places; adjust as needed
    seed = resolved.get("seed", None)

    project_name = resolved.get("project", {}).get("name", None)
    sub_project_name = resolved.get("project", {}).get("subname", None)
    run_id = _make_run_id(proj_dir=project_name, sub_proj_dir=sub_project_name,
                          dataset=dataset, cfg_hash=cfg_hash, seed=seed)
    run_root = out_root / run_id

    # Subdirs
    sub = {
        "logs": run_root / "logs",
        "query": run_root / "query",
        "images": run_root / "images",
        "masks": run_root / "masks",
        "cutouts": run_root / "cutouts",
        "plots": run_root / "plots",
        "cvat_downloads": run_root / "cvat_downloads",  # ADD THIS LINE
        "preprocessed": run_root / "preprocessed",
    }
    for p in [run_root, *sub.values()]:
        p.mkdir(parents=True, exist_ok=True)

    # ---- Load previous cfg (if any) and merge, ignoring nulls from current stage
    # cfg_path = run_root / "cfg.yaml"
    # prev_cfg = load_cfg_if_exists(cfg_path)
    # if prev_cfg is not None:
    #     cfg = merge_preserving_existing(prev_cfg, cfg)

    # Attach runtime + paths
    cfg.runtime = {
        "stage": stage,
        "dataset": dataset,
        "created_local": datetime.now().isoformat(timespec="seconds"),
        "user": getpass.getuser(),
        "host": socket.gethostname(),
        "git_commit": _git_commit(),
        "cli_overrides": cli_overrides or [],
        "hash": cfg_hash,
        "run_id": run_id,
    }
    cfg.paths = {
        "out_root": str(out_root),
        "run_root": str(run_root),
        "logs": str(sub["logs"]),
        "query": str(sub["query"]),
        "images": str(sub["images"]),
        "masks": str(sub["masks"]),
        "cutouts": str(sub["cutouts"]),
        "plots": str(sub["plots"]),
        "cvat_downloads": str(sub["cvat_downloads"]),
        "preprocessed": str(sub["preprocessed"]),
        "cfg_path": str(run_root / "cfg.yaml"),
        "metrics_path": str(run_root / "metrics.json"),
        "manifest_path": str(run_root / "manifest.csv"),  # CHANGED: .jsonl -> .csv
    }

    # Setup logging dir
    cfg.train.logger.csv.save_dir = cfg.paths.logs
    cfg.train.logger.wandb.save_dir = cfg.paths.logs
    cfg.train.logger.wandb.name = cfg.runtime.run_id

    # Persist the frozen cfg for reproducibility (after we enriched it)
    cfg_path = Path(cfg.paths["cfg_path"])
    with open(cfg_path, "w") as f:
        OmegaConf.save(config=cfg, f=f.name, resolve=True)

    # Touch metrics + manifest files
    Path(cfg.paths["metrics_path"]).write_text("{}")
    Path(cfg.paths["manifest_path"]).touch()

    return cfg
