from datetime import datetime
import hashlib, json
from pathlib import Path
from typing import Optional
from omegaconf import DictConfig
        
def make_run_id(stage: str, dataset: str, cfg: dict, seed: int | None = None) -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # hash only the bits that change behavior
    material_cfg = {k: cfg[k] for k in sorted(cfg) if k not in ("logging", "paths")}
    # save this to a json for testing
    with open("make_run_id_cfg.json", "w") as f:
        json.dump(material_cfg, f, indent=4)
    h = hashlib.md5(json.dumps(material_cfg, sort_keys=True).encode()).hexdigest()[:6]
    tail = f"seed{seed}" if seed is not None else f"h={h}"
    return f"{ts}__{stage}__{dataset}__{tail}"
