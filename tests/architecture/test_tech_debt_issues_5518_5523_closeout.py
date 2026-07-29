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
"""Closeout guardrails for technical-debt issues #5518-#5523."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5518-5523-closeout.json"
COMPATIBILITY_CENSUS = (
    ROOT / "reports" / "quality" / "compatibility-importer-census.json"
)
CONFIG_SURFACE_BACKLOG = ROOT / "reports" / "quality" / "config-surface-backlog.json"
ENTITY_METADATA_REGISTRY = (
    ROOT / "configs" / "quality" / "entity_contract_metadata_registry.yaml"
)
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
CLI_BOOTSTRAP_CONFIG = (
    ROOT / "src" / "bioetl" / "composition" / "bootstrap" / "cli" / "config.py"
)
RUNTIME_CONFIG_ACCESS = (
    ROOT / "src" / "bioetl" / "composition" / "runtime_builders" / "config_access.py"
)
DOMAIN_COMPOSITE_INIT = ROOT / "src" / "bioetl" / "domain" / "composite" / "__init__.py"
PRIVATE_RUN_MANIFEST_HELPER = (
    ROOT
    / "src"
    / "bioetl"
    / "interfaces"
    / "cli"
    / "commands"
    / "_run_manifest_output_support.py"
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


def test_closeout_artifact_covers_requested_issues__5518_5523() -> None:
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]

    assert payload["schema_version"] == "tech-debt-issues-5518-5523-closeout-v1"
    assert payload["debt_budget_outcome"] == "reduced_or_unchanged"
    assert {issue["number"] for issue in issues} == {5518, 5519, 5520, 5521, 5522, 5523}
    assert all(issue["status"] == "closed-ready" for issue in issues)

    for issue in issues:
        for relative_path in issue["evidence"]:
            assert (ROOT / relative_path).exists(), (
                f"Missing closeout evidence for #{issue['number']}: {relative_path}"
            )


def test_issue_5518_cli_bootstrap_config_uses_owner_loader_seam() -> None:
    source = CLI_BOOTSTRAP_CONFIG.read_text(encoding="utf-8")
    runtime_source = RUNTIME_CONFIG_ACCESS.read_text(encoding="utf-8")

    assert "create_dq_config_loader" in source
    assert "load_dq_config_for_pipeline" not in source
    assert "def create_dq_config_loader(" in runtime_source


def test_issue_5519_health_api_has_zero_src_importers() -> None:
    payload = _load_json(COMPATIBILITY_CENSUS)
    row = _retained_entrypoint(payload, "src/bioetl/composition/health_api.py")

    assert row["internal_callers_zero"] is True
    assert row["src_importer_count"] == 0
    assert row["src_importers"] == []


def test_issue_5520_domain_composite_config_root_facade_stays_zero_src_importers() -> (
    None
):
    payload = _load_json(COMPATIBILITY_CENSUS)
    row = _retained_entrypoint(payload, "src/bioetl/domain/composite/config.py")
    tree = ast.parse(DOMAIN_COMPOSITE_INIT.read_text(encoding="utf-8"))

    assert row["src_importer_count"] == 0
    assert row["src_importers"] == []
    assert all(
        node.module != "bioetl.domain.composite.config"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )


def test_issue_5521_run_manifest_output_twin_pair_removed() -> None:
    payload = _load_json(COMPATIBILITY_CENSUS)

    assert PRIVATE_RUN_MANIFEST_HELPER.exists() is False
    assert payload["summary"]["twin_pair_count"] == 0


def test_issue_5522_entity_quality_metadata_registry_replaces_inline_duplicates() -> (
    None
):
    registry = _load_yaml(ENTITY_METADATA_REGISTRY)
    backlog = _load_json(CONFIG_SURFACE_BACKLOG)
    profiles = registry["profiles"]
    shared = profiles["shared_entity_quality_metadata"]
    cluster_paths = {
        cluster["block_path"]
        for cluster in backlog["duplication_audit"]["clusters"]
        if isinstance(cluster, dict)
    }

    assert len(shared["applies_to"]) == 22
    assert "quality_metadata" in shared
    assert all("quality.metadata" not in block_path for block_path in cluster_paths)

    for relative_path in shared["applies_to"]:
        payload = yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        quality = payload.get("quality")
        assert isinstance(quality, dict)
        assert "metadata" not in quality


def test_issue_5523_observability_freshness_limit_is_tightened_and_passing() -> None:
    payload = _load_json(DEBT_GATES)
    gates = {row["name"]: row for row in payload["gates"] if isinstance(row, dict)}
    freshness = gates["observability_release_review_freshness"]

    assert freshness["limit"] == 21
    assert freshness["status"] == "pass"
