from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

import pytest
from typer.testing import CliRunner   # <- Typer runner to invoke a Typer app
from omegaconf import OmegaConf

from agir_cvtoolkit.cli import app as cli_app


# ───────────────────────── Fixtures ─────────────────────────

@pytest.fixture(scope="session")
def sample_db_path() -> Path:
    """Path to the small test copy of the AgIR DB."""
    db_path = Path("tests/data/db/AgIR_DB_v1_0_202509_100000sample.db")
    assert db_path.exists(), f"missing test db: {db_path}"
    return db_path


@pytest.fixture(autouse=True)
def patch_compose_cfg(monkeypatch, sample_db_path, tmp_path):
    """
    Patch cli._compose_cfg so Hydra is bypassed and returns a minimal config
    pointing to the real sample db on disk.
    """
    from agir_cvtoolkit import cli as cli_mod

    def _fake_compose_cfg(config_name: str = "config", overrides: Optional[List[str]] = None):
        cfg = OmegaConf.create({
            "db": {"semif": {
                "sqlite_path": str(sample_db_path),
                "root_map": {"data": str(tmp_path)},   # not used heavily here, but required by code
                "table": "semif",                       # change if your test DB uses another table name
            }},
            "query_defaults": {"limit": 5, "expand": {}},
            "log_level": "INFO",
        })
        cfg["working_dir"] = tmp_path
        return cfg

    monkeypatch.setattr(cli_mod, "_compose_cfg", _fake_compose_cfg)
    yield


# ───────────────────────── Tests ─────────────────────────

def test_query_json_file_smoke(tmp_path):
    """
    Since run_query writes JSON to a file (not stdout), provide --out-path and verify.
    """
    out_path = tmp_path / "q.json"
    runner = CliRunner()
    result = runner.invoke(
        cli_app,
        [
            "query",
            "--db", "semif",
            "--out", "json",
            "--out-path", str(out_path),
            "--limit", "3",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_path.exists(), "Expected JSON file to be created"

    data = json.loads(out_path.read_text())
    assert isinstance(data, list)
    assert 0 <= len(data) <= 3
    # sanity: records should be dict-like with several keys
    if data:
        assert isinstance(data[0], dict)
        # don't over-assert columns since schemas vary; just ensure we have some content
        assert len(data[0]) >= 3


def test_query_csv_output_minimal_quoting(tmp_path):
    """
    Write CSV to disk and verify it exists and that at least one numeric token
    appears unquoted (regression guard for over-quoting).
    """
    out_csv = tmp_path / "subset.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli_app,
        [
            "query",
            "--db", "semif",
            "--out", "csv",
            "--out-path", str(out_csv),
            "--limit", "10",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_csv.exists(), "Expected CSV file to be created"

    lines = out_csv.read_text().splitlines()
    assert len(lines) >= 2, "CSV should have header + at least one row"

    # header is the first row — it should not contain quotes
    header = lines[0]
    assert '"' not in header

    # Look for any bare numeric token in the first data row (no surrounding quotes),
    # e.g., ,123,  or ,45.6,
    first_data = lines[1]
    has_bare_number = re.search(r'(,|\A)-?\d+(\.\d+)?(,|\Z)', first_data) is not None
    # If the first data row doesn’t contain numbers, scan a few rows
    if not has_bare_number and len(lines) > 2:
        for row in lines[2: min(len(lines), 10)]:
            if re.search(r'(,|\A)-?\d+(\.\d+)?(,|\Z)', row):
                has_bare_number = True
                break
    assert has_bare_number, "Expected at least one unquoted numeric token (QUOTE_MINIMAL)"


def test_query_with_filters_sort_and_preview(tmp_path):
    """
    Run a query with filters/sort/preview. We can't inspect internals here,
    but we can assert the command succeeds and produces output.
    """
    out_path = tmp_path / "filtered.json"
    runner = CliRunner()
    result = runner.invoke(
        cli_app,
        [
            "query",
            "--db", "semif",
            "-f", "state=NC",                         # adjust to a column that exists in your DB if needed
            "-f", "category_common_name=barley,hairy vetch",
            "--sort", "datetime:desc",
            "--limit", "5",
            "--preview", "2",                         # ensures the preview path is exercised
            "--out", "json",
            "--out-path", str(out_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_path.exists(), "Expected filtered JSON file to be created"

    data = json.loads(out_path.read_text())
    assert isinstance(data, list)
    assert len(data) <= 5
    if data:
        assert isinstance(data[0], dict)


def test_query_filter_by_estimated_bbox_area_cm2(tmp_path):

    out_path = tmp_path / "area_ge_100.json"
    runner = CliRunner()
    res = runner.invoke(
        cli_app,
        [
            "query",
            "--db", "semif",
            "-f", "estimated_bbox_area_cm2>=100",
            "--limit", "20",
            "--projection", "cutout_id,image_path,estimated_bbox_area_cm2",
            "--out", "json",
            "--out-path", str(out_path),
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(out_path.read_text())
    for row in data:
        # tolerate missing field in rare rows; skip those
        if "estimated_bbox_area_cm2" in row and row["estimated_bbox_area_cm2"] is not None:
            assert row["estimated_bbox_area_cm2"] >= 100

def test_query_filter_by_estimated_bbox_area_cm2_between(tmp_path):
    """
    Verify both 'between [lo,hi]' and 'between lo and hi' syntaxes work.
    We'll run the latter since you added _rx_range2.
    """
    out_path = tmp_path / "area_between_50_200.json"
    res = CliRunner().invoke(
        cli_app,
        [
            "query",
            "--db", "semif",
            "-f", "estimated_bbox_area_cm2 between 50 and 200",
            "--limit", "20",
            "--projection", "cutout_id,image_path,estimated_bbox_area_cm2",
            "--out", "json",
            "--out-path", str(out_path),
        ],
    )
    assert res.exit_code == 0, res.output
    data = json.loads(out_path.read_text())
    for row in data:
        v = row.get("estimated_bbox_area_cm2")
        if v is not None:
            assert 50 <= v <= 200