"""Closeout guardrails for technical-debt issues #5524-#5528."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5524-5528-closeout.json"
COMPATIBILITY_CENSUS = ROOT / "reports" / "quality" / "compatibility-importer-census.json"
CONFIG_SURFACE_BACKLOG = ROOT / "reports" / "quality" / "config-surface-backlog.json"
FILTER_METADATA_REGISTRY = (
    ROOT / "configs" / "quality" / "entity_filter_metadata_registry.yaml"
)
COMPATIBILITY_INVENTORY = (
    ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
MODULE_COVERAGE_GATES = ROOT / "configs" / "quality" / "module_coverage_gates.yaml"
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
REMOVED_COMPOSITE_WRAPPER = (
    ROOT
    / "src"
    / "bioetl"
    / "interfaces"
    / "cli"
    / "commands"
    / "domains"
    / "composite"
    / "command.py"
)


FILTER_METADATA_TARGETS = (
    "configs/entities/chembl/assay_parameters.yaml",
    "configs/entities/chembl/cell_line.yaml",
    "configs/entities/chembl/compound_record.yaml",
    "configs/entities/chembl/molecule.yaml",
    "configs/entities/chembl/protein_class.yaml",
    "configs/entities/chembl/publication.yaml",
    "configs/entities/chembl/publication_similarity.yaml",
    "configs/entities/chembl/publication_term.yaml",
    "configs/entities/chembl/subcellular_fraction.yaml",
    "configs/entities/chembl/target_component.yaml",
    "configs/entities/chembl/target_protein_classification.yaml",
    "configs/entities/chembl/tissue.yaml",
    "configs/entities/crossref/publication.yaml",
    "configs/entities/openalex/publication.yaml",
    "configs/entities/pubchem/compound.yaml",
    "configs/entities/pubmed/publication.yaml",
    "configs/entities/semanticscholar/publication.yaml",
    "configs/entities/uniprot/idmapping.yaml",
    "configs/entities/uniprot/protein.yaml",
)

SINK_DEDUP_TARGETS = (
    "configs/entities/chembl/cell_line.yaml",
    "configs/entities/chembl/compound_record.yaml",
    "configs/entities/chembl/subcellular_fraction.yaml",
    "configs/entities/chembl/tissue.yaml",
    "configs/entities/crossref/publication.yaml",
    "configs/entities/openalex/publication.yaml",
    "configs/entities/pubchem/compound.yaml",
    "configs/entities/semanticscholar/publication.yaml",
    "configs/entities/uniprot/idmapping.yaml",
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _retained_entrypoint(payload: dict[str, Any], path: str) -> dict[str, Any]:
    rows = payload["retained_entrypoints"]
    assert isinstance(rows, list)
    for row in rows:
        if isinstance(row, dict) and row.get("path") == path:
            return row
    raise AssertionError(f"Missing retained entrypoint row for {path}")


def test_closeout_artifact_covers_requested_issues__5524_5528() -> None:
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]

    assert payload["schema_version"] == "tech-debt-issues-5524-5528-closeout-v1"
    assert payload["debt_budget_outcome"] == "reduced_or_unchanged"
    assert {issue["number"] for issue in issues} == {5524, 5525, 5526, 5527, 5528}
    assert all(issue["status"] == "closed-ready" for issue in issues)

    for issue in issues:
        for relative_path in issue["evidence"]:
            assert (ROOT / relative_path).exists(), (
                f"Missing closeout evidence for #{issue['number']}: {relative_path}"
            )


def test_issue_5524_filter_metadata_registry_replaces_inline_duplicates() -> None:
    registry = _load_yaml(FILTER_METADATA_REGISTRY)
    backlog = _load_json(CONFIG_SURFACE_BACKLOG)
    shared = registry["profiles"]["shared_publication_filter_metadata"]
    cluster_paths = {
        cluster["block_path"]
        for cluster in backlog["duplication_audit"]["clusters"]
        if isinstance(cluster, dict)
    }

    assert tuple(shared["applies_to"]) == FILTER_METADATA_TARGETS
    assert "filter_metadata" in shared
    assert "filters.metadata" not in cluster_paths
    assert "filters.metadata.publication_filter_policy" not in cluster_paths

    for relative_path in FILTER_METADATA_TARGETS:
        payload = _load_yaml(ROOT / relative_path)
        filters = payload.get("filters")
        assert isinstance(filters, dict)
        assert "metadata" not in filters


def test_issue_5525_pipeline_sink_shell_is_deduplicated_from_raw_entity_configs() -> (
    None
):
    backlog = _load_json(CONFIG_SURFACE_BACKLOG)
    cluster_paths = {
        cluster["block_path"]
        for cluster in backlog["duplication_audit"]["clusters"]
        if isinstance(cluster, dict)
    }

    assert "pipeline.sink" not in cluster_paths

    for relative_path in SINK_DEDUP_TARGETS:
        payload = _load_yaml(ROOT / relative_path)
        pipeline = payload.get("pipeline")
        assert isinstance(pipeline, dict)
        assert "sink" not in pipeline


def test_issue_5526_module_coverage_warning_debt_is_replaced_with_reviewed_ratchets() -> (
    None
):
    gates_policy = _load_yaml(MODULE_COVERAGE_GATES)
    debt_gates = _load_json(DEBT_GATES)
    gate_rows = {row["name"]: row for row in debt_gates["gates"] if isinstance(row, dict)}
    aggregate_ratchets = gates_policy["aggregate_residual_ratchets"]

    assert aggregate_ratchets["mode"] == "fail-fast-current-inventory"
    assert aggregate_ratchets["unmeasured_module_count"]["max_count"] == 0
    assert aggregate_ratchets["uncovered_module_count"]["max_count"] == 0
    assert gate_rows["module_coverage_unmeasured_modules"]["status"] == "pass"
    assert gate_rows["module_coverage_uncovered_modules"]["status"] == "pass"
    assert (
        gate_rows["module_coverage_unmeasured_modules"]["source_artifact"]
        == "configs/quality/module_coverage_gates.yaml#aggregate_residual_ratchets"
    )


def test_issue_5527_internal_composite_wrapper_dependency_is_removed() -> None:
    payload = _load_json(COMPATIBILITY_CENSUS)
    row = _retained_entrypoint(
        payload,
        "src/bioetl/interfaces/cli/commands/run_composite.py",
    )

    assert REMOVED_COMPOSITE_WRAPPER.exists() is False
    assert row["src_importer_count"] == 0
    assert row["src_importers"] == []
    assert row["internal_callers_zero"] is True


def test_issue_5528_entrypoints_public_export_budget_is_ratchet_down() -> None:
    payload = _load_json(COMPATIBILITY_CENSUS)
    inventory = _load_yaml(COMPATIBILITY_INVENTORY)
    row = _retained_entrypoint(payload, "src/bioetl/composition/entrypoints.py")
    tracked_rows = inventory["retained_entrypoints"]
    inventory_row = next(
        item
        for item in tracked_rows
        if isinstance(item, dict)
        and item.get("path") == "src/bioetl/composition/entrypoints.py"
    )

    assert row["public_export_count"] == 13
    assert row["internal_callers_zero"] is True
    assert (
        inventory_row["public_export_contract"]["max_public_exports"] == 13
    )
