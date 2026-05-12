"""Architecture guardrails for hotspot-family duplication ratchets."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"


def _load_scorecard() -> dict[str, object]:
    payload = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert all(isinstance(row, dict) for row in rows)
    return rows


def _match_family_targets(
    rows: list[dict[str, object]],
    *,
    path_prefixes: list[str],
) -> list[dict[str, object]]:
    normalized_prefixes = tuple(prefix.rstrip("/") for prefix in path_prefixes)
    matched: list[dict[str, object]] = []
    for row in rows:
        target = row.get("target")
        if not isinstance(target, str):
            continue
        if any(target.startswith(prefix) for prefix in normalized_prefixes):
            matched.append(row)
    return matched


def _family_is_clean(
    rows: list[dict[str, object]],
    *,
    path_prefixes: list[str],
) -> bool:
    matched = _match_family_targets(rows, path_prefixes=path_prefixes)
    return bool(matched) and all(row.get("duplicate_count") == 0 for row in matched)


def test_active_hotspot_family_duplication_ratchets_require_confirmed_clean_history() -> (
    None
):
    """Active family ratchets must stay bounded to zero-duplication seams only."""
    scorecard = _load_scorecard()
    hotspot_policy = scorecard.get("hotspot_family_ratchets", {})
    assert isinstance(hotspot_policy, dict)
    assert hotspot_policy.get("mode") == "fail-fast"

    artifact_policy = hotspot_policy.get("artifact_policy", {})
    assert isinstance(artifact_policy, dict)
    assert artifact_policy.get("expected_direction") == "downward"
    assert artifact_policy.get("confirming_clean_snapshots_required") == 2

    baseline_artifact = artifact_policy.get("baseline_artifact")
    history_artifact = artifact_policy.get("history_artifact")
    latest_reviewed_snapshot = artifact_policy.get("latest_reviewed_snapshot")
    assert isinstance(baseline_artifact, str) and baseline_artifact
    assert isinstance(history_artifact, str) and history_artifact
    assert isinstance(latest_reviewed_snapshot, str) and latest_reviewed_snapshot

    baseline_payload = _load_json(PROJECT_ROOT / baseline_artifact)
    history_records = _load_jsonl(PROJECT_ROOT / history_artifact)

    baseline_summary = baseline_payload.get("summary", {})
    assert isinstance(baseline_summary, dict)
    assert baseline_summary.get("snapshot_date") == latest_reviewed_snapshot

    baseline_targets = baseline_payload.get("targets", [])
    assert isinstance(baseline_targets, list)
    baseline_target_rows = [row for row in baseline_targets if isinstance(row, dict)]

    families = hotspot_policy.get("families", [])
    assert isinstance(families, list) and families
    active_families = [
        family
        for family in families
        if isinstance(family, dict) and family.get("ratchet_stage") == "active"
    ]
    assert active_families, "Expected at least one active hotspot family ratchet"

    required_clean_snapshots = int(
        artifact_policy["confirming_clean_snapshots_required"]
    )
    for family in active_families:
        assert family.get("ratchet_scope") == "duplication-plus-bounded-growth"
        metrics = family.get("metrics", {})
        assert isinstance(metrics, dict)
        assert metrics.get("duplication_clusters") == 0

        expected_action = family.get("expected_action")
        assert isinstance(expected_action, str)
        assert "file-growth and fan-in" in expected_action

        path_prefixes = family.get("path_prefixes", [])
        assert isinstance(path_prefixes, list) and path_prefixes
        assert _family_is_clean(
            baseline_target_rows,
            path_prefixes=[
                prefix for prefix in path_prefixes if isinstance(prefix, str)
            ],
        ), (
            f"Active family {family.get('name')} must stay at zero duplication in the latest baseline"
        )

        clean_history = [
            record
            for record in history_records
            if isinstance(record.get("targets"), list)
            and _family_is_clean(
                [row for row in record["targets"] if isinstance(row, dict)],
                path_prefixes=[
                    prefix for prefix in path_prefixes if isinstance(prefix, str)
                ],
            )
        ]
        assert len(clean_history) >= required_clean_snapshots, (
            f"Active family {family.get('name')} requires at least "
            f"{required_clean_snapshots} confirming clean snapshots"
        )
        assert all(
            record.get("snapshot_date") == latest_reviewed_snapshot
            for record in clean_history[-required_clean_snapshots:]
        ), (
            f"Active family {family.get('name')} must be confirmed by the latest "
            "reviewed clean snapshots"
        )
