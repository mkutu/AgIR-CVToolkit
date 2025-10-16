from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Optional, List

import pandas as pd
from omegaconf import DictConfig

from agir_cvtoolkit.core.db import AgirDB
from agir_cvtoolkit.pipelines.utils.query_parse import _parse_repeatable_filters
from agir_cvtoolkit.pipelines.utils.serializers import (
    _rec_to_dict, 
    _parse_sort, 
    _parse_sample
)

import logging
log = logging.getLogger(__name__)

def save_records_as_dataframe(projection, out, out_path, recs_iter):
    """Save records as CSV or Parquet."""
    rows = [_rec_to_dict(r) for r in (recs_iter if isinstance(recs_iter, list) else list(recs_iter))]
    df = pd.DataFrame(rows)
    
    if projection:
        proj_cols = [c.strip() for c in projection.split(",") if c.strip()]
        ordered = [c for c in proj_cols if c in df.columns] + [
            c for c in df.columns if c not in proj_cols
        ]
        df = df[ordered]
    
    if out == "csv":
        df.to_csv(out_path, index=False, quoting=csv.QUOTE_MINIMAL, escapechar="\\")
    else:
        df.to_parquet(out_path, index=False)

def save_records_to_json(out_path: Path, recs_iter):
    """Save records as JSON."""
    with out_path.open("w") as f:
        if isinstance(recs_iter, list):
            json.dump([_rec_to_dict(r) for r in recs_iter], f, indent=2)
        else:
            f.write("[\n")
            first = True
            for r in recs_iter:
                f.write(("" if first else ",\n") + json.dumps(_rec_to_dict(r)))
                first = False
            f.write("\n]\n")

def _save_query_spec(
    out_path: Path,
    db: str,
    filters: Optional[List[str]],
    projection: Optional[str],
    sort: Optional[str],
    limit: Optional[int],
    offset: Optional[int],
    sample: Optional[str],
    cfg: DictConfig,
) -> None:
    """Save the query specification to a JSON file for reproducibility."""
    from datetime import datetime
    
    # Parse filters for better readability
    from agir_cvtoolkit.pipelines.utils.query_parse import _parse_repeatable_filters
    parsed_filters = _parse_repeatable_filters(filters or []) if filters else {}
    
    # Parse sort
    parsed_sort = _parse_sort(sort) if sort else None
    
    # Parse sample
    parsed_sample = _parse_sample(sample) if sample else None
    
    query_spec = {
        "query_metadata": {
            "run_id": cfg['runtime']['run_id'],
            "timestamp": datetime.now().isoformat(),
            "user": cfg['runtime']['user'],
            "host": cfg['runtime']['host'],
            "git_commit": cfg['runtime'].get('git_commit'),
        },
        "database": {
            "type": db,
            "db_path": str(cfg.get("db", {}).get(db.lower(), {}).get("db_path")),
            "table": cfg.get("db", {}).get(db.lower(), {}).get("table"),
        },
        "query_parameters": {
            "filters": {
                "raw": filters or [],
                "parsed": parsed_filters,
            },
            "projection": projection.split(",") if projection else None,
            "sort": {
                "raw": sort,
                "parsed": parsed_sort,
            },
            "limit": limit,
            "offset": offset,
            "sample": {
                "raw": sample,
                "parsed": parsed_sample,
            },
        },
        "execution": {
            "preview_mode": cfg.get("query", {}).get("preview", 0) > 0,
            "preview_count": cfg.get("query", {}).get("preview", 0),
            "output_format": cfg.get("query", {}).get("out", "json"),
        },
    }
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(query_spec, f, indent=2)
    
    log.info(f"Query specification saved to: {out_path}")

def run_query(
    cfg: DictConfig,
    db: str,
    *,
    filters: Optional[List[str]],
    projection: Optional[str],
    sort: Optional[str],
    limit: Optional[int],
    offset: Optional[int],
    out: str,
    preview: int,
    sample: Optional[str],
) -> None:
    """Simplified query runner using unified AgirDB."""
    
    # Connect to database
    db_cfg = cfg.get("db", {}).get(db.lower())
    agir_db = AgirDB.connect(
        db_type=db.lower(),
        db_path=Path(db_cfg["db_path"]),
        table=db_cfg.get("table")
    )
    
    # Build query using fluent interface
    # Start with an empty builder so we always have .execute()
    query = agir_db.builder()
    
    # Apply filters
    if filters:
        fdict = _parse_repeatable_filters(filters)
        
        # Handle raw expressions separately
        raw_exprs = fdict.pop("$raw", [])
        for expr in raw_exprs:
            query = query.where(expr)
        
        # Apply regular filters
        if fdict:
            query = query.filter(**fdict)
    
    # Apply projection
    if projection:
        cols = [c.strip() for c in projection.split(",") if c.strip()]
        query = query.select(*cols)
    
    # Apply sorting
    if sort:
        for col, direction in _parse_sort(sort):
            query = query.sort(col, direction)
    
    # Apply sampling
    if sample:
        sample_dict = _parse_sample(sample)
        strategy = sample_dict.get("strategy", "").lower()
        
        if strategy == "random":
            query = query.sample_random(sample_dict.get("n", limit or 100))
        elif strategy == "seeded":
            query = query.sample_seeded(
                sample_dict.get("n", limit or 100),
                sample_dict.get("seed", 42)
            )
        elif strategy == "stratified":
            query = query.sample_stratified(
                by=sample_dict.get("by", []),
                per_group=sample_dict.get("per_group", 10)
            )
    
    # Apply limit/offset
    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)

    # Save query specification BEFORE executing
    query_spec_path = Path(cfg['paths']['query']) / "query_spec.json"
    _save_query_spec(
        query_spec_path,
        db=db,
        filters=filters,
        projection=projection,
        sort=sort,
        limit=limit,
        offset=offset,
        sample=sample,
        cfg=cfg,
    )
    
    # Execute query
    if preview > 0:
        recs = query.preview(n=preview)
        # agir_db.preview(query, n=preview)
        recs = query.execute()
    else:
        recs = query.execute()

    # Output results
    out_path = Path(cfg['paths']['query']) / f"query.{out}"
    
    if out == "json":
        save_records_to_json(out_path, recs)
    elif out in ("csv", "parquet"):
        save_records_as_dataframe(projection, out, out_path, recs)
    
    agir_db.close()

