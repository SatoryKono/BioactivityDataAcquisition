"""Malformed or unavailable allowlists do not waive metric drift."""

from __future__ import annotations

import builtins
import json
import pytest
from bioetl.infrastructure.observability import metric_inventory_policy as subject

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("payload", [None, [], {"allowed": []}])
def test_non_mapping_allowlist_has_no_entries(tmp_path, payload):
    path = tmp_path / "allowlist.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert subject._load_drift_allowlist(path) == {}


def test_non_list_category_cannot_supply_exceptions(tmp_path):
    path = tmp_path / "allowlist.json"
    path.write_text(
        json.dumps({"allowed": {"runtime_without_registry": "not-a-list"}}),
        encoding="utf-8",
    )
    assert not subject._load_drift_allowlist(path).get("runtime_without_registry")


def test_valid_metadata_is_loaded_and_only_matching_metric_is_allowed(tmp_path):
    path = tmp_path / "allowlist.json"
    path.write_text(
        json.dumps(
            {
                "allowed": {
                    "runtime_without_registry": [
                        {
                            "metric": "bioetl_reviewed_total",
                            "owner": "fixture",
                            "reason": "synthetic contract",
                            "review_date": "2099-01-01",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    allowed = subject._load_drift_allowlist(path)
    assert allowed["runtime_without_registry"] == {"bioetl_reviewed_total"}
    report = {
        "runtime_without_registry": [
            "bioetl_unreviewed_total",
            "bioetl_reviewed_total",
            "bioetl_unreviewed_total",
        ]
    }
    assert subject.validate_metric_inventory(report, allowlist=allowed) == {
        "runtime_without_registry": ["bioetl_unreviewed_total"]
    }


def test_unavailable_yaml_parser_does_not_load_exceptions(monkeypatch, tmp_path):
    path = tmp_path / "allowlist.yaml"
    path.write_text("allowed: {}", encoding="utf-8")
    original_import = builtins.__import__

    def without_yaml(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("synthetic unavailable parser")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_yaml)
    assert subject._load_drift_allowlist(path) == {}


def test_non_list_report_value_is_not_interpreted_as_metric_names():
    assert (
        subject.validate_metric_inventory(
            {"runtime_without_registry": {"unexpected": "mapping"}}
        )
        == {}
    )
