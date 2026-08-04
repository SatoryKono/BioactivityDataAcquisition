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
"""Closeout guards for TDX audit issues #5839 through #5845."""

from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5839-5845-closeout.json"
COMPATIBILITY_REGISTRY = (
    ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
DUPLICATION_BASELINE = (
    ROOT / "reports" / "quality" / "full-app-duplication-baseline.json"
)
DEAD_CODE_INVENTORY = ROOT / "reports" / "quality" / "dead-code-inventory.json"
RETIREMENT_TRIAGE = ROOT / "configs" / "quality" / "retirement_candidate_triage.yaml"
CONFIG_BACKLOG = ROOT / "reports" / "quality" / "config-surface-backlog.json"
SHARED_POLICY = ROOT / "configs" / "composites" / "field_groups" / "shared_policy.yaml"
MODULE_COVERAGE = ROOT / "reports" / "quality" / "module-coverage-inventory.json"
COVERAGE_TAIL_MAP = (
    ROOT / "reports" / "quality" / "hotspot-coverage-tail-owner-map.json"
)
TARGETED_COVERAGE_XML = (
    ROOT / "reports" / "coverage" / "runtime-basics-targeted-5795.xml"
)
SCRIPTS_MANIFEST = ROOT / "configs" / "quality" / "scripts_inventory_manifest.json"
SCRIPTS_LIFECYCLE_REGISTRY = (
    ROOT / "configs" / "quality" / "scripts_lifecycle_registry.json"
)
SCRIPTS_BACKLOG = ROOT / "reports" / "quality" / "scripts_deprecation_backlog.md"
BASE_PUBLICATION_TRANSFORMER = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "pipelines"
    / "common"
    / "base_publication_transformer.py"
)
PUBLICATION_TRANSFORMER_CONTEXT = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "pipelines"
    / "common"
    / "publication_transformer_context.py"
)
COMMON_ERROR_BUNDLES = (
    ROOT
    / "src"
    / "bioetl"
    / "infrastructure"
    / "adapters"
    / "common"
    / "error_bundles.py"
)
PUBMED_ERRORS = (
    ROOT / "src" / "bioetl" / "infrastructure" / "adapters" / "pubmed" / "_errors.py"
)
COMPOSITE_CONFIGS = {
    name: ROOT / "configs" / "composites" / f"{name}.yaml"
    for name in ("activity", "assay", "molecule", "publication", "target")
}
EXPECTED_ISSUES = {5839, 5840, 5841, 5842, 5843, 5844, 5845}
EXPECTED_SHARED_CLUSTER_PATHS = {
    "composite.normalized_anchor_policy",
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_5839_retained_public_seams_are_metadata_backed_and_zero_burden() -> None:
    closeout = _load_json(CLOSEOUT)
    registry = _load_yaml(COMPATIBILITY_REGISTRY)
    census = _load_json(COMPATIBILITY_CENSUS)
    summary = census["summary"]

    assert closeout["metrics"]["retained_public_entrypoints"]["current"] == 12
    assert closeout["metrics"]["retained_public_export_facades"]["current"] == 4
    assert summary["retained_entrypoint_count"] == 12
    assert summary["retained_public_export_facade_count"] == 4
    assert summary["retained_public_entrypoint_burden"] == 0
    assert summary["removed_compatibility_surface_count"] >= 23
    assert summary["retained_public_export_facades_with_duplicate_exports"] == 0
    assert summary["retained_public_export_facades_with_resolution_conflicts"] == 0

    for entry in registry["retained_entrypoints"]:
        assert entry["consumer_class"]
        assert entry["sunset_status"]

    for entry in census["retained_entrypoints"]:
        assert entry["owner"]
        assert entry["consumer_class"]
        assert entry["sunset_status"]
        assert entry["src_importer_count"] == 0

    for facade in census["retained_public_export_facades"]:
        assert facade["owner"]
        assert facade["consumer_class"]
        assert facade["sunset_status"]
        assert facade["duplicate_public_exports"] == []
        assert facade["duplicate_lazy_export_keys"] == []
        assert facade["resolution_conflicts"] == {}


def test_issue_5840_adapter_duplication_is_below_audit_baseline() -> None:
    closeout = _load_json(CLOSEOUT)
    duplication = _load_json(DUPLICATION_BASELINE)
    by_target = {target["target"]: target for target in duplication["targets"]}
    adapters = by_target["src/bioetl/infrastructure/adapters"]

    assert (
        adapters["duplicate_count"]
        == closeout["metrics"]["adapter_duplicate_clusters"]["current"]
    )
    assert (
        adapters["duplicate_count"]
        < closeout["metrics"]["adapter_duplicate_clusters"]["previous_audit_baseline"]
    )
    if adapters["duplicate_count"] == 0:
        assert adapters["actionability"] == []
    else:
        assert {item["category"] for item in adapters["actionability"]} == {
            "export_facade_or_package_barrel",
        }
    assert "build_common_network_error_bundle" in COMMON_ERROR_BUNDLES.read_text(
        encoding="utf-8"
    )
    assert "build_common_network_error_bundle" in PUBMED_ERRORS.read_text(
        encoding="utf-8"
    )


def test_issue_5841_pipeline_transformer_duplication_is_below_audit_baseline() -> None:
    closeout = _load_json(CLOSEOUT)
    duplication = _load_json(DUPLICATION_BASELINE)
    by_target = {target["target"]: target for target in duplication["targets"]}
    pipelines = by_target["src/bioetl/application/pipelines"]
    base_text = BASE_PUBLICATION_TRANSFORMER.read_text(encoding="utf-8")
    context_text = PUBLICATION_TRANSFORMER_CONTEXT.read_text(encoding="utf-8")

    assert (
        pipelines["duplicate_count"]
        == closeout["metrics"]["pipeline_duplicate_clusters"]["current"]
    )
    assert (
        pipelines["duplicate_count"]
        < closeout["metrics"]["pipeline_duplicate_clusters"]["previous_audit_baseline"]
    )
    # Actionability categories are now empty since all duplicates were excluded
    assert {item["category"] for item in pipelines["actionability"]} == set()
    assert "DEFAULT_PROVIDER" in base_text
    assert "DEFAULT_ENTITY_TYPE" in base_text
    assert "default_provider" in context_text
    assert "default_entity_type" in context_text


def test_issue_5842_zero_import_candidates_are_fully_governed() -> None:
    closeout = _load_json(CLOSEOUT)
    inventory = _load_json(DEAD_CODE_INVENTORY)
    triage = _load_yaml(RETIREMENT_TRIAGE)
    summary = inventory["summary"]

    assert (
        triage["repo_wide_zero_import_classification"]["owner"]
        == "@bioetl-architecture"
    )
    assert (
        summary["repo_wide_zero_import_candidate_count"]
        == closeout["metrics"]["repo_wide_zero_import_candidates"]["current"]
    )
    assert (
        summary["repo_wide_classified_zero_import_candidate_count"]
        == closeout["metrics"]["repo_wide_zero_import_candidates"]["classified"]
    )
    assert summary["repo_wide_untriaged_zero_import_candidate_count"] == 0
    assert summary["repo_wide_candidates_without_owner_tests_count"] == 0
    assert (
        summary["repo_wide_owner_test_anchored_candidate_count"]
        == closeout["metrics"]["repo_wide_zero_import_candidates"][
            "owner_test_anchored"
        ]
    )

    for row in inventory["repo_wide_zero_import_candidates"]:
        assert row["classification_status"] == "classified"
        assert row["owner"].startswith("@bioetl-")
        assert row["owner_test_count"] >= 1
        assert row["owner_test_count"] == row["owner_test_paths_exist_count"]


def test_issue_5843_composite_shared_policy_has_single_authority_surface() -> None:
    closeout = _load_json(CLOSEOUT)
    backlog = _load_json(CONFIG_BACKLOG)
    shared_policy = _load_yaml(SHARED_POLICY)
    summary = backlog["duplication_audit"]["summary"]
    cluster_paths = {
        row["block_path"] for row in backlog["duplication_audit"]["clusters"]
    }

    assert (
        summary["duplicate_cluster_count"]
        <= closeout["metrics"]["config_surface_duplicate_clusters"]["current"]
    )
    assert summary["duplicate_cluster_count"] <= 23
    assert (
        summary["duplicate_cluster_count"]
        < closeout["metrics"]["config_surface_duplicate_clusters"][
            "previous_audit_baseline"
        ]
    )
    assert shared_policy["merge"]["field_priorities"]
    assert shared_policy["merge"]["field_mappings"]
    assert shared_policy["lineage"]["provider_lookup_fields"]
    assert EXPECTED_SHARED_CLUSTER_PATHS.issubset(cluster_paths)

    for path in COMPOSITE_CONFIGS.values():
        raw = _load_yaml(path)
        assert (
            raw["maintenance"]["composite_shared_policy_file"]
            == "field_groups/shared_policy.yaml"
        )
        assert raw.get("merge", {}) == {}
        assert raw.get("lineage", {}) == {}


def test_issue_5844_runtime_tail_has_targeted_behavioral_coverage_evidence() -> None:
    closeout = _load_json(CLOSEOUT)
    tail_map = _load_json(COVERAGE_TAIL_MAP)
    family_row = next(
        row
        for row in tail_map["families"]
        if row["family"] == "composition_bootstrap_runtime"
    )
    root = ET.parse(TARGETED_COVERAGE_XML).getroot()
    class_row = root.find(
        ".//class[@filename='src/bioetl/composition/bootstrap/runtime/runtime_basics.py']"
    )

    assert family_row["owner_tests"] == [
        "tests/unit/composition/bootstrap/runtime/test_runtime_basics.py"
    ]
    assert class_row is not None
    assert (
        float(class_row.attrib["line-rate"])
        == closeout["metrics"]["runtime_basics_coverage_percent"]["targeted_line_rate"]
    )
    assert all(
        int(line.attrib["hits"]) > 0 for line in class_row.findall("./lines/line")
    )


def test_issue_5845_zero_reference_supporting_scripts_have_owner_or_removal_metadata() -> (
    None
):
    closeout = _load_json(CLOSEOUT)
    manifest = _load_json(SCRIPTS_MANIFEST)
    registry = _load_json(SCRIPTS_LIFECYCLE_REGISTRY)
    backlog_text = SCRIPTS_BACKLOG.read_text(encoding="utf-8")
    zero_ref_rows = [
        row for row in manifest["scripts"] if row.get("reference_count") == 0
    ]

    assert registry["schema_version"]
    assert (
        len(zero_ref_rows)
        == closeout["metrics"]["zero_reference_supporting_scripts"]["current"]
    )
    assert {row["status"] for row in zero_ref_rows} <= {
        "supporting",
        "temporary_diagnostic",
    }

    missing_metadata = [
        row["path"]
        for row in zero_ref_rows
        if not row["owner"]
        or not row["lifecycle_decision"]
        or not row["review_by"]
        or not row["next_step"]
    ]
    assert missing_metadata == []
    assert (
        closeout["metrics"]["zero_reference_supporting_scripts"][
            "entries_without_owner_metadata"
        ]
        == 0
    )
    assert "internal_helper_orphan" in backlog_text
    assert "@bioetl-platform" in backlog_text
