# src/agir_cvtoolkit/cli.py
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer
from hydra import compose, initialize_config_module
from omegaconf import DictConfig, OmegaConf

from .core.logging_utils import setup_logging
from .pipelines.stages.query import run_query
from .pipelines.stages.seg_infer import SegmentationInferenceStage
from .pipelines.utils.hydra_utils import finalize_cfg

app = typer.Typer(help="AgIR CV Toolkit CLI", pretty_exceptions_show_locals=False)


def _compose_cfg(config_name: str = "config", overrides: Optional[List[str]] = None) -> DictConfig:
    """
    Centralized Hydra composition so every command uses the same behavior.
    - Looks for configs in the Python package module: `agir_cvtoolkit.conf`
    - Injects a runtime working_dir into the config
    """
    with initialize_config_module(
        config_module="agir_cvtoolkit.conf",
        job_name="agir_cvtoolkit",
        version_base="1.3",
    ):
        cfg = compose(config_name=config_name, overrides=overrides or [])
        cfg["working_dir"] = str(Path.cwd())
    return cfg

@app.command()
def query(
    config: str = typer.Option("config", help="Hydra config name (without .yaml)"),
    override: List[str] = typer.Option(
        None, "--override", "-o", help="Hydra override (repeatable)"
    ),
    db: Optional[str] = typer.Option(
        "semif", "--db", "-d", help="semif|field database (default: semif)"
    ),
    # passthrough args to the query runner:
    filters: List[str] = typer.Option(
        None, "--filters", "-f", help="Repeatable filter (mini-DSL or JSON)"
    ),
    projection: Optional[str] = typer.Option(
        None, help="Comma-separated columns; omit for ALL"
    ),
    sort: Optional[str] = typer.Option(
        None, help='Comma list like "datetime:desc,cutout_id:asc"'
    ),
    limit: Optional[int] = typer.Option(None),
    offset: Optional[int] = typer.Option(None),
    out: str = typer.Option("csv", help="json|csv|parquet"),
    preview: int = typer.Option(0, help="If >0, show first N via preview()"),
    sample: Optional[str] = typer.Option(
        None,
        help='Sampling spec, e.g. "random:n=200" or "seeded:n=200,seed=42" or "stratified:by=category_common_name,per_group=10"',
    ),
):
    """
    Query the AgIR DB and write JSON/CSV/Parquet (or stream JSON to stdout).
    All actual work lives in commands/query.py to keep this entrypoint clean.
    """
    # Compose cfg first so we can inject CLI args as overrides
    cfg = _compose_cfg(config_name=config, overrides=override)
    # Populate the "query" key in cfg with all the parsed values
    cfg["query"] = {
        "filters": filters or [],
        "db": db,
        "projection": projection,
        "sort": sort,
        "limit": limit,
        "offset": offset or None,
        "out": out or "json",
        "preview": preview or 0,
        "sample": sample
    }
    # Finalize cfg (adds runtime, paths, run_id, hash, etc)
    cfg = OmegaConf.to_container(
        finalize_cfg(cfg, stage="query", dataset=db or "unknown", cli_overrides=override),
        resolve=True
    )

    setup_logging(cfg)  # consistent logging
    # Run the query
    run_query(
        cfg=cfg,
        db=db,
        filters=filters,
        projection=projection,
        sort=sort,
        limit=limit,
        offset=offset,
        out=out,
        preview=preview,
        sample=sample,
    )
    typer.echo(f"Query run complete: {cfg['runtime']['run_id']}\n• run_root: {cfg['paths']['run_root']}")

@app.command("infer-seg")
def infer_seg(
    config: str = typer.Option("config", help="Hydra config name (without .yaml)"),
    override: List[str] = typer.Option(None, "--override", "-o", help="Hydra overrides"),
):
    """Run segmentation inference pipeline."""
    cfg = _compose_cfg(config, override)
    cfg = finalize_cfg(
        cfg,
        stage="infer_seg",
        dataset=cfg.get("seg_inference", {}).get("source", {}).get("db", "semif"), 
        cli_overrides=override
    )

    setup_logging(cfg)
    from agir_cvtoolkit.pipelines.stages.seg_infer import SegmentationInferenceStage
    SegmentationInferenceStage(cfg).run()
    
    typer.echo(f"Segmentation inference complete\nrun_id: {cfg['runtime']['run_id']}\nrun_root: {cfg['paths']['run_root']}")

@app.command("upload-cvat")
def upload_cvat(
    config: str = typer.Option("config", help="Hydra config name (without .yaml)"),
    override: List[str] = typer.Option(None, "--override", "-o", help="Hydra overrides"),
):
    """Upload annotations to CVAT (detections or segmentations)."""
    cfg = _compose_cfg(config, override)
    cfg = finalize_cfg(
        cfg,
        stage="upload_cvat",
        dataset=cfg.get("cvat_upload", {}).get("source", {}).get("db", "semif"),
        cli_overrides=override
    )

    setup_logging(cfg)
    from agir_cvtoolkit.pipelines.stages.cvat_upload import CVATUploadStage
    CVATUploadStage(cfg).run()
    
    typer.echo(
        f"CVAT upload complete\n"
        f"run_id: {cfg['runtime']['run_id']}\n"
        f"run_root: {cfg['paths']['run_root']}"
    )

@app.command("download-cvat")
def download_cvat(
    config: str = typer.Option("config", help="Hydra config name (without .yaml)"),
    override: List[str] = typer.Option(None, "--override", "-o", help="Hydra overrides"),
):
    """Download annotations from CVAT (with task filtering)."""
    cfg = _compose_cfg(config, override)
    cfg = finalize_cfg(
        cfg,
        stage="download_cvat",
        dataset="cvat",
        cli_overrides=override
    )

    setup_logging(cfg)
    from agir_cvtoolkit.pipelines.stages.cvat_download import CVATDownloadStage
    CVATDownloadStage(cfg).run()
    
    typer.echo(
        f"CVAT download complete\n"
        f"run_id: {cfg['runtime']['run_id']}\n"
        f"run_root: {cfg['paths']['run_root']}"
    )

@app.command("train")
def train(
    config: str = typer.Option("config", help="Hydra config name (without .yaml)"),
    override: List[str] = typer.Option(None, "--override", "-o", help="Hydra overrides"),
):
    """Train a segmentation model using PyTorch Lightning."""
    cfg = _compose_cfg(config, override)
    cfg = finalize_cfg(
        cfg,
        stage="train",
        dataset=cfg.get("train", {}).get("dataset", "field"),
        cli_overrides=override
    )
    
    setup_logging(cfg)
    from agir_cvtoolkit.pipelines.stages.train import TrainingStage
    TrainingStage(cfg).run()
    
    typer.echo(
        f"Training complete\n"
        f"run_id: {cfg['runtime']['run_id']}\n"
        f"run_root: {cfg['paths']['run_root']}"
    )

if __name__ == "__main__":
    app()