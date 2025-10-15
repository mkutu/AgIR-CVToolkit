"""
Unified, fluent database interface for AgIR CV Toolkit.

Usage:
    # Simple filtering
    db = AgirDB.connect("semif", sqlite_path="data.db")
    records = db.filter(category_common_name="barley").limit(10).execute()
    
    # Complex stratified sampling
    records = db.sample_stratified(
        by=["category_common_name", "area_bin"],
        per_group=10
    ).execute()
    
    # Raw expressions
    records = db.where("estimated_bbox_area_cm2 > 100").sort("datetime").execute()
    
    # Count records
    count = db.filter(state="NC").count()
"""
from __future__ import annotations
import logging
import sqlite3
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterator, List, Optional, Tuple, Literal

from .types import ImageRecord, QuerySpec
from .filters import build_where, filters_to_exprs, build_order, build_limit_offset
from .filters import seeded_order_sql, random_order_sql

log = logging.getLogger(__name__)

DBType = Literal["semif", "field"]


class QueryBuilder:
    """Fluent interface for building queries."""
    
    def __init__(self, db: AgirDB):
        self._db = db
        self._filters: Dict[str, Any] = {}
        self._projection: Optional[List[str]] = None
        self._sort: List[Tuple[str, str]] = []
        self._limit_val: Optional[int] = None
        self._offset_val: Optional[int] = None
        self._sample_spec: Optional[dict] = None
    
    def filter(self, **kwargs) -> QueryBuilder:
        """Add equality filters. Can be called multiple times (values are merged)."""
        for k, v in kwargs.items():
            if k in self._filters:
                # Merge values into list
                existing = self._filters[k]
                if not isinstance(existing, list):
                    existing = [existing]
                if isinstance(v, list):
                    existing.extend(v)
                else:
                    existing.append(v)
                # Deduplicate while preserving order
                seen = set()
                merged = []
                for x in existing:
                    key = x.lower() if isinstance(x, str) else x
                    if key not in seen:
                        seen.add(key)
                        merged.append(x)
                self._filters[k] = merged if len(merged) > 1 else merged[0]
            else:
                self._filters[k] = v
        return self
    
    def where(self, expr: str) -> QueryBuilder:
        """Add a raw SQL-like expression (mini-DSL)."""
        self._filters.setdefault("$raw", []).append(expr)
        return self
    
    def select(self, *columns: str) -> QueryBuilder:
        """Specify columns to return (default: all)."""
        if self._projection is None:
            self._projection = []
        self._projection.extend(columns)
        return self
    
    def sort(self, column: str, direction: str = "asc") -> QueryBuilder:
        """Add sort order."""
        direction = direction.lower()
        if direction not in ("asc", "desc"):
            raise ValueError(f"Sort direction must be 'asc' or 'desc', got {direction!r}")
        self._sort.append((column, direction))
        return self
    
    def limit(self, n: int) -> QueryBuilder:
        """Limit result count."""
        self._limit_val = n
        return self
    
    def offset(self, n: int) -> QueryBuilder:
        """Skip first N results."""
        self._offset_val = n
        return self
    
    def sample_random(self, n: int) -> QueryBuilder:
        """Take a random sample of N records (after filtering)."""
        self._sample_spec = {"strategy": "random", "n": n}
        return self
    
    def sample_seeded(self, n: int, seed: int = 42) -> QueryBuilder:
        """Take a deterministic pseudo-random sample of N records."""
        self._sample_spec = {"strategy": "seeded", "n": n, "seed": seed}
        return self
    
    def sample_stratified(
        self,
        by: List[str],
        per_group: int,
        seed: Optional[int] = None
    ) -> QueryBuilder:
        """Take per_group random records from each unique combination of 'by' columns."""
        spec = {"strategy": "stratified", "by": by, "per_group": per_group}
        if seed is not None:
            spec["seed"] = seed
        self._sample_spec = spec
        return self
    
    def to_spec(self) -> QuerySpec:
        """Convert to a QuerySpec for direct use."""
        return QuerySpec(
            filters=self._filters,
            projection=self._projection,
            sort=self._sort or None,
            limit=self._limit_val,
            offset=self._offset_val,
            sample=self._sample_spec,
        )
    
    def execute(self) -> Iterator[ImageRecord]:
        """Execute the query and return an iterator of records."""
        return self._db.query(self.to_spec())
    
    def all(self) -> List[ImageRecord]:
        """Execute and materialize all results into a list."""
        return list(self.execute())
    
    def first(self) -> Optional[ImageRecord]:
        """Execute and return the first result, or None."""
        for rec in self.execute():
            return rec
        return None
    
    def count(self) -> int:
        """Count matching records without fetching them."""
        return self._db.count(self.to_spec())


class AgirDB:
    """
    Unified database interface for SemiF and Field databases.
    
    Provides a clean, fluent API for common operations while maintaining
    flexibility for complex queries.
    """
    
    def __init__(
        self,
        db_type: DBType,
        sqlite_path: Path,
        table: str,
        id_column: str = "cutout_id"
    ):
        self.db_type = db_type.lower()
        self.sqlite_path = Path(sqlite_path)
        self.table = table
        self.id_column = id_column
        
        if not self.sqlite_path.exists():
            raise FileNotFoundError(f"Database not found: {self.sqlite_path}")
        
        self._conn: Optional[sqlite3.Connection] = None
    
    @classmethod
    def connect(
        cls,
        db_type: DBType,
        sqlite_path: str | Path,
        table: Optional[str] = None
    ) -> AgirDB:
        """
        Factory method to create a database connection.
        
        Args:
            db_type: "semif" or "field"
            sqlite_path: Path to SQLite database
            table: Table name (defaults: "semif" for semif, "records" for field)
        """
        db_type = db_type.lower()
        if table is None:
            table = "semif" if db_type == "semif" else "records"
        
        id_col = "cutout_id" if db_type == "semif" else "id"
        
        return cls(db_type, Path(sqlite_path), table, id_col)
    
    def get_by_image_id(self, image_id: str) -> Optional[ImageRecord]:
        """Get a single record by image_id (if applicable)."""
        if self.db_type != "semif":
            raise NotImplementedError("get_by_image_id is only supported for 'semif' databases")
        
        spec = QuerySpec(filters={"image_id": image_id}, limit=1)
        for rec in self.query(spec):
            return rec
        return None
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.sqlite_path))
            self._conn.row_factory = sqlite3.Row
            # Performance pragmas
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
        return self._conn
    
    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __enter__(self) -> AgirDB:
        return self
    
    def __exit__(self, *args) -> None:
        self.close()
    
    # ---------- Fluent Query Interface ----------
    
    def builder(self) -> QueryBuilder:
        """Get a new query builder (useful for programmatic construction)."""
        return QueryBuilder(self)
    
    def filter(self, **kwargs) -> QueryBuilder:
        """Start a query with equality filters."""
        return QueryBuilder(self).filter(**kwargs)
    
    def where(self, expr: str) -> QueryBuilder:
        """Start a query with a raw expression."""
        return QueryBuilder(self).where(expr)
    
    def select(self, *columns: str) -> QueryBuilder:
        """Start a query with column selection."""
        return QueryBuilder(self).select(*columns)
    
    def all(self) -> List[ImageRecord]:
        """Get all records (no filters)."""
        return QueryBuilder(self).all()
    
    def sample_random(self, n: int) -> QueryBuilder:
        """Start a query with random sampling."""
        return QueryBuilder(self).sample_random(n)
    
    def sample_seeded(self, n: int, seed: int = 42) -> QueryBuilder:
        """Start a query with seeded sampling."""
        return QueryBuilder(self).sample_seeded(n, seed)
    
    def sample_stratified(
        self,
        by: List[str],
        per_group: int,
        seed: Optional[int] = None
    ) -> QueryBuilder:
        """Start a query with stratified sampling."""
        return QueryBuilder(self).sample_stratified(by, per_group, seed)
    
    # ---------- Direct Query Methods ----------
    
    def query(self, spec: QuerySpec) -> Iterator[ImageRecord]:
        """Execute a QuerySpec and return an iterator of records."""
        t0 = perf_counter()
        rows_scanned = rows_returned = rows_invalid = 0
        
        con = self._get_connection()
        
        # Discover columns if no projection provided
        if not spec.projection:
            cols = [r[1] for r in con.execute(f"PRAGMA table_info({self.table})")]
            projection_cols = cols[:]
        else:
            projection_cols = spec.projection[:]
        
        # Ensure ID column is always present
        if self.id_column not in projection_cols:
            projection_cols.insert(0, self.id_column)
        
        # Build WHERE clause
        where_sql, params = build_where(filters_to_exprs(spec.filters))
        
        # Handle sampling strategies
        sample = spec.sample or {}
        strategy = sample.get("strategy", "none").lower()
        
        base_sql = f"SELECT {', '.join(projection_cols)} FROM {self.table}{where_sql}"
        
        if strategy == "random":
            n = int(sample.get("n", spec.limit or 0))
            if n <= 0:
                raise ValueError("sample.random requires 'n' > 0")
            sql = f"{base_sql}{random_order_sql()} LIMIT ?"
            bound = params + (n,)
        
        elif strategy == "seeded":
            n = int(sample.get("n", spec.limit or 0))
            if n <= 0:
                raise ValueError("sample.seeded requires 'n' > 0")
            seed = int(sample.get("seed", 0))
            sql = f"{base_sql}{seeded_order_sql(':seed')} LIMIT ?"
            bound = params + (seed, n)
        
        elif strategy == "stratified":
            by_cols = sample.get("by", [])
            if not by_cols:
                raise ValueError("sample.stratified requires 'by': [col,...]")
            k = int(sample.get("per_group", 0))
            if k <= 0:
                raise ValueError("sample.stratified requires 'per_group' > 0")
            
            partition = ", ".join(by_cols)
            inner = (
                f"SELECT {', '.join(projection_cols)}, "
                f"ROW_NUMBER() OVER (PARTITION BY {partition} ORDER BY RANDOM()) AS __rn "
                f"FROM {self.table}{where_sql}"
            )
            sql = f"SELECT * FROM ({inner}) WHERE __rn <= ?"
            bound = params + (k,)
            
            # Apply limit/offset if specified
            if spec.limit is not None or spec.offset is not None:
                lim_sql, lim_params = build_limit_offset(spec.limit, spec.offset)
                sql = f"SELECT * FROM ({sql}){lim_sql}"
                bound = bound + lim_params
        
        else:
            # Normal query with optional ORDER BY and LIMIT/OFFSET
            order_sql = build_order(spec.sort) if spec.sort else f" ORDER BY {self.id_column} ASC"
            lim_sql, lim_params = build_limit_offset(spec.limit, spec.offset)
            sql = f"{base_sql}{order_sql}{lim_sql}"
            bound = params + lim_params
        
        # Execute and stream results
        cur = con.execute(sql, bound)
        for row in cur:
            rows_scanned += 1
            try:
                rec = self._row_to_record(row)
                rows_returned += 1
                yield rec
            except Exception as e:
                rows_invalid += 1
                log.warning("Invalid row id=%s err=%s", row.get(self.id_column), e)
        
        ms = int((perf_counter() - t0) * 1000)
        log.info(
            "Query stats (%s): rows_scanned=%d rows_returned=%d rows_invalid=%d query_ms=%d",
            self.db_type, rows_scanned, rows_returned, rows_invalid, ms
        )
    
    def get(self, record_id: str) -> Optional[ImageRecord]:
        """Get a single record by ID."""
        spec = QuerySpec(filters={self.id_column: record_id}, limit=1)
        for rec in self.query(spec):
            return rec
        return None
    
    def count(self, spec: Optional[QuerySpec] = None) -> int:
        """Count records matching the query spec."""
        if spec is None:
            spec = QuerySpec()
        
        con = self._get_connection()
        where_sql, params = build_where(filters_to_exprs(spec.filters))
        sql = f"SELECT COUNT(*) FROM {self.table}{where_sql}"
        result = con.execute(sql, params).fetchone()
        return result[0] if result else 0
    
    def preview(self, spec: Optional[QuerySpec] = None, n: int = 10) -> List[ImageRecord]:
        """Quick preview of N records."""
        if spec is None:
            spec = QuerySpec(limit=n)
        else:
            spec = spec.model_copy()
            spec.limit = min(n, spec.limit or n)
        return list(self.query(spec))
    
    # ---------- Internal Helpers ----------
    
    def _row_to_record(self, row: sqlite3.Row) -> ImageRecord:
        """Convert a row to an ImageRecord (DB-specific logic)."""
        data = {k: row[k] for k in row.keys()}
        
        if self.db_type == "semif":
            return self._semif_row_to_record(data)
        elif self.db_type == "field":
            return self._field_row_to_record(data)
        else:
            raise ValueError(f"Unknown db_type: {self.db_type}")
    
    def _semif_row_to_record(self, data: dict) -> ImageRecord:
        """Convert SemiF row to ImageRecord."""
        aux_paths: Dict[str, Path] = {}
        for col in ("cutout_path", "cutout_mask_path", "cutout_json_path", "cropout_path"):
            p = data.get(col)
            if p:
                aux_paths[col] = Path(p)
        
        return ImageRecord(
            cutout_id=str(data.get("cutout_id")),
            image_id=str(data.get("image_id")) if data.get("image_id") else None,
            image_path=Path(data["image_path"]) if data.get("image_path") else None,
            mask_path=Path(data["mask_path"]) if data.get("mask_path") else None,
            json_path=Path(data["json_path"]) if data.get("json_path") else None,
            aux_paths=aux_paths,
            extras=data,
        )
    
    def _field_row_to_record(self, data: dict) -> ImageRecord:
        """Convert Field row to ImageRecord."""
        # Choose best image path
        image_path = (
            data.get("developed_image_path")
            or data.get("raw_image_path")
            or data.get("cutout_image_path")
            or data.get("final_cutout_path")
        )
        
        aux_candidates = [
            "raw_image_path",
            "developed_image_path",
            "cutout_image_path",
            "final_cutout_path",
            "final_mask_path",
        ]
        aux_paths: Dict[str, Path] = {}
        for col in aux_candidates:
            p = data.get(col)
            if p:
                aux_paths[col] = Path(p)
        
        return ImageRecord(
            cutout_id=str(data.get("id")),
            image_id=str(data.get("image_id")) if data.get("image_id") else None,
            image_path=Path(image_path) if image_path else None,
            mask_path=Path(data["final_mask_path"]) if data.get("final_mask_path") else None,
            json_path=None,
            aux_paths=aux_paths,
            extras=data,
        )