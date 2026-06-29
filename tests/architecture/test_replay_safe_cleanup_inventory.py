"""Guardrails for replay-safe cleanup and retention inventory."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "configs" / "quality" / "replay_safe_cleanup_inventory.yaml"
QUALITY_REPORTS_ROOT = ROOT / "reports" / "quality"
_PRETEST_GUARDRAILS_TIMESTAMP_RE = re.compile(
    r"^pretest_guardrails_(\d{8})_(\d{6})\.json$"
)
REQUIRED_REPLAY_ANCHORS = {
    "fixture_input",
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
    assert "data/debug_exports/**" in runbook
    assert "reports/quality/_tmp_*" in runbook
    assert "pretest_guardrails_*.json" in runbook


@pytest.mark.architecture
def test_reports_quality_working_diagnostics_publish_owner_and_ttl() -> None:
    payload = _inventory()
    entries = payload["entries"]
    assert isinstance(entries, list)

    by_id = {str(entry["id"]): entry for entry in entries if isinstance(entry, dict)}

    for entry_id, expected_ttl in (
        ("reports_quality_tmp_diagnostics", 7),
        ("reports_quality_pretest_guardrails_history", 30),
    ):
        entry = by_id[entry_id]
        assert entry.get("touches_replay_evidence") is False
        assert entry.get("protection") == "owner-reviewed-working-report-ttl"
        assert entry.get("owner") == "Engineering / Quality"
        assert entry.get("ttl_days") == expected_ttl


@pytest.mark.architecture
def test_reports_quality_ttl_artifacts_are_not_past_retention_window() -> None:
    """Live repo state must not retain expired reports/quality TTL artifacts."""
    now = datetime.now(tz=UTC)
    expired: list[str] = []
    ttl_by_pattern = {"_tmp_*": 7, "pretest_guardrails_*.json": 30}

    for pattern, ttl_days in ttl_by_pattern.items():
        for path in QUALITY_REPORTS_ROOT.glob(pattern):
            if not path.is_file():
                continue
            timestamp = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            match = _PRETEST_GUARDRAILS_TIMESTAMP_RE.match(path.name)
            if match is not None:
                date_part, time_part = match.groups()
                timestamp = datetime.strptime(
                    f"{date_part}{time_part}",
                    "%Y%m%d%H%M%S",
                ).replace(tzinfo=UTC)
            age_days = (now.date() - timestamp.date()).days
            if age_days > ttl_days:
                expired.append(path.relative_to(ROOT).as_posix())

    assert expired == []


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


@pytest.mark.architecture
def test_debug_exports_cleanup_surface_is_inventory_backed() -> None:
    payload = _inventory()
    entries = payload["entries"]
    assert isinstance(entries, list)

    by_id = {str(entry["id"]): entry for entry in entries if isinstance(entry, dict)}
    entry = by_id["debug_exports"]

    assert entry["path"] == "data/debug_exports/**"
    assert entry["classification"] == "debug_export_cleanup"
    assert entry["touches_replay_evidence"] is True
    assert entry["dry_run_required"] is True
    assert entry["protection"] == "owner-reviewed-retention-sensitive-cleanup"
    assert Path(str(entry["runbook"])).name == "retention-sensitive-cleanup.md"


@pytest.mark.architecture
def test_data_cleanup_families_have_explicit_retention_classes() -> None:
    payload = _inventory()
    entries = payload["entries"]
    assert isinstance(entries, list)

    by_id = {str(entry["id"]): entry for entry in entries if isinstance(entry, dict)}

    expected_classes = {
        "tracked_input_datasets": ("data/input/**", "reproducibility_fixture"),
        "debug_exports": ("data/debug_exports/**", "tracked_debug_evidence"),
        "control_plane_run_manifest": (
            "data/output/control/run_manifest/**",
            "checkpoint_control_plane_state",
        ),
        "control_plane_run_ledger": (
            "data/output/control/run_ledger/**",
            "checkpoint_control_plane_state",
        ),
        "control_plane_effective_config": (
            "data/output/control/effective_config/**",
            "checkpoint_control_plane_state",
        ),
        "control_plane_lineage": (
            "data/output/control/lineage/**",
            "checkpoint_control_plane_state",
        ),
        "checkpoints": (
            "data/output/checkpoints/**",
            "checkpoint_control_plane_state",
        ),
        "cached_bronze_snapshots": (
            "data/output/bronze/**",
            "local_runtime_output",
        ),
        "silver_gold_outputs": (
            "data/output/{silver,gold}/**",
            "local_runtime_output",
        ),
        "quarantine_records": (
            "data/output/quarantine/**",
            "local_runtime_output",
        ),
    }

    for entry_id, (path, retention_class) in expected_classes.items():
        entry = by_id[entry_id]
        assert entry["path"] == path
        assert entry["retention_class"] == retention_class
        assert entry["dry_run_required"] is True
        assert str(entry["runbook"]).strip()
