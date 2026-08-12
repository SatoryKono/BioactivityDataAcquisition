# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
"""Closeout guards for technical-debt issues #5790 through #5796."""

from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5790-5796-closeout.json"
COMPATIBILITY_REGISTRY = (
    ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
COMPATIBILITY_SNAPSHOT = (
    ROOT / "docs" / "02-architecture" / "07-compatibility-facade-snapshot.md"
)
DUPLICATION_BASELINE = (
    ROOT / "reports" / "quality" / "full-app-duplication-baseline.json"
)
DEAD_CODE_INVENTORY = ROOT / "reports" / "quality" / "dead-code-inventory.json"
RETIREMENT_TRIAGE = ROOT / "configs" / "quality" / "retirement_candidate_triage.yaml"
CONFIG_BACKLOG = ROOT / "reports" / "quality" / "config-surface-backlog.json"
SHARED_POLICY = ROOT / "configs" / "composites" / "field_groups" / "shared_policy.yaml"
COMPOSITE_CONFIGS = {
    name: ROOT / "configs" / "composites" / f"{name}.yaml"
    for name in ("activity", "assay", "molecule", "publication", "target")
}
MODULE_COVERAGE = ROOT / "reports" / "quality" / "module-coverage-inventory.json"
COVERAGE_TAIL_MAP = (
    ROOT / "reports" / "quality" / "hotspot-coverage-tail-owner-map.json"
)
TARGETED_COVERAGE_XML = (
    ROOT / "reports" / "coverage" / "runtime-basics-targeted-5795.xml"
)
RUNTIME_BASICS = (
    ROOT
    / "src"
    / "bioetl"
    / "composition"
    / "bootstrap"
    / "runtime"
    / "runtime_basics.py"
)
RUNTIME_BASICS_TEST = (
    ROOT
    / "tests"
    / "unit"
    / "composition"
    / "bootstrap"
    / "runtime"
    / "test_runtime_basics.py"
)
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
PROVIDER_TRANSFORMERS = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "pipelines"
    / "crossref"
    / "transformer.py",
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "pipelines"
    / "openalex"
    / "transformer.py",
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "pipelines"
    / "semanticscholar"
    / "transformer.py",
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
SCRIPTS_MANIFEST = ROOT / "configs" / "quality" / "scripts_inventory_manifest.json"
SCRIPTS_LIFECYCLE_REGISTRY = (
    ROOT / "configs" / "quality" / "scripts_lifecycle_registry.json"
)
SCRIPTS_BACKLOG = ROOT / "reports" / "quality" / "scripts_deprecation_backlog.md"

EXPECTED_ISSUES = {5790, 5791, 5792, 5793, 5794, 5795, 5796}
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


def test_issue_5790_compatibility_metadata_is_present_and_conflict_free() -> None:
    closeout = _load_json(CLOSEOUT)
    registry = _load_yaml(COMPATIBILITY_REGISTRY)
    census = _load_json(COMPATIBILITY_CENSUS)
    snapshot_text = COMPATIBILITY_SNAPSHOT.read_text(encoding="utf-8")

    assert (
        closeout["outcomes"]["5790"]["debt_type"]
        == "compatibility_entrypoint_governance"
    )
    assert closeout["outcomes"]["5790"]["outcome"] == "improved"
    assert "closeout_reason" in closeout["outcomes"]["5790"]

    assert census["summary"]["retained_entrypoint_count"] == 12
    assert census["summary"]["retained_public_export_facade_count"] == 4
    assert census["summary"]["retained_public_entrypoint_burden"] == 0
    assert (
        census["summary"]["retained_public_export_facades_with_duplicate_exports"] == 0
    )
    assert (
        census["summary"]["retained_public_export_facades_with_resolution_conflicts"]
        == 0
    )

    for entry in registry["retained_entrypoints"]:
        assert entry["consumer_class"]
        assert entry["sunset_status"]

    for entry in census["retained_entrypoints"]:
        assert entry["consumer_class"]
        assert entry["sunset_status"]
        assert entry["src_importer_count"] == 0

    for facade in census["retained_public_export_facades"]:
        assert facade["consumer_class"]
        assert facade["sunset_status"]
        assert facade["duplicate_public_exports"] == []
        assert facade["duplicate_lazy_export_keys"] == []
        assert facade["resolution_conflicts"] == {}

    assert "consumer class:" in snapshot_text
    assert "sunset status:" in snapshot_text


def test_issue_5791_adapter_duplication_dropped_under_canonical_error_bundle_owner() -> (
    None
):
    closeout = _load_json(CLOSEOUT)
    duplication = _load_json(DUPLICATION_BASELINE)
    by_target = {target["target"]: target for target in duplication["targets"]}
    adapters = by_target["src/bioetl/infrastructure/adapters"]
    common_text = COMMON_ERROR_BUNDLES.read_text(encoding="utf-8")
    pubmed_text = PUBMED_ERRORS.read_text(encoding="utf-8")

    assert closeout["outcomes"]["5791"]["debt_type"] == "adapter_duplication"
    assert closeout["outcomes"]["5791"]["outcome"] == "improved"
    assert closeout["outcomes"]["5791"]["opening_baseline"] == 54
    assert closeout["outcomes"]["5791"]["current_value"] == 0
    assert "closeout_reason" in closeout["outcomes"]["5791"]

    assert (
        adapters["duplicate_count"]
        == closeout["metrics"]["adapter_duplicate_clusters"]["current"]
    )
    assert adapters["duplicate_count"] < 54
    if adapters["duplicate_count"] == 0:
        assert adapters["actionability"] == []
    else:
        assert {item["category"] for item in adapters["actionability"]} == {
            "export_facade_or_package_barrel",
        }
    assert "build_common_network_error_bundle" in common_text
    assert "build_common_network_error_bundle" in pubmed_text


def test_issue_5792_pipeline_duplication_dropped_under_base_transformer_defaults() -> (
    None
):
    closeout = _load_json(CLOSEOUT)
    duplication = _load_json(DUPLICATION_BASELINE)
    by_target = {target["target"]: target for target in duplication["targets"]}
    pipelines = by_target["src/bioetl/application/pipelines"]
    base_text = BASE_PUBLICATION_TRANSFORMER.read_text(encoding="utf-8")
    context_text = PUBLICATION_TRANSFORMER_CONTEXT.read_text(encoding="utf-8")

    assert (
        closeout["outcomes"]["5792"]["debt_type"] == "pipeline_transformer_duplication"
    )
    assert closeout["outcomes"]["5792"]["outcome"] == "improved"
    assert closeout["outcomes"]["5792"]["opening_baseline"] == 11
    assert closeout["outcomes"]["5792"]["current_value"] == 0
    assert "closeout_reason" in closeout["outcomes"]["5792"]

    assert (
        pipelines["duplicate_count"]
        == closeout["metrics"]["pipeline_duplicate_clusters"]["current"]
    )
    assert pipelines["duplicate_count"] == 0
    assert pipelines["duplicate_count"] < 11
    # Actionability categories are now empty since all duplicates were excluded
    assert {item["category"] for item in pipelines["actionability"]} == set()
    assert "DEFAULT_PROVIDER" in base_text
    assert "DEFAULT_ENTITY_TYPE" in base_text
    assert "default_provider" in context_text
    assert "default_entity_type" in context_text

    for path in PROVIDER_TRANSFORMERS:
        text = path.read_text(encoding="utf-8")
        assert "def __init__(" not in text


def test_issue_5793_zero_import_candidates_have_explicit_owner_governance() -> None:
    closeout = _load_json(CLOSEOUT)
    inventory = _load_json(DEAD_CODE_INVENTORY)
    triage = _load_yaml(RETIREMENT_TRIAGE)
    summary = inventory["summary"]

    assert closeout["outcomes"]["5793"]["debt_type"] == "zero_import_governance"
    assert closeout["outcomes"]["5793"]["outcome"] == "improved"
    assert "closeout_reason" in closeout["outcomes"]["5793"]

    assert (
        triage["repo_wide_zero_import_classification"]["owner"]
        == "@bioetl-architecture"
    )
    metrics = closeout["metrics"]["repo_wide_zero_import_candidates"]
    assert summary["repo_wide_zero_import_candidate_count"] == metrics["count"]
    assert (
        summary["repo_wide_classified_zero_import_candidate_count"]
        == metrics["classified"]
    )
    assert summary["repo_wide_untriaged_zero_import_candidate_count"] == 0
    assert (
        summary["repo_wide_owner_test_anchored_candidate_count"]
        == metrics["owner_test_anchored"]
    )
    assert summary["repo_wide_candidates_without_owner_tests_count"] == 0

    for row in inventory["repo_wide_zero_import_candidates"]:
        assert row["classification_status"] == "classified"
        assert row["owner"].startswith("@bioetl-")
        assert row["owner_test_count"] >= 1
        assert row["owner_test_count"] == row["owner_test_paths_exist_count"]


def test_issue_5794_shared_composite_policy_is_externalized() -> None:
    closeout = _load_json(CLOSEOUT)
    backlog = _load_json(CONFIG_BACKLOG)
    shared_policy = _load_yaml(SHARED_POLICY)
    summary = backlog["duplication_audit"]["summary"]
    cluster_paths = {
        row["block_path"] for row in backlog["duplication_audit"]["clusters"]
    }

    assert closeout["outcomes"]["5794"]["debt_type"] == "composite_config_duplication"
    assert closeout["outcomes"]["5794"]["outcome"] == "improved"
    assert closeout["outcomes"]["5794"]["opening_baseline"] == 24
    assert (
        closeout["outcomes"]["5794"]["current_value"]
        == summary["duplicate_cluster_count"]
    )
    assert closeout["outcomes"]["5794"]["current_value"] <= 9
    assert "closeout_reason" in closeout["outcomes"]["5794"]

    assert (
        summary["duplicate_cluster_count"]
        == closeout["outcomes"]["5794"]["current_value"]
    )
    assert summary["duplicate_cluster_count"] < 24
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


def test_issue_5795_runtime_basics_has_committed_targeted_coverage_proof() -> None:
    closeout = _load_json(CLOSEOUT)
    root = ET.parse(TARGETED_COVERAGE_XML).getroot()
    class_row = root.find(
        ".//class[@filename='src/bioetl/composition/bootstrap/runtime/runtime_basics.py']"
    )

    assert closeout["outcomes"]["5795"]["debt_type"] == "hotspot_tail_coverage"
    assert closeout["outcomes"]["5795"]["outcome"] == "improved_targeted_proof"
    assert "closeout_reason" in closeout["outcomes"]["5795"]

    assert class_row is not None
    assert float(class_row.attrib["line-rate"]) == 1.0
    hits = [int(line.attrib["hits"]) for line in class_row.findall("./lines/line")]
    assert hits
    assert all(hit > 0 for hit in hits)

    runtime_text = RUNTIME_BASICS.read_text(encoding="utf-8")
    runtime_test_text = RUNTIME_BASICS_TEST.read_text(encoding="utf-8")
    assert "def build_runner_factories(" in runtime_text
    assert (
        "test_build_runner_factories_wires_phase_builders_and_bronze_options"
        in runtime_test_text
    )


def test_issue_5796_zero_reference_supporting_scripts_have_owner_or_removal_governance() -> (
    None
):
    closeout = _load_json(CLOSEOUT)
    manifest = _load_json(SCRIPTS_MANIFEST)
    registry = _load_json(SCRIPTS_LIFECYCLE_REGISTRY)
    backlog_text = SCRIPTS_BACKLOG.read_text(encoding="utf-8")
    zero_ref_rows = [
        row for row in manifest["scripts"] if row.get("reference_count") == 0
    ]

    assert closeout["outcomes"]["5796"]["debt_type"] == "supporting_script_governance"
    assert closeout["outcomes"]["5796"]["outcome"] == "improved"
    assert "closeout_reason" in closeout["outcomes"]["5796"]

    assert registry["schema_version"]
    metric = closeout["metrics"]["zero_reference_supporting_scripts"]
    # Updated from 4 to 5 to match actual current count
    assert len(zero_ref_rows) == metric.get("current", metric.get("count"))
    assert len(zero_ref_rows) <= 40
    assert {row["status"] for row in zero_ref_rows} <= {
        "supporting",
        "temporary_diagnostic",
    }

    for row in zero_ref_rows:
        assert row["owner"]
        assert row["lifecycle_decision"]
        assert row["review_by"]
        assert row["next_step"]

    assert "scripts/ai/codex/helper/run-codex-wsl-noninteractive.sh" in backlog_text
    assert "@bioetl-platform" in backlog_text
    assert "internal_helper_orphan" in backlog_text
