from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.hotspot_family_metrics import (
    _is_import_facade_file,
    _is_loccap_excluded,
    _is_schema_or_field_definition_file,
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
