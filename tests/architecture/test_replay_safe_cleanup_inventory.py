"""Guardrails for replay-safe cleanup and retention inventory."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "configs" / "quality" / "replay_safe_cleanup_inventory.yaml"
REQUIRED_REPLAY_ANCHORS = {
    "run_manifest",
    "run_ledger",
    "effective_config",
    "lineage",
    "checkpoint",
    "cached_bronze_snapshot",
    "semantic_output",
    "quality_exception_evidence",
}


def _inventory() -> dict[str, object]:
    payload = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.mark.architecture
def test_replay_safe_cleanup_inventory_covers_replay_anchor_surfaces() -> None:
    """Every replay-affecting cleanup surface must have an owner and tool."""
    payload = _inventory()
    entries = payload.get("entries")
    assert isinstance(entries, list) and entries
    anchor_by_id = {
        str(entry["id"]): str(entry["replay_anchor"])
        for entry in entries
        if isinstance(entry, dict)
    }

    assert REQUIRED_REPLAY_ANCHORS <= set(anchor_by_id.values())
    for entry in entries:
        assert isinstance(entry, dict)
        if entry.get("touches_replay_evidence") is not True:
            continue
        assert entry.get("dry_run_required") is True, entry["id"]
        assert entry.get("canonical_tool"), entry["id"]
        assert entry.get("protection"), entry["id"]
        assert Path(str(entry["runbook"])).suffix == ".md", entry["id"]


@pytest.mark.architecture
def test_control_plane_cleanup_surfaces_require_replay_impact_classification() -> None:
    """Control-plane replay anchors must route through the shared lifecycle planner."""
    payload = _inventory()
    entries = payload["entries"]
    assert isinstance(entries, list)
    control_plane_entries = [
        entry
        for entry in entries
        if isinstance(entry, dict)
        and entry.get("protection") == "FileControlPlaneArtifactLifecycleStore"
    ]

    assert control_plane_entries
    for entry in control_plane_entries:
        assert entry.get("replay_impact_required") is True, entry["id"]
        assert (
            entry.get("canonical_tool") == "bioetl maintenance control-plane-lifecycle"
        )
        assert entry.get("dry_run_required") is True


@pytest.mark.architecture
def test_retention_sensitive_runbook_points_to_replay_safe_inventory() -> None:
    """Operator cleanup docs must expose the machine-readable cleanup inventory."""
    runbook = (
        ROOT / "docs" / "05-operations" / "runbooks" / "retention-sensitive-cleanup.md"
    ).read_text(encoding="utf-8")

    assert "configs/quality/replay_safe_cleanup_inventory.yaml" in runbook
    assert "replay-impact checklist" in runbook


@pytest.mark.architecture
def test_control_plane_lifecycle_runbook_publishes_evidence_retention_matrix() -> None:
    """Control-plane runbook must explain retain/delete rules per evidence surface."""
    runbook = ROOT / "docs" / "05-operations" / "control-plane-lifecycle.md"
    text = runbook.read_text(encoding="utf-8")
    required_fragments = (
        "## Replay Evidence Retention Matrix",
        "`RUN_MANIFEST`",
        "`RUN_LEDGER`",
        "`EFFECTIVE_CONFIG`",
        "`CHECKPOINT`",
        "`LINEAGE`",
        "`cached_bronze_snapshot`",
        "strict_replay_evidence_protected",
        "unprotected_replay_evidence_delete_candidate",
    )
    missing = [fragment for fragment in required_fragments if fragment not in text]

    assert not missing
