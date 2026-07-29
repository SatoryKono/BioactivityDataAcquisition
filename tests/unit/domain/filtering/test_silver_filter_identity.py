# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for domain-owned Silver filter runtime identity helpers."""

from __future__ import annotations

import pytest

from bioetl.domain.filtering.silver_filter_identity import (
    HISTORICAL_SILVER_FILTER_COMPATIBILITY_MODE,
    build_silver_filter_compatibility_snapshot,
    normalize_silver_filter_compatibility_mode,
    resolve_silver_filter_compatibility_mode,
)

pytestmark = pytest.mark.unit


def test_resolve_silver_filter_compatibility_mode_returns_canonical_identity() -> None:
    assert resolve_silver_filter_compatibility_mode() == "structural_only_compat"


def test_build_silver_filter_compatibility_snapshot_is_manifest_stable() -> None:
    assert build_silver_filter_compatibility_snapshot() == {
        "schema_version": "silver-filter-compatibility-v1",
        "mode": "structural_only_compat",
        "source": "default",
    }


def test_normalize_silver_filter_compatibility_mode_preserves_historical_alias() -> (
    None
):
    assert (
        normalize_silver_filter_compatibility_mode(
            HISTORICAL_SILVER_FILTER_COMPATIBILITY_MODE
        )
        == "structural_only_auto_promote"
    )


def test_normalize_silver_filter_compatibility_mode_rejects_retired_semantic_mode() -> (
    None
):
    with pytest.raises(
        ValueError, match="Unsupported silver_filter_compatibility_mode"
    ):
        normalize_silver_filter_compatibility_mode("legacy_semantic_silver")
