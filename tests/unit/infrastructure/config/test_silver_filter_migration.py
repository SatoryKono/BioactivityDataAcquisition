"""Unit tests for Silver filter compatibility identity helpers."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.config.silver_filter_migration import (
    HISTORICAL_SILVER_FILTER_COMPATIBILITY_MODE,
    build_silver_filter_compatibility_snapshot,
    normalize_silver_filter_compatibility_mode,
    resolve_silver_filter_compatibility_mode,
)

pytestmark = pytest.mark.unit


def test_runtime_identity_uses_clear_structural_only_compat_mode() -> None:
    """Current runtime identity must not imply semantic auto-promotion."""
    assert resolve_silver_filter_compatibility_mode() == "structural_only_compat"
    assert build_silver_filter_compatibility_snapshot()["mode"] == (
        "structural_only_compat"
    )


def test_historical_auto_promote_mode_remains_readable() -> None:
    """Persisted historical manifests may still carry the old identity value."""
    assert (
        normalize_silver_filter_compatibility_mode(
            HISTORICAL_SILVER_FILTER_COMPATIBILITY_MODE
        )
        == "structural_only_auto_promote"
    )


def test_unknown_silver_filter_compatibility_mode_fails_closed() -> None:
    """Unsupported mode names must not silently become structural-only defaults."""
    with pytest.raises(
        ValueError, match="Unsupported silver_filter_compatibility_mode"
    ):
        normalize_silver_filter_compatibility_mode("legacy_semantic_silver")
