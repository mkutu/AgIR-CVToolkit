"""Species information management and lookup."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


class SpeciesInfo:
    """Manages species/category information from JSON database."""
    
    def __init__(self, path: Optional[Path]) -> None:
        """Initialize species info manager.
        
        Args:
            path: Path to species_info.json file
        """
        self.path = path
        self.by_class_id: Dict[str, Dict[str, Any]] = {}
        self.by_usda_symbol: Dict[str, Dict[str, Any]] = {}
        self.by_common_name: Dict[str, Dict[str, Any]] = {}
    
    def load(self) -> None:
        """Load species information from JSON file."""
        if not self.path or not self.path.exists():
            log.warning(f"Species info file not found: {self.path}")
            self.by_class_id = {}
            self.by_usda_symbol = {}
            self.by_common_name = {}
            return
        
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Clean and normalize species data
        cleaned = self.clean_species_block(data, uppercase_keys=False)
        species_data = cleaned.get("species", {})
        
        # Build lookup dictionaries
        self.by_class_id = {
            str(cat["class_id"]): cat 
            for key, cat in species_data.items()
            if "class_id" in cat
        }
        
        self.by_usda_symbol = {
            cat["USDA_symbol"]: cat
            for cat in self.by_class_id.values()
            if "USDA_symbol" in cat and cat["USDA_symbol"]
        }
        
        self.by_common_name = {
            cat["common_name"].lower(): cat
            for cat in self.by_class_id.values()
            if "common_name" in cat and cat["common_name"]
        }
        
        log.info(
            f"Loaded {len(self.by_class_id)} species from {self.path}"
        )
    
    def get_by_class_id(self, class_id: int | str) -> Optional[Dict[str, Any]]:
        """Get species info by class ID.
        
        Args:
            class_id: Numeric class ID
            
        Returns:
            Species dictionary or None if not found
        """
        return self.by_class_id.get(str(class_id))
    
    def get_by_usda_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get species info by USDA symbol.
        
        Args:
            symbol: USDA plant symbol
            
        Returns:
            Species dictionary or None if not found
        """
        return self.by_usda_symbol.get(symbol.upper())
    
    def get_by_common_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get species info by common name (case-insensitive).
        
        Args:
            name: Common name
            
        Returns:
            Species dictionary or None if not found
        """
        return self.by_common_name.get(name.lower())
    
    def categories_from_annotations(
        self, 
        anns: Optional[List[Dict[str, Any]]]
    ) -> Optional[List[Dict[str, Any]]]:
        """Extract category info from annotation list.
        
        Args:
            anns: List of annotation dictionaries
            
        Returns:
            List of category dictionaries or None if no annotations
        """
        if not anns:
            return None
        
        cats: List[Dict[str, Any]] = []
        for ann in anns:
            cid = ann.get("category_class_id")
            if cid is not None:
                cat = self.get_by_class_id(cid)
                if cat:
                    cats.append(cat)
        
        return cats or None
    
    def clean_species_block(
        self, 
        data: Dict[str, Any], 
        uppercase_keys: bool = True
    ) -> Dict[str, Any]:
        """Clean and normalize species data.
        
        Args:
            data: Raw species data dictionary
            uppercase_keys: Whether to uppercase outer species keys
            
        Returns:
            Cleaned species data dictionary
        """
        src = data.get("species") or {}
        cleaned_species = self._clean_categories_map(src, uppercase_keys=uppercase_keys)
        out = dict(data)
        out["species"] = cleaned_species
        return out
    
    @staticmethod
    def _clean_categories_map(
        categories: Dict[str, Dict[str, Any]], 
        uppercase_keys: bool
    ) -> Dict[str, Dict[str, Any]]:
        """Clean individual category entries.
        
        Applies field-specific casing, normalization, and validation.
        """
        UPPER_KEYS = {"usda_symbol", "eppo"}
        LOWER_KEYS = {"common_name", "species", "growth_habit", "duration", "group"}
        CAP_KEYS = {"class", "subclass", "order", "family", "genus"}
        TITLE_KEYS = {"authority"}
        
        def _trim_or_none(v: Any) -> Any:
            if isinstance(v, str):
                s = v.strip()
                return s if s else None
            return v
        
        def _smart_title(s: str) -> str:
            """Title case with special handling for small words."""
            small = {"and", "or", "of", "the", "in", "on", "at", "to", "for"}
            parts = s.title().split()
            out = []
            for i, w in enumerate(parts):
                core = w.strip("()[],.")
                if i not in (0, len(parts)-1) and core.lower() in small:
                    w = w.replace(core, core.lower(), 1)
                out.append(w)
            return " ".join(out)
        
        def _fix_typos(s: str) -> str:
            return s.replace("perenial", "perennial")
        
        def _normalize_separators(s: str) -> str:
            s = re.sub(r"\s*,\s*", ", ", s)
            s = re.sub(r"\s*/\s*", "/", s)
            s = re.sub(r"\s{2,}", " ", s)
            return s
        
        def _norm_hex(h: Any) -> Any:
            if not isinstance(h, str):
                return h
            s = h.strip().lower()
            if not s:
                return None
            if s.startswith("#"):
                s = s[1:]
            if len(s) in (3, 6) and all(c in "0123456789abcdef" for c in s):
                if len(s) == 3:
                    s = "".join(ch*2 for ch in s)
                return "#" + s
            return h
        
        def _norm_rgb(v: Any) -> Any:
            if isinstance(v, (list, tuple)) and len(v) == 3:
                try:
                    return [max(0, min(255, int(x))) for x in v]
                except Exception:
                    return v
            return v
        
        def _norm_alias(v: Any) -> Any:
            if isinstance(v, list):
                seen = set()
                out: List[str] = []
                for item in v:
                    if isinstance(item, str):
                        t = item.strip()
                        if t and t not in seen:
                            seen.add(t)
                            out.append(t)
                return out
            return v
        
        cleaned: Dict[str, Dict[str, Any]] = {}
        
        for outer_key, category in categories.items():
            if not isinstance(category, dict):
                continue
            
            cz: Dict[str, Any] = {}
            for k, v in category.items():
                val = _trim_or_none(v)
                lk = k.lower()
                
                if isinstance(val, str):
                    if lk in UPPER_KEYS:
                        val = val.upper()
                    elif lk in LOWER_KEYS:
                        val = _fix_typos(_normalize_separators(val)).lower()
                    elif lk in CAP_KEYS:
                        val = val.capitalize()
                    elif lk in TITLE_KEYS:
                        val = _smart_title(val)
                
                if lk == "hex":
                    val = _norm_hex(val)
                elif lk == "rgb":
                    val = _norm_rgb(val)
                elif lk == "alias":
                    val = _norm_alias(val)
                
                cz[k] = val
            
            new_key = outer_key.upper() if uppercase_keys else outer_key
            cleaned[new_key] = cz
        
        return cleaned