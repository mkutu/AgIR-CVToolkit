
from agir_cvtoolkit.core.db.types import ImageRecord
from typing import Optional

def _rec_to_dict(r: ImageRecord) -> dict:
    """
    Emit ALL DB columns 1:1 from r.extras,
    override with absolute path strings when available,
    then add *_abs convenience columns from aux_paths.
    """
    d = dict(r.extras)
    if r.image_path is not None:
        d["image_path"] = str(r.image_path)
    if r.mask_path is not None:
        d["mask_path"] = str(r.mask_path)
    for k, p in r.aux_paths.items():
        d[k] = str(p)
    return d


def _parse_sort(sort: Optional[str]) -> Optional[list[tuple[str, str]]]:
    if not sort:
        return None
    out: list[tuple[str, str]] = []
    for token in sort.split(","):
        col, *dir_ = token.split(":")
        d = (dir_[0] if dir_ else "asc").lower()
        out.append((col.strip(), ("desc" if d == "desc" else "asc")))
    return out or None


def _parse_sample(sample: Optional[str]) -> Optional[dict]:
    if not sample:
        return None
    # Parse "strategy:key=val,key=val"
    strategy, *rest = sample.split(":", 1)
    kv = {}
    if rest:
        for token in rest[0].split(","):
            token = token.strip()
            if not token:
                continue
            if "=" in token:
                k, v = token.split("=", 1)
                k = k.strip()
                v = v.strip()
                if v.isdigit():
                    v = int(v)
                kv[k] = v
    if "by" in kv and isinstance(kv["by"], str):
        kv["by"] = [s.strip() for s in kv["by"].replace("|", ",").split(",") if s.strip()]
    return {"strategy": strategy.strip(), **kv}
