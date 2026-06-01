"""Guardrails for retiring SilverWriter compatibility mixin debt."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SILVER_ROOT = ROOT / "src" / "bioetl" / "infrastructure" / "storage" / "silver"
SILVER_WRITER = (
    ROOT / "src" / "bioetl" / "infrastructure" / "storage" / "silver_writer.py"
)

RETIRED_FILES = (
    SILVER_ROOT / "compatibility_mixins.py",
    SILVER_ROOT / "finalization_compatibility_mixins.py",
    SILVER_ROOT / "audit_metadata_compatibility_mixin.py",
    SILVER_ROOT / "finalization_pipeline_compatibility_mixin.py",
)


def test_silver_writer_compatibility_mixin_modules_are_retired() -> None:
    """Retired SilverWriter compatibility mixin files must not return."""
    assert [path for path in RETIRED_FILES if path.exists()] == []


def test_silver_writer_does_not_import_compatibility_mixins() -> None:
    """SilverWriter must use composition services, not legacy compatibility mixins."""
    source = SILVER_WRITER.read_text(encoding="utf-8")
    forbidden = (
        "CompatibilityMixin",
        "compatibility_mixins",
        "finalization_compatibility",
        "audit_metadata_compatibility",
        "**legacy_kwargs",
        "_pop_legacy_runtime_kwargs",
        "_coerce_silver_write_invocation",
        "DeltaTable =",
        "write_deltalake =",
        "asyncio =",
    )
    assert [needle for needle in forbidden if needle in source] == []


def test_silver_metadata_runtime_has_no_legacy_finalization_fallbacks() -> None:
    """Direct metadata-writer and AsyncMock finalization fallbacks must stay retired."""
    metadata_ops = (
        ROOT
        / "src/bioetl/infrastructure/storage/silver/operations/metadata_operations.py"
    ).read_text(encoding="utf-8")
    finalization_support = (
        ROOT
        / "src/bioetl/infrastructure/storage/silver/operations/metadata_finalization_support.py"
    ).read_text(encoding="utf-8")
    assert "AsyncMock" not in metadata_ops
    assert "_build_direct_legacy_silver_metadata" not in finalization_support
