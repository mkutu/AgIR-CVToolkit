import ast
import json

def _parse_repeatable_filters(exprs: list[str]) -> dict:
    """
    Accepts any mix of:
      - Mini-DSL:  'category_common_name==["barley","hairy vetch"]'
      - JSON:      '{"category_common_name": ["barley","hairy vetch"]}'
      - Shorthand: 'category_common_name=barley,hairy vetch'   (single '=' + comma list)
      - Scalars:   'state=NC'  (single '=' + scalar)
    """
    def _maybe_list_from_commas(s: str):
        s = s.strip()
        if not s:
            return s
        # Python/JSON list literal?
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("(") and s.endswith(")")):
            try:
                return ast.literal_eval(s)
            except Exception:
                return s
        # Comma-separated shorthand -> list
        if "," in s:
            parts = [p.strip() for p in s.split(",") if p.strip()]
            return parts if len(parts) > 1 else parts[0]
        return s

    def _merge_value(acc: dict, key: str, val):
        """Merge val into acc[key], promoting to list and de-duplicating (stable order)."""
        if key not in acc:
            acc[key] = val
            return
        existing = acc[key]
        if not isinstance(existing, list):
            existing = [existing]
        if isinstance(val, list):
            existing.extend(val)
        else:
            existing.append(val)
        # stable de-dup (case-insensitive for strings)
        seen = set()
        merged = []
        for x in existing:
            k = x if not isinstance(x, str) else x.lower()
            if k in seen:
                continue
            seen.add(k)
            merged.append(x)
        acc[key] = merged

    out: dict = {}
    for e in exprs or []:
        if not e:
            continue
        e = e.strip()

        # JSON block
        if e.startswith("{"):
            obj = json.loads(e)
            for k, v in obj.items():
                _merge_value(out, k, v)
            continue

        # Full mini-DSL (==, in, between, is null, >=, etc.) → store as raw exprs list
        if any(tok in e for tok in ("==", " in ", " between ", " is null", " is not null", ">=", "<=", ">", "<")):
            out.setdefault("$raw", []).append(e)
            continue

        # Single '=' shorthand: key=value or key=a,b,c
        if "=" in e:
            k, v = e.split("=", 1)
            k = k.strip()
            v = _maybe_list_from_commas(v)
            if isinstance(v, str) and v.startswith("[") and v.endswith("]"):
                try:
                    v = ast.literal_eval(v)
                except Exception:
                    pass
            _merge_value(out, k, v)
            continue

        # Fallback: treat whole token as raw expr
        out.setdefault("$raw", []).append(e)

    return out