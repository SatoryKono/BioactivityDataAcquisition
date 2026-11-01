"""Runtime allowlist IO failures and drift filtering retain their contracts."""

from __future__ import annotations

import builtins
from datetime import date
from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.observability import metric_inventory_policy as policy

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("text", ["", "[]", "true", "allowed: []"])
def test_non_mapping_allowlist_cannot_suppress_new_drift(
    tmp_path: Path, text: str
) -> None:
    path = tmp_path / "allowlist.yaml"
    path.write_text(text, encoding="utf-8")
    allowed = policy._load_drift_allowlist(path)
    assert allowed == {}
    assert policy.validate_metric_inventory(
        {"runtime_without_registry": ["bioetl_new_total"]}, allowlist=allowed
    ) == {"runtime_without_registry": ["bioetl_new_total"]}


def test_missing_file_and_optional_yaml_dependency_do_not_allow_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "allowlist.yaml"
    assert policy._load_drift_allowlist(path) == {}
    path.write_text("allowed: {}\n", encoding="utf-8")
    original_import = builtins.__import__

    def without_yaml(name: str, *args, **kwargs):
        if name == "yaml":
            raise ImportError("optional YAML dependency unavailable")
        return original_import(name, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "__import__", without_yaml)
        allowed = policy._load_drift_allowlist(path)
    assert allowed == {}
    assert policy.validate_metric_inventory(
        {"runtime_without_registry": ["bioetl_new_total"]}, allowlist=allowed
    ) == {"runtime_without_registry": ["bioetl_new_total"]}


def test_invalid_yaml_and_read_denial_propagate_instead_of_allowing_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "allowlist.yaml"
    path.write_text("allowed: [\n", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        policy._load_drift_allowlist(path)
    original_read = Path.read_text

    def denied(current: Path, *args, **kwargs):
        if current == path.resolve():
            raise PermissionError("allowlist read denied")
        return original_read(current, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(PermissionError, match="allowlist read denied"):
        policy._load_drift_allowlist(path)


def test_allowlist_only_suppresses_named_metrics_and_keeps_sorted_unique_drift(
    tmp_path: Path,
) -> None:
    path = tmp_path / "allowlist.yaml"
    path.write_text(
        "allowed:\n  runtime_without_registry: [bioetl_allowed_total, bioetl_allowed_total]\n"
        "  documented_without_registry: invalid-list\n",
        encoding="utf-8",
    )
    allowed = policy._load_drift_allowlist(path)
    assert allowed["runtime_without_registry"] == {"bioetl_allowed_total"}
    assert "documented_without_registry" not in allowed
    report = {
        "runtime_without_registry": [
            "z_total",
            "bioetl_allowed_total",
            "a_total",
            "z_total",
        ],
        "documented_without_registry": {"nested": []},
    }
    assert policy.validate_metric_inventory(report, allowlist=allowed) == {
        "runtime_without_registry": ["a_total", "z_total"]
    }
    assert (
        policy.validate_metric_inventory(
            {"runtime_without_registry": ["bioetl_allowed_total"]}, allowlist=allowed
        )
        == {}
    )


def test_review_date_validation_rejects_malformed_and_expired_dates() -> None:
    arguments = {
        "key": "runtime_cardinality_review_required",
        "metric_name": "bioetl_test_total",
    }
    with pytest.raises(ValueError, match="expected ISO YYYY-MM-DD"):
        policy._validate_allowlist_review_date(
            **arguments, raw_review_date="not-a-date"
        )
    with pytest.raises(ValueError, match="expired review_date"):
        policy._validate_allowlist_review_date(
            **arguments, raw_review_date="2026-10-28", today=date(2026, 10, 29)
        )
    assert (
        policy._validate_allowlist_review_date(
            **arguments, raw_review_date="2026-10-29", today=date(2026, 10, 29)
        )
        is None
    )


@pytest.mark.parametrize("field", ["owner", "reason", "review_date"])
def test_runtime_loader_requires_lifecycle_metadata(tmp_path: Path, field: str) -> None:
    entry = {
        "metric": "bioetl_test_total",
        "owner": "observability",
        "reason": "bounded labels",
        "review_date": "2999-01-01",
    }
    path = tmp_path / "allowlist.yaml"
    path.write_text(
        yaml.safe_dump({"allowed": {"runtime_cardinality_review_required": [entry]}}),
        encoding="utf-8",
    )
    assert policy._load_drift_allowlist(path)[
        "runtime_cardinality_review_required"
    ] == {"bioetl_test_total"}
    del entry[field]
    path.write_text(
        yaml.safe_dump({"allowed": {"runtime_cardinality_review_required": [entry]}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=f"missing required {field}"):
        policy._load_drift_allowlist(path)
