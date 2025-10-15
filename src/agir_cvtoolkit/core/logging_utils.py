import logging, sys
from omegaconf import DictConfig
import datetime
from pathlib import Path

FMT = "[%(asctime)s][%(name)s][%(levelname)s] - %(message)s"
def setup_logging(cfg: DictConfig, level: str = "INFO"):
    # add a epoch datetime to the log file name
    timestamp = datetime.datetime.now()
    epoch = int(timestamp.timestamp())
    log_path = Path(cfg.get("paths", {}).get("logs", "./outputs/logs")) / f"{epoch}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # log_dir = Path(cfg.get("paths", {}).get("logs", "./outputs/logs"))
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter(FMT))

    if not log_path.parent.exists():
        log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.touch()
    fh = logging.FileHandler(log_path)
    fh.setFormatter(logging.Formatter(FMT))
    h.setLevel(level)
    fh.setLevel(level)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(h)
    root.addHandler(fh)
    root.setLevel(level)
