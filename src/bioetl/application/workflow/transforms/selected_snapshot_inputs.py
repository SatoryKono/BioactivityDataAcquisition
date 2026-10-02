"""Resolve immutable producer snapshots carried by workflow dependencies."""

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
            for metadata in (candidate, snapshots.get(str(identity), {})):
                lineage = metadata.get("ancestor_versions", [])
                if not isinstance(lineage, list) or any(
                    type(v) is not int for v in lineage
                ):
                    raise ValueError("invalid selected snapshot lineage")
            previous = snapshots.get(str(identity))
            if previous and previous != candidate:
                ancestors = candidate.get("ancestor_versions", [])
                assert isinstance(ancestors, list)
                reverse = previous.get("ancestor_versions", [])
                assert isinstance(reverse, list)
                if previous.get("version") in ancestors:
                    pass
                elif candidate.get("version") in reverse:
                    continue
                else:
                    raise ValueError(f"ambiguous selected snapshot: {identity}")
                if previous.get("run_ids") != candidate.get("run_ids"):
                    raise ValueError(f"selected snapshot producer changed: {identity}")
            snapshots[str(identity)] = candidate
    return snapshots
