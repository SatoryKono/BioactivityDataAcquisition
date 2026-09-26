"""Unit tests for resolve_metric_labels allowlist (#11223)."""

from __future__ import annotations

import pytest

from bioetl.domain.ports.observability.metrics import (
    ALLOWED_CORE_METRIC_LABEL_KEYS,
    ALLOWED_METRIC_LABEL_KEYS,
    resolve_metric_labels,
)


def test_resolve_metric_labels_none_and_empty() -> None:
    assert resolve_metric_labels(None) == {}
    assert resolve_metric_labels({}) == {}


def test_resolve_metric_labels_allows_core_keys() -> None:
    labels = {key: "x" for key in sorted(ALLOWED_CORE_METRIC_LABEL_KEYS)}
    resolved = resolve_metric_labels(labels)
    assert resolved == labels
    assert resolved is not labels


def test_resolve_metric_labels_allows_extended_bounded_key() -> None:
    labels = {"pipeline": "activity", "table": "gold.activity"}
    assert resolve_metric_labels(labels) == labels


@pytest.mark.parametrize(
    "forbidden_key",
    ("run_id", "record_id", "error_message", "path", "url", "message"),
)
def test_resolve_metric_labels_rejects_forbidden_keys(forbidden_key: str) -> None:
    with pytest.raises(ValueError, match="Forbidden metric label"):
        resolve_metric_labels({"pipeline": "x", forbidden_key: "leak"})


def test_resolve_metric_labels_rejects_unrecognized_keys() -> None:
    with pytest.raises(ValueError, match="Unrecognized metric label"):
        resolve_metric_labels({"pipeline": "x", "totally_unknown_label": "y"})


def test_allowed_metric_label_keys_cover_core() -> None:
    assert ALLOWED_CORE_METRIC_LABEL_KEYS <= ALLOWED_METRIC_LABEL_KEYS
