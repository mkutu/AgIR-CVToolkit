from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, field_validator

SortDir = Literal["asc", "desc"]

class QuerySpec(BaseModel):
    """
    Query spec for the single cutouts table.
    - filters: dict of either mini-DSL strings or values (lists/scalars/ranges)
    - projection: None means "all DB columns"
    - sort/limit/offset: deterministic paging; default ORDER BY cutout_id asc
    - expand: reserved (no-op for single-table cutouts, keeps API stable)
    """
    filters: Dict[str, Any] = Field(default_factory=dict)
    projection: Optional[List[str]] = None
    sort: Optional[List[Tuple[str, SortDir]]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    expand: Dict[str, bool] = Field(default_factory=dict)
    sample: Optional[dict] = None
    # sample schema (documented):
    # {
    #   "strategy": "random" | "seeded" | "stratified",
    #   "n": 200,                       # total rows (random/seeded),
    #   "seed": 42,                     # for "seeded",
    #   "by": ["category_common_name"], # for "stratified"
    #   "per_group": 10,                # fixed count per group
    # }

    @field_validator("sort")
    @classmethod
    def _validate_sort(cls, v):
        if v:
            for _, d in v:
                if d not in ("asc", "desc"):
                    raise ValueError("sort dir must be 'asc' or 'desc'")
        return v


@dataclass
class ImageRecord:
    """
    One cutout row + convenience absolute paths.
    - extras: a 1:1 mapping of all DB columns (complete row)
    - image_path/mask_path: absolute if resolvable
    - aux_paths: absolute variants of other *_path columns (json/cutout/etc.)
    """
    cutout_id: str
    image_id: Optional[str] = None

    image_path: Optional[Path] = None
    mask_path: Optional[Path] = None
    json_path: Optional[Path] = None
    aux_paths: Dict[str, Path] = field(default_factory=dict)

    extras: Dict[str, Any] = field(default_factory=dict)
