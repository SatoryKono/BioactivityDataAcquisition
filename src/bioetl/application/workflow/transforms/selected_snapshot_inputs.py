"""Resolve immutable producer snapshots carried by workflow dependencies."""

from __future__ import annotations

from collections.abc import Mapping


def selected_snapshot_inputs(
    upstream_outputs: Mapping[str, object],
) -> dict[str, dict[str, object]]:
    """Combine pinned inputs, accepting only explicitly recorded descendants."""
    snapshots: dict[str, dict[str, object]] = {}
    for payload in upstream_outputs.values():
        output = getattr(payload, "output", payload)
        raw = (
            output.get("selected_snapshots")
            if isinstance(output, Mapping)
            else getattr(output, "selected_snapshots", None)
        )
        if not isinstance(raw, Mapping):
            continue
        for identity, value in raw.items():
            if not isinstance(value, Mapping):
                raise ValueError("invalid selected snapshot metadata")
            candidate = dict(value)
            previous = snapshots.get(str(identity))
            if _accept_snapshot(str(identity), candidate, previous):
                snapshots[str(identity)] = candidate
    return snapshots


def _lineage(metadata: Mapping[str, object]) -> list[int]:
    """Validate ancestry before comparing selected versions."""
    lineage = metadata.get("ancestor_versions", [])
    if not isinstance(lineage, list) or any(type(v) is not int for v in lineage):
        raise ValueError("invalid selected snapshot lineage")
    return lineage


def _accept_snapshot(
    identity: str, candidate: dict[str, object], previous: dict[str, object] | None
) -> bool:
    """Accept a descendant while preserving the producer and table identities."""
    ancestors = _lineage(candidate)
    reverse = _lineage(previous or {})
    if not previous:
        return True
    if previous.get("table_id") != candidate.get("table_id"):
        raise ValueError(f"selected table identity changed: {identity}")
    if previous == candidate:
        return True
    if previous.get("version") not in ancestors:
        if candidate.get("version") in reverse:
            return False
        raise ValueError(f"ambiguous selected snapshot: {identity}")
    if previous.get("run_ids") != candidate.get("run_ids"):
        raise ValueError(f"selected snapshot producer changed: {identity}")
    return True
