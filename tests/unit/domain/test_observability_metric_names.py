"""Unit coverage for canonical observability metric name helpers."""

from __future__ import annotations

import pytest

from bioetl.domain.observability_metric_names import (
    CANONICAL_OBSERVABILITY_METRIC_PREFIX,
    canonicalize_observability_metric_name,
    is_legacy_observability_metric_name,
)


pytestmark = pytest.mark.unit


def test_canonicalize_observability_metric_name_preserves_empty_and_canonical() -> None:
    assert CANONICAL_OBSERVABILITY_METRIC_PREFIX == "bioetl_"
    assert canonicalize_observability_metric_name("   ") == ""
    assert (
        canonicalize_observability_metric_name("bioetl_pipeline_started_total")
        == "bioetl_pipeline_started_total"
    )


def test_canonicalize_observability_metric_name_prefixes_legacy_name() -> None:
    assert (
        canonicalize_observability_metric_name(" pipeline_started_total ")
        == "bioetl_pipeline_started_total"
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("pipeline_started_total", True),
        (" bioetl_pipeline_started_total ", False),
        ("", False),
        ("   ", False),
    ],
)
def test_is_legacy_observability_metric_name(name: str, expected: bool) -> None:
    assert is_legacy_observability_metric_name(name) is expected
