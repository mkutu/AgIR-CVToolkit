"""
Utilities for working with query specifications.

Helps with reproducing queries and converting between formats.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional


def load_query_spec(query_spec_path: Path) -> Dict:
    """Load query specification from JSON file."""
    with open(query_spec_path) as f:
        return json.load(f)


def query_spec_to_cli_args(query_spec: Dict, include_db: bool = True) -> List[str]:
    """
    Convert query specification to CLI arguments.
    
    Args:
        query_spec: Query specification dict
        include_db: Whether to include --db flag
    
    Returns:
        List of CLI arguments
    
    Example:
        >>> spec = load_query_spec("query_spec.json")
        >>> args = query_spec_to_cli_args(spec)
        >>> print(" ".join(args))
        --db semif --filters "state=NC" --limit 100
    """
    args = []
    
    # Database
    if include_db:
        db = query_spec.get("database", {}).get("type")
        if db:
            args.extend(["--db", db])
    
    # Query parameters
    params = query_spec.get("query_parameters", {})
    
    # Filters
    filters = params.get("filters", {}).get("raw", [])
    for f in filters:
        args.extend(["--filters", f'"{f}"'])
    
    # Projection
    projection = params.get("projection")
    if projection:
        args.extend(["--projection", ",".join(projection)])
    
    # Sort
    sort_raw = params.get("sort", {}).get("raw")
    if sort_raw:
        args.extend(["--sort", f'"{sort_raw}"'])
    
    # Limit
    limit = params.get("limit")
    if limit:
        args.extend(["--limit", str(limit)])
    
    # Offset
    offset = params.get("offset")
    if offset:
        args.extend(["--offset", str(offset)])
    
    # Sample
    sample_raw = params.get("sample", {}).get("raw")
    if sample_raw:
        args.extend(["--sample", f'"{sample_raw}"'])
    
    # Output format
    output_format = query_spec.get("execution", {}).get("output_format")
    if output_format:
        args.extend(["--out", output_format])
    
    return args


def print_query_command(query_spec_path: Path, command: str = "agir-cvtoolkit query") -> None:
    """
    Print the CLI command to reproduce a query.
    
    Args:
        query_spec_path: Path to query_spec.json
        command: Base command (default: "agir-cvtoolkit query")
    """
    spec = load_query_spec(query_spec_path)
    args = query_spec_to_cli_args(spec)
    
    print(f"{command} \\")
    for i, arg in enumerate(args):
        end = " \\" if i < len(args) - 1 else ""
        print(f"  {arg}{end}")


def query_spec_summary(query_spec: Dict) -> str:
    """
    Generate a human-readable summary of the query specification.
    
    Example:
        >>> spec = load_query_spec("query_spec.json")
        >>> print(query_spec_summary(spec))
        Query: semif database
        Filters: state=NC, category_common_name in [barley, wheat]
        Sampling: stratified (10 per group by category_common_name)
        Limit: 100 records
        Output: JSON
    """
    lines = []
    
    # Metadata
    meta = query_spec.get("query_metadata", {})
    lines.append(f"Run ID: {meta.get('run_id', 'N/A')}")
    lines.append(f"Timestamp: {meta.get('timestamp', 'N/A')}")
    lines.append("")
    
    # Database
    db = query_spec.get("database", {})
    lines.append(f"Database: {db.get('type', 'N/A')}")
    lines.append(f"Table: {db.get('table', 'N/A')}")
    lines.append("")
    
    # Query parameters
    params = query_spec.get("query_parameters", {})
    
    # Filters
    filters = params.get("filters", {}).get("parsed", {})
    if filters:
        lines.append("Filters:")
        for key, value in filters.items():
            if key == "$raw":
                for expr in value:
                    lines.append(f"  - {expr}")
            else:
                if isinstance(value, list):
                    lines.append(f"  - {key} IN {value}")
                else:
                    lines.append(f"  - {key} = {value}")
        lines.append("")
    
    # Projection
    projection = params.get("projection")
    if projection:
        lines.append(f"Columns: {', '.join(projection)}")
        lines.append("")
    
    # Sort
    sort_parsed = params.get("sort", {}).get("parsed")
    if sort_parsed:
        sort_strs = [f"{col} {direction.upper()}" for col, direction in sort_parsed]
        lines.append(f"Sort: {', '.join(sort_strs)}")
        lines.append("")
    
    # Sample
    sample = params.get("sample", {}).get("parsed")
    if sample:
        strategy = sample.get("strategy", "none")
        if strategy == "stratified":
            by = sample.get("by", [])
            per_group = sample.get("per_group", 0)
            lines.append(f"Sampling: Stratified ({per_group} per group by {', '.join(by)})")
        elif strategy == "random":
            n = sample.get("n", 0)
            lines.append(f"Sampling: Random ({n} records)")
        elif strategy == "seeded":
            n = sample.get("n", 0)
            seed = sample.get("seed", 0)
            lines.append(f"Sampling: Seeded ({n} records, seed={seed})")
        lines.append("")
    
    # Limit
    limit = params.get("limit")
    if limit:
        lines.append(f"Limit: {limit} records")
    
    offset = params.get("offset")
    if offset:
        lines.append(f"Offset: {offset}")
    
    if limit or offset:
        lines.append("")
    
    # Execution
    exec_info = query_spec.get("execution", {})
    lines.append(f"Output: {exec_info.get('output_format', 'N/A').upper()}")
    if exec_info.get("preview_mode"):
        lines.append(f"Preview: First {exec_info.get('preview_count', 0)} records")
    
    return "\n".join(lines)


def compare_query_specs(spec1_path: Path, spec2_path: Path) -> Dict:
    """
    Compare two query specifications and show differences.
    
    Returns:
        Dict with 'same', 'different', and 'details' keys
    """
    spec1 = load_query_spec(spec1_path)
    spec2 = load_query_spec(spec2_path)
    
    p1 = spec1.get("query_parameters", {})
    p2 = spec2.get("query_parameters", {})
    
    differences = {}
    
    # Compare filters
    f1 = p1.get("filters", {}).get("parsed", {})
    f2 = p2.get("filters", {}).get("parsed", {})
    if f1 != f2:
        differences["filters"] = {"spec1": f1, "spec2": f2}
    
    # Compare sampling
    s1 = p1.get("sample", {}).get("parsed")
    s2 = p2.get("sample", {}).get("parsed")
    if s1 != s2:
        differences["sample"] = {"spec1": s1, "spec2": s2}
    
    # Compare limit
    l1 = p1.get("limit")
    l2 = p2.get("limit")
    if l1 != l2:
        differences["limit"] = {"spec1": l1, "spec2": l2}
    
    # Compare sort
    sort1 = p1.get("sort", {}).get("parsed")
    sort2 = p2.get("sort", {}).get("parsed")
    if sort1 != sort2:
        differences["sort"] = {"spec1": sort1, "spec2": sort2}
    
    return {
        "same": len(differences) == 0,
        "different": list(differences.keys()),
        "details": differences,
    }


# ==================== CLI Utility ====================

def main():
    """CLI utility for working with query specifications."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Query specification utilities")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Show query summary")
    summary_parser.add_argument("query_spec", type=Path, help="Path to query_spec.json")
    
    # Reproduce command
    reproduce_parser = subparsers.add_parser("reproduce", help="Show CLI command to reproduce query")
    reproduce_parser.add_argument("query_spec", type=Path, help="Path to query_spec.json")
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two query specs")
    compare_parser.add_argument("spec1", type=Path, help="First query_spec.json")
    compare_parser.add_argument("spec2", type=Path, help="Second query_spec.json")
    
    args = parser.parse_args()
    
    if args.command == "summary":
        spec = load_query_spec(args.query_spec)
        print(query_spec_summary(spec))
    
    elif args.command == "reproduce":
        print_query_command(args.query_spec)
    
    elif args.command == "compare":
        result = compare_query_specs(args.spec1, args.spec2)
        if result["same"]:
            print("✓ Query specifications are identical")
        else:
            print("✗ Query specifications differ in:", ", ".join(result["different"]))
            print("\nDifferences:")
            for key, values in result["details"].items():
                print(f"\n{key}:")
                print(f"  Spec 1: {values['spec1']}")
                print(f"  Spec 2: {values['spec2']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()