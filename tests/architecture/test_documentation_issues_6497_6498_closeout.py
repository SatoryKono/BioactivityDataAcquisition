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
"""Regression guards for documentation issues #6494, #6495, #6497-#6499."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
from tests.architecture.quality_artifacts import (
    load_quality_json,
    quality_artifact_path,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _exports(path: str) -> set[str]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in node.targets
            )
            and isinstance(node.value, (ast.List, ast.Tuple))
        ):
            return {
                item.value
                for item in node.value.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            }
    raise AssertionError(f"missing literal __all__ in {path}")


def test_domain_public_facades_have_documented_classification() -> None:
    doc = (
        ROOT / "docs/04-reference/domain/symbol-invariant-traceability.md"
    ).read_text(encoding="utf-8")
    for facade in ("aggregates", "value_objects", "control_plane"):
        exports = _exports(f"src/bioetl/domain/{facade}/__init__.py")
        missing = sorted(symbol for symbol in exports if f"`{symbol}`" not in doc)
        assert not missing, f"{facade} exports missing from traceability: {missing}"


def test_aggregate_registry_anchors_resolve() -> None:
    registry = json.loads(
        (quality_artifact_path("domain-aggregate-invariant-registry.json")).read_text(
            encoding="utf-8"
        )
    )
    assert registry["aggregate_root_count"] == 3
    for row in registry["aggregates"]:
        assert (ROOT / row["root_module"]).is_file()
        assert all((ROOT / path).is_file() for path in row["implementation_modules"])
        assert row["invariants"]
        assert row["test_paths"]
        assert all((ROOT / path).exists() for path in row["test_paths"])


def test_pipeline_contract_matrix_matches_active_inventory() -> None:
    report = json.loads(
        (quality_artifact_path("contract-coverage-matrix.json")).read_text(
            encoding="utf-8"
        )
    )
    section = (ROOT / "docs/04-reference/pipelines/contract-facet-matrix.md").read_text(
        encoding="utf-8"
    )
    documented = set(re.findall(r"^\| `([^`]+)` \|", section, re.MULTILINE))
    expected = {row["pipeline_name"] for row in report["rows"]}
    assert report["row_count"] == 27
    assert documented == expected
    for row in report["rows"]:
        assert row["primary_key_fields"]
        assert row["published_contract_nullable_policy_declared"] is True
        assert row["gold_strict_validation_declared"] is True
        assert row["contract_yaml_path"] in section


def test_publication_runbook_uses_supported_read_only_surfaces() -> None:
    runbook = (
        ROOT / "docs/05-operations/runbooks/publication-validation-runbook.md"
    ).read_text(encoding="utf-8")
    forbidden = (
        "read_parquet",
        "read-parquet",
        "to_parquet",
        "--skip-external",
        "--skip-semantic",
    )
    assert all(token not in runbook for token in forbidden)
    assert "DeltaTable" in runbook
    assert "quarantine payload and payload hash are immutable" in runbook.lower()


def test_dq_recovery_does_not_recommend_threshold_weakening() -> None:
    runbook = (ROOT / "docs/05-operations/runbooks/pipeline-failure-dq.md").read_text(
        encoding="utf-8"
    )
    assert "Temporarily increase threshold" not in runbook
    assert "hard_fail_threshold: 0.30" not in runbook
    assert "deterministic replay" in runbook


def test_monitoring_guide_routes_panel_detail_to_all_shipped_panel_docs() -> None:
    guide_path = ROOT / "docs/05-operations/01-monitoring-guide.md"
    guide = guide_path.read_text(encoding="utf-8")
    dashboard_stems = {
        path.stem for path in (ROOT / "grafana/dashboards").glob("*.json")
    }
    panel_doc_names = {
        path.name
        for path in (ROOT / "docs/03-guides/dashboards/panels").glob("*-panels.md")
    }
    missing_panel_docs = sorted(
        f"{dashboard_stem}-panels.md"
        for dashboard_stem in dashboard_stems
        if f"{dashboard_stem}-panels.md" not in panel_doc_names
    )
    assert len(dashboard_stems) == 7
    assert not missing_panel_docs, missing_panel_docs
    assert "dashboard-inventory.md" in guide, (
        f"{guide_path} must route inventory ownership to dashboard-inventory.md"
    )
    assert "*-panels.md" in guide, (
        f"{guide_path} must keep an explicit panel-detail ownership pointer "
        "containing the literal token '*-panels.md' (do not inline panel catalogs)"
    )
    guide_lines = len(guide.splitlines())
    assert guide_lines < 400, (
        f"{guide_path} must stay a short operator workflow surface "
        f"(<{400} lines); found {guide_lines} lines"
    )
