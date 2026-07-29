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
"""Closeout guards for TDX issues #5811 through #5816."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.engineering.qa import check_constructor_args
from scripts.engineering.qa import report_observability_metric_inventory as inventory
from scripts.engineering.qa.import_graph_inventory import (
    collect_exact_module_import_usage,
)

# PhasedMigrationCoordinator removed - retired shim (2026-07-03)
from bioetl.domain.behavior.staged_enforcement import StagedEnforcementEngine
from bioetl.infrastructure.config.staged_enforcement_policy_loader import (
    load_staged_enforcement_policies,
)

pytestmark = pytest.mark.architecture
REFERENCE_TODAY = datetime(2026, 7, 6, tzinfo=UTC).date()

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5811-5816-closeout.json"
PHASED_MIGRATION_DOC = (
    ROOT / "docs" / "04-reference" / "components" / "phased-migration.md"
)
STAGED_ENFORCEMENT_REGISTRY = (
    ROOT / "configs" / "quality" / "staged_enforcement_policy_registry.yaml"
)
COMPLEXITY_REGISTRY = (
    ROOT / "configs" / "quality" / "duplication_complexity_exemptions.yaml"
)
CONSTRUCTOR_WAIVERS = ROOT / "configs" / "quality" / "constructor_waivers.yaml"
WORKFLOW = ROOT / ".github" / "workflows" / "duplication-complexity.yml"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _src_importers(module_name: str) -> set[str]:
    usage = collect_exact_module_import_usage(ROOT, module_name)
    return {str(path) for path in usage["src"]}


def test_issue_5811_closeout_artifact_covers_all_child_issues() -> None:
    closeout = _load_json(CLOSEOUT)

    assert closeout["schema_version"] == "tech-debt-issues-5811-5816-closeout-v1"
    assert closeout["parent_issue"] == 5811
    assert closeout["debt_budget_policy"] == "flat_or_decreasing_only"
    assert set(closeout["issues"]) == {5812, 5813, 5814, 5815, 5816}
    assert closeout["roadmap_closeout"]["status"] == "closeable"

    for outcome in closeout["outcomes"].values():
        assert outcome["status"] == "closeable"
        assert outcome["theme"]
        assert outcome["outcome"]
        for relative_path in outcome["evidence"]:
            assert (ROOT / relative_path).exists(), relative_path


def test_issue_5812_phased_migration_support_is_retired_compat_shim() -> None:
    # Compatibility facade restored for deprecation window (#6473 / docs).
    assert (
        ROOT / "src" / "bioetl" / "domain" / "behavior" / "phased_migration_support.py"
    ).exists()

    from bioetl.domain.behavior import PhasedMigrationCoordinator
    from bioetl.domain.behavior.phased_migration_support import (
        PhasedMigrationCoordinator as DirectCoordinator,
    )

    assert PhasedMigrationCoordinator is DirectCoordinator
    with pytest.warns(DeprecationWarning, match="retired compatibility shim"):
        coordinator = PhasedMigrationCoordinator()
    status = coordinator.get_current_migration_status()
    assert status.current_phase == "retired"


def test_issue_5813_staged_enforcement_registry_is_single_and_externalized() -> None:
    registry = _load_yaml(STAGED_ENFORCEMENT_REGISTRY)
    source_text = (
        ROOT / "src" / "bioetl" / "domain" / "behavior" / "staged_enforcement.py"
    ).read_text(encoding="utf-8")
    loaded = load_staged_enforcement_policies(STAGED_ENFORCEMENT_REGISTRY)
    engine = StagedEnforcementEngine()

    assert registry["linked_issue"] == "#5813"
    assert registry["contract_subset_policy"] == "fail_fast_subset_of_registry_only"
    assert set(engine._contract_policies) == {
        "contract_identity",
        "registry_consistency",
        "schema_compatibility",
    }
    assert "2024-" not in source_text
    assert {
        name: (
            policy.current_stage.value,
            policy.failure_threshold,
            policy.warning_threshold,
        )
        for name, policy in loaded.items()
    } == {
        name: (
            policy.current_stage.value,
            policy.failure_threshold,
            policy.warning_threshold,
        )
        for name, policy in engine.policies.items()
    }


def test_issue_5814_execution_api_stays_public_but_first_party_usage_moves_owner_side() -> (
    None
):
    execution_api_importers = _src_importers("bioetl.composition.execution_api")
    owner_seam_importers = _src_importers("bioetl.composition.execution_service_access")

    assert execution_api_importers == {"src/bioetl/composition/entrypoints.py"}
    assert owner_seam_importers == {
        "src/bioetl/interfaces/cli/commands/debug.py",
        "src/bioetl/interfaces/cli/commands/domains/health/metrics_server_integration.py",
        "src/bioetl/interfaces/cli/commands/domains/run/runtime_helpers.py",
        "src/bioetl/interfaces/cli/commands/domains/run_all/public_runtime.py",
    }

    metrics_publication = (
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "health"
        / "metrics_publication_integration.py"
    ).read_text(encoding="utf-8")
    composite_support = (
        ROOT
        / "src"
        / "bioetl"
        / "interfaces"
        / "cli"
        / "commands"
        / "domains"
        / "composite"
        / "support.py"
    ).read_text(encoding="utf-8")
    assert "bioetl.composition.observability_api" in metrics_publication
    assert "bioetl.composition.observability_api" in composite_support


def test_issue_5815_complexity_and_constructor_gates_are_blocking_and_reviewable() -> (
    None
):
    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    registry = _load_yaml(COMPLEXITY_REGISTRY)
    waivers = _load_yaml(CONSTRUCTOR_WAIVERS)
    today = REFERENCE_TODAY
    loaded_waivers = check_constructor_args._load_waivers(CONSTRUCTOR_WAIVERS)
    violations, waived = check_constructor_args._collect_violations_and_waivers(
        ROOT / "src" / "bioetl",
        loaded_waivers,
        today,
        183,
    )

    assert registry["linked_issue"] == "#5815"
    assert "check-duplication-complexity-exemptions" in workflow_text
    assert "--warn-only" not in workflow_text
    assert violations == []
    assert len(waived) == len(waivers)

    for row in waivers.values():
        assert "max_args" in row
        assert "expiry" in row
        assert "allowed_args" not in row
        assert "expiry_date" not in row


def test_issue_5816_retired_observability_events_fail_fast_on_live_inventory() -> None:
    report = inventory.collect_metric_inventory(ROOT)

    assert report["retired_declared_observability_events_emitted"] == []
    for event_name in report["retired_declared_observability_events"]:
        assert report["observability_event_emitters"].get(event_name, []) == []
