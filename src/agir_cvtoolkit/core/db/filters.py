from __future__ import annotations
import ast
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

IN_CHUNK = 1000  # max params per IN clause

DEFAULT_ID_COL = "cutout_id"


@dataclass
class SqlWhere:
    sql: str
    params: Tuple[Any, ...]

_rx_null = __import__("re").compile(r"^\s*(?P<key>\w+)\s+is\s+(?P<neg>not\s+)?null\s*$", __import__("re").IGNORECASE)
_rx_range = __import__("re").compile(r"^\s*(?P<key>\w+)\s*(?:in|between)\s*\[(?P<lo>.+?),(?P<hi>.+?)\]\s*$", __import__("re").IGNORECASE)
_rx_bin = __import__("re").compile(r"^\s*(?P<key>\w+)\s*(?P<op>==|>=|<=|>|<)\s*(?P<rhs>.+?)\s*$")
_rx_range2 = __import__("re").compile(
    r"^\s*(?P<key>\w+)\s*between\s+(?P<lo>.+?)\s+and\s+(?P<hi>.+?)\s*$",
    __import__("re").IGNORECASE
)

def _lit(text: str):
    text = text.strip()
    try:
        return ast.literal_eval(text)
    except Exception:
        return text

def parse_filter(expr: str) -> List[SqlWhere]:
    m = _rx_null.match(expr)
    if m:
        key = m.group("key")
        neg = m.group("neg")
        return [SqlWhere(sql=f"{key} IS {'NOT ' if neg else ''}NULL", params=())]

    # between/in with brackets: key in [lo,hi]  OR  key between [lo,hi]
    m = _rx_range.match(expr)
    if m:
        key, lo, hi = m.group("key"), _lit(m.group("lo")), _lit(m.group("hi"))
        return [SqlWhere(sql=f"{key} BETWEEN ? AND ?", params=(lo, hi))]

    # between without brackets: key between lo and hi
    m = _rx_range2.match(expr)
    if m:
        key, lo, hi = m.group("key"), _lit(m.group("lo")), _lit(m.group("hi"))
        return [SqlWhere(sql=f"{key} BETWEEN ? AND ?", params=(lo, hi))]

    # binary ops and IN from list literals
    m = _rx_bin.match(expr)
    if m:
        key, op, rhs_raw = m.group("key"), m.group("op"), m.group("rhs")
        rhs = _lit(rhs_raw)
        if isinstance(rhs, (list, tuple)):
            parts = []
            for i in range(0, len(rhs), IN_CHUNK):
                chunk = rhs[i:i+IN_CHUNK]
                parts.append(SqlWhere(sql=f"{key} IN ({','.join('?' for _ in chunk)})", params=tuple(chunk)))
            if len(parts) == 1:
                return parts
            return [SqlWhere(sql="(" + " OR ".join(p.sql for p in parts) + ")",
                             params=tuple(sum((list(p.params) for p in parts), [])))]
        else:
            op = "=" if op == "==" else op
            return [SqlWhere(sql=f"{key} {op} ?", params=(rhs,))]

    raise ValueError(f"Bad filter expr: {expr}")


def _looks_like_expr(s: str) -> bool:
    s = s.lower()
    return any(tok in s for tok in ["==", " in ", " between ", ">=", "<=", ">", "<", " is null", " is not null"])

def filters_to_exprs(filters: Dict[str, Any]) -> List[str]:
    """
    Normalize user filters into mini-DSL expressions that can be parsed into SQL.
    Supports:
      - Lists  -> IN (?, ?, ?)
      - Ranges -> BETWEEN ? AND ?
      - has_mask/has_masks shorthand
      - Multiple common names in one string: "barley,hairy vetch"
      - RAW pass-through via filters["$raw"] or keys starting with "__expr__"
    """
    exprs: List[str] = []

    if not filters:
        return exprs

    # ---- RAW expressions (new style) ----
    if "$raw" in filters:
        val = filters["$raw"]
        if isinstance(val, str):
            exprs.append(val)
        elif isinstance(val, (list, tuple)):
            exprs.extend([x for x in val if isinstance(x, str)])
        else:
            raise ValueError(f"Bad $raw value: {val!r}")

    # ---- RAW expressions (legacy style __expr__N) ----
    for k, v in filters.items():
        if isinstance(k, str) and k.startswith("__expr__"):
            if isinstance(v, str):
                exprs.append(v)
            elif isinstance(v, (list, tuple)):
                exprs.extend([x for x in v if isinstance(x, str)])
            else:
                raise ValueError(f"Bad raw expr for {k}: {v!r}")

    # ---- Normalized filters ----
    for k, v in (filters or {}).items():
        # skip special raw keys
        if k == "$raw" or (isinstance(k, str) and k.startswith("__expr__")):
            continue

        # has_mask / has_masks shorthand
        if k in ("has_mask", "has_masks"):
            exprs.append("mask_path is not null" if bool(v) else "mask_path is null")
            continue

        # allow keys that embed an operator, e.g., "score>=" : 0.5
        op = None
        for candidate in (">=", "<=", ">", "<", "=="):
            if k.endswith(candidate):
                op = candidate
                key = k[: -len(candidate)]
                exprs.append(f"{key}{op}{v}")
                break
        if op:
            continue

        # value is pre-baked mini-DSL string?
        if isinstance(v, str) and _looks_like_expr(v):
            exprs.append(v)
            continue

        # comma-separated shorthand -> IN list
        if isinstance(v, str) and "," in v and not v.strip().startswith("["):
            names = [s.strip() for s in v.split(",") if s.strip()]
            exprs.append(f"{k}=={names}")
            continue

        # lists / tuples / sets -> IN (...)
        if isinstance(v, (list, tuple, set)):
            exprs.append(f"{k}=={list(v)}")
            continue

        # dict range: {in:[lo,hi]} or {between:[lo,hi]}
        if isinstance(v, dict):
            if "in" in v:
                lo, hi = v["in"]
                exprs.append(f"{k} in [{lo},{hi}]")
                continue
            if "between" in v:
                lo, hi = v["between"]
                exprs.append(f"{k} between [{lo},{hi}]")
                continue

        # scalar equality
        exprs.append(f"{k}=={v}")

    return exprs


def build_where(exprs: Sequence[str]) -> Tuple[str, Tuple[Any, ...]]:
    if not exprs:
        return "", ()
    parts: List[str] = []
    params: List[Any] = []
    for e in exprs:
        ws = parse_filter(e)
        if len(ws) == 1:
            parts.append(ws[0].sql)
            params.extend(ws[0].params)
        else:
            parts.append("(" + " OR ".join(w.sql for w in ws) + ")")
            for w in ws:
                params.extend(w.params)
    return " WHERE " + " AND ".join(parts), tuple(params)


def build_order(sort: Optional[List[Tuple[str, str]]]) -> str:
    if sort:
        return " ORDER BY " + ", ".join(f"{c} {d.upper()}" for c, d in sort)
    return f" ORDER BY {DEFAULT_ID_COL} ASC"

def build_limit_offset(limit: Optional[int], offset: Optional[int]) -> Tuple[str, Tuple[int, ...]]:
    sql = ""
    params: List[int] = []
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))
    if offset is not None:
        sql += " OFFSET ?"
        params.append(int(offset))
    return sql, tuple(params)

def seeded_order_sql(seed_param: str = ":seed") -> str:
    # Deterministic pseudo-random order based on rowid and a seed (LCG-ish).
    # Faster and stable; avoids full-table ORDER BY RANDOM().
    # Uses bit ops supported by SQLite.
    return f" ORDER BY ((rowid * 1103515245 + {seed_param}) & 0x7fffffff)"

def random_order_sql() -> str:
    # True random per call; can be expensive on large selections
    return " ORDER BY RANDOM()"