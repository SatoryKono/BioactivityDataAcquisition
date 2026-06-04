from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import scripts.engineering.qa.hotspot_family_metrics as hotspot_family_metrics
from scripts.engineering.qa.hotspot_family_metrics import (
    _is_import_facade_file,
    _is_loccap_excluded,
    _is_schema_or_field_definition_file,
    iter_family_python_files,
)

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_import_facade_file_is_excluded() -> None:
    """Import facade modules are excluded from 250 LOC file-growth checks."""
    facade_file = PROJECT_ROOT / "src/bioetl/infrastructure/observability/metrics_definitions.py"

    assert _is_import_facade_file(path=facade_file)
    assert _is_loccap_excluded(path=facade_file)


def test_schema_field_definition_file_is_excluded() -> None:
    """Schema/field definition files are excluded from 250 LOC thresholds."""
    schema_file = PROJECT_ROOT / "src/bioetl/infrastructure/schemas/source_config.py"

    assert _is_schema_or_field_definition_file(path=schema_file)
    assert _is_loccap_excluded(path=schema_file)


def test_business_logic_file_remains_counted() -> None:
    """Business-logic modules stay visible for file-growth checks."""
    logic_file = PROJECT_ROOT / "src/bioetl/infrastructure/config/composite_config_api.py"

    assert not _is_loccap_excluded(path=logic_file)


def test_iter_family_python_files_ignores_untracked_python_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Family collectors must stay stable when local untracked files exist."""
    tracked_file = tmp_path / "src/bioetl/application/core/tracked_module.py"
    untracked_file = tmp_path / "src/bioetl/application/core/untracked_module.py"
    tracked_file.parent.mkdir(parents=True, exist_ok=True)
    tracked_file.write_text("value = 1\n", encoding="utf-8")
    untracked_file.write_text("value = 2\n", encoding="utf-8")

    def _fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args[0] if args else [],
            returncode=0,
            stdout="src/bioetl/application/core/tracked_module.py\n",
            stderr="",
        )

    monkeypatch.setattr(hotspot_family_metrics, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(hotspot_family_metrics.subprocess, "run", _fake_run)

    files = iter_family_python_files(path_prefixes=["src/bioetl/application/core/"])

    assert files == [tracked_file]
