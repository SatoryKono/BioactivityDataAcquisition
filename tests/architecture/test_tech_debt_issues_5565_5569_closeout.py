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
"""Closeout guards for technical-debt issues #5565 through #5569."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.engineering.qa.import_graph_inventory import (
    collect_exact_module_import_usage,
)

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5565-5569-closeout.json"
SEMANTIC_SEAMS = ROOT / "configs" / "quality" / "semantic_seam_role_inventory.yaml"
FACADE_POLICY = ROOT / "configs" / "quality" / "control_plane_facade_import_policy.yaml"
CONFIG_BACKLOG = ROOT / "reports" / "quality" / "config-surface-backlog.json"
OBSERVABILITY_GOVERNANCE = (
    ROOT / "configs" / "quality" / "observability_metric_governance.yaml"
)
OBSERVABILITY_EVIDENCE = (
    ROOT / "reports" / "observability" / "runtime_cardinality_inventory.json"
)

EXPECTED_ISSUES = {5565, 5566, 5567, 5568, 5569}
ALLOWED_SEMANTIC_ROLES = {"policy", "runtime_builder", "use_case"}

pytestmark = pytest.mark.architecture


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


def _non_composite_duplication_clusters(
    backlog: dict[str, Any],
) -> list[dict[str, Any]]:
    clusters = backlog["duplication_audit"]["clusters"]
    assert isinstance(clusters, list)
    return [
        cluster
        for cluster in clusters
        if any(
            surface_kind != "composite_config"
            for surface_kind in cluster["surface_kind_counts"]
        )
    ]


def test_issue_5566_semantic_seams_have_roles_and_no_new_src_callers() -> None:
    inventory = _load_yaml(SEMANTIC_SEAMS)

    assert inventory["linked_issue"] == "#5566"
    assert inventory["new_caller_policy"] == "fail_fast_review_required"
    assert set(inventory["allowed_semantic_roles"]) == ALLOWED_SEMANTIC_ROLES

    seams = inventory["seams"]
    assert len(seams) == 3
    for seam in seams:
        assert seam["semantic_role"] in ALLOWED_SEMANTIC_ROLES
        assert seam["owner"].startswith("@bioetl-")
        assert (ROOT / seam["path"]).exists(), seam["path"]
        assert str(seam["rationale"]).strip()

        guard = seam["caller_guard"]
        expected = set(guard["allowed_src_importers"])
        actual = _src_importers(str(seam["module"]))
        assert actual == expected, (
            f"{seam['module']} src importers drifted beyond the reviewed role "
            f"guard. Expected {sorted(expected)}, got {sorted(actual)}"
        )
        assert len(actual) <= int(guard["max_src_importer_count"])


def test_issue_5567_control_plane_facades_have_bounded_first_party_imports() -> None:
    policy = _load_yaml(FACADE_POLICY)

    assert policy["linked_issue"] == "#5567"
    assert policy["new_src_import_policy"] == "fail_fast_review_required"
    facades = policy["facades"]
    assert len(facades) == 6

    for facade in facades:
        assert (ROOT / facade["path"]).exists(), facade["path"]
        assert facade["owner"].startswith("@bioetl-")
        assert str(facade["disposition"]).strip()
        assert str(facade["rationale"]).strip()

        expected = set(facade["allowed_src_importers"])
        actual = _src_importers(str(facade["module"]))
        assert actual == expected, (
            f"{facade['module']} facade importers changed without #5567 review. "
            f"Expected {sorted(expected)}, got {sorted(actual)}"
        )
        assert len(actual) <= int(facade["max_src_importer_count"])


def test_issue_5568_non_composite_config_duplication_is_explicitly_governed() -> None:
    closeout = _load_json(CLOSEOUT)
    backlog = _load_json(CONFIG_BACKLOG)
    non_composite_clusters = _non_composite_duplication_clusters(backlog)
    max_cluster_count = int(
        closeout["metrics"]["max_non_composite_duplication_clusters"]
    )

    assert len(non_composite_clusters) <= max_cluster_count
    assert non_composite_clusters
    for cluster in non_composite_clusters:
        governance = cluster["governance"]
        assert governance["linked_issue"] == "#5568", cluster["block_path"]
        assert governance["decision"] != "review_required", cluster["block_path"]
        assert governance["owner"].startswith("@bioetl-"), cluster["block_path"]
        assert str(governance["rationale"]).strip(), cluster["block_path"]


def test_issue_5569_retired_observability_events_have_lifecycle_guards() -> None:
    governance = _load_yaml(OBSERVABILITY_GOVERNANCE)
    event_governance = governance["event_signal_governance"]
    evidence = _load_json(OBSERVABILITY_EVIDENCE)

    entries = event_governance["retired_declared_events"]
    entries_by_name = {str(entry["event_name"]): entry for entry in entries}
    retired_events = evidence["retired_declared_observability_events"]

    assert retired_events == sorted(retired_events)
    assert set(entries_by_name) == set(retired_events)
    assert evidence["retired_declared_observability_events_emitted"] == []
    assert evidence["unused_declared_observability_events"] == []

    event_emitters = evidence["observability_event_emitters"]
    for event_name in retired_events:
        entry = entries_by_name[event_name]
        assert entry["action"] == "retire"
        assert entry["linked_issue"] == "#5569"
        assert entry["lifecycle"] == "retired_declared_contract"
        assert entry["disposition"] == "retain_declared_retired_block_emission"
        assert len(entry["reactivation_requires"]) >= 3
        assert event_emitters.get(event_name, []) == []
