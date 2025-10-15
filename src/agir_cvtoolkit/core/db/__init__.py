# src/agir_cvtoolkit/core/db/__init__.py
"""
Unified database interface for AgIR CV Toolkit.
"""
from .agir_db import AgirDB, QueryBuilder
from .types import QuerySpec, ImageRecord, SortDir

__all__ = [
    "AgirDB",
    "QueryBuilder", 
    "QuerySpec",
    "ImageRecord",
    "SortDir",
]