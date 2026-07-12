"""Governance checks for domain aggregate classification coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
DOMAIN_ROOT = ROOT / "src/bioetl/domain"
CLASSIFICATION_PATH = ROOT / "configs/quality/domain_aggregate_classification.yaml"
REGISTRY_PATH = ROOT / "reports/quality/domain-aggregate-invariant-registry.json"


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _top_level_domain_package_paths() -> set[str]:
    return {
        path.relative_to(ROOT).as_posix()
        for path in DOMAIN_ROOT.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }


def _top_level_domain_module_paths() -> set[str]:
    return {
        path.relative_to(ROOT).as_posix()
        for path in DOMAIN_ROOT.iterdir()
        if path.is_file() and path.suffix == ".py" and path.name != "__init__.py"
    }


def test_domain_aggregate_classification_has_expected_policy_shape() -> None:
    payload = _load_yaml(CLASSIFICATION_PATH)

    assert payload["schema_version"] == 1
    assert payload["policy_scope"] == "domain_aggregate_classification"
    assert payload["linked_issue"] == "#6225"
    assert payload["new_surface_policy"] == (
        "fail_fast_unclassified_domain_aggregate_surface"
    )
    assert payload["aggregate_package"]["path"] == "src/bioetl/domain/aggregates"
    assert payload["true_aggregates"]
    assert payload["non_aggregate_clusters"]
    assert payload["non_aggregate_root_modules"]


def test_domain_top_level_packages_are_exactly_classified() -> None:
    payload = _load_yaml(CLASSIFICATION_PATH)
    aggregate_package = payload["aggregate_package"]
    assert isinstance(aggregate_package, dict)

    classified = {str(aggregate_package["path"])}
    classified.update(str(row["path"]) for row in payload["non_aggregate_clusters"])

    assert classified == _top_level_domain_package_paths()


def test_domain_top_level_root_modules_are_exactly_classified() -> None:
    payload = _load_yaml(CLASSIFICATION_PATH)
    classified = {str(row["path"]) for row in payload["non_aggregate_root_modules"]}

    assert classified == _top_level_domain_module_paths()


def test_true_aggregates_match_invariant_registry() -> None:
    classification = _load_yaml(CLASSIFICATION_PATH)
    registry = _load_json(REGISTRY_PATH)

    true_rows = {
        str(row["aggregate"]): row for row in classification["true_aggregates"]
    }
    registry_rows = {str(row["aggregate"]): row for row in registry["aggregates"]}

    assert set(true_rows) == set(registry_rows)
    assert registry["aggregate_root_count"] == len(true_rows)

    for aggregate_name, true_row in true_rows.items():
        registry_row = registry_rows[aggregate_name]
        assert true_row["root_module"] == registry_row["root_module"]
        assert set(true_row["implementation_modules"]) == set(
            registry_row["implementation_modules"]
        )
        assert set(true_row["invariant_tests"]) == set(registry_row["test_paths"])

        evidence_paths = [
            true_row["root_module"],
            *true_row["implementation_modules"],
            *true_row["invariant_tests"],
        ]
        missing = [path for path in evidence_paths if not (ROOT / path).exists()]
        assert missing == []


def test_non_aggregate_classifications_do_not_overlap_aggregate_package() -> None:
    payload = _load_yaml(CLASSIFICATION_PATH)
    non_aggregate_paths = [
        *(str(row["path"]) for row in payload["non_aggregate_clusters"]),
        *(str(row["path"]) for row in payload["non_aggregate_root_modules"]),
    ]

    assert not [
        path
        for path in non_aggregate_paths
        if path.startswith("src/bioetl/domain/aggregates")
    ]
    assert len(non_aggregate_paths) == len(set(non_aggregate_paths))
