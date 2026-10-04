"""Resolve immutable producer snapshots carried by workflow dependencies."""

from collections.abc import Mapping
from typing import cast

from bioetl.application.services.execution.pipeline_runner_models import RunResult


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
            _merge_selected_snapshot(snapshots, str(identity), value)
    return snapshots


def _validated_lineage(metadata: Mapping[str, object]) -> list[int]:
    lineage = metadata.get("ancestor_versions", [])
    if not isinstance(lineage, list) or any(type(v) is not int for v in lineage):
        raise ValueError("invalid selected snapshot lineage")
    return lineage


def _merge_selected_snapshot(
    snapshots: dict[str, dict[str, object]], identity: str, value: object
) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("invalid selected snapshot metadata")
    candidate = dict(value)
    previous = snapshots.get(identity)
    _validated_lineage(candidate)
    _validated_lineage(previous or {})
    if _use_selected_candidate(previous, candidate, identity):
        snapshots[identity] = candidate


def _use_selected_candidate(
    previous: dict[str, object] | None, candidate: dict[str, object], identity: str
) -> bool:
    if not previous:
        return True
    if previous.get("table_id") != candidate.get("table_id"):
        raise ValueError(f"selected table identity changed: {identity}")
    if previous == candidate:
        return True
    if previous.get("version") not in _validated_lineage(candidate):
        if candidate.get("version") in _validated_lineage(previous):
            return False
        raise ValueError(f"ambiguous selected snapshot: {identity}")
    if previous.get("run_ids") != candidate.get("run_ids"):
        raise ValueError(f"selected snapshot producer changed: {identity}")
    return True


def _identity(entry: Mapping[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in entry.items()
        if key not in {"version", "ancestor_versions"}
    }


def _mutation_count(payload: Mapping[str, object], expected_count: int) -> int:
    counts = [
        payload.get(key)
        for key in (
            "scanned_rows",
            "retained_rows",
            "orphan_rows_deleted",
            "quarantine_rows_written",
        )
    ]
    if any(type(count) is not int or count < 0 for count in counts):
        raise ValueError("reference_cohort descendant counts invalid")
    scanned, retained, expired, quarantined = [cast(int, count) for count in counts]
    if (
        scanned != expected_count
        or scanned != retained + expired
        or expired <= 0
        or quarantined != expired
    ):
        raise ValueError("reference_cohort descendant count or quarantine mismatch")
    return retained


def _require_confirmed_mutation(result: object, payload: Mapping[str, object]) -> None:
    if (
        getattr(result, "status", "success") != "success"
        or payload.get("dry_run") is not False
        or payload.get("would_mutate") is not False
        or payload.get("reconciliation_mode") != "selected-snapshot"
        or payload.get("source_scope") != "current_run"
        or payload.get("reference_scope") != "current_run"
        or payload.get("mutation_blocked_reason")
    ):
        raise ValueError("reference_cohort descendant mutation unconfirmed")


def _source_mutations(
    upstream: Mapping[str, object], key: str
) -> list[Mapping[str, object]]:
    mutations = []
    for result in upstream.values():
        payload = getattr(result, "output", result)
        if (
            not isinstance(payload, Mapping)
            or payload.get("transform_name") != "reconcile_foreign_keys"
        ):
            continue
        if (
            f"{payload.get('source_layer')}:{payload.get('source_table')}" != key
            or payload.get("mutated") is not True
        ):
            continue
        _require_confirmed_mutation(result, payload)
        mutations.append(payload)
    return mutations


def _advance(
    entry: Mapping[str, object], payload: Mapping[str, object], key: str
) -> dict[str, object]:
    inputs, outputs = payload.get("input_snapshots"), payload.get("selected_snapshots")
    if (
        not isinstance(inputs, Mapping)
        or not isinstance(outputs, Mapping)
        or inputs.get(key) != entry
    ):
        raise ValueError("reference_cohort descendant input pin mismatch")
    expected = dict(entry)
    expected["version"] = cast(int, entry["version"]) + 1
    expected["ancestor_versions"] = [
        *cast(list[int], entry.get("ancestor_versions", [])),
        entry["version"],
    ]
    if (
        outputs.get(key) != expected
        or set(inputs) != set(outputs)
        or any(
            inputs[identity] != outputs[identity]
            for identity in inputs
            if identity != key
        )
    ):
        raise ValueError(
            "reference_cohort descendant pin or producer membership mismatch"
        )
    return expected


def resolve_cohort_lineage(
    source: RunResult, upstream: Mapping[str, object], key: str
) -> tuple[Mapping[str, object], int]:
    """Resolve an exact recorded descendant and its producer-scoped retained count."""
    original = (source.selected_snapshots or {}).get(key)
    selected = selected_snapshot_inputs(upstream).get(key)
    if not isinstance(original, Mapping) or not isinstance(selected, Mapping):
        raise ValueError("reference_cohort producer snapshot identity mismatch")
    _require_descendant_pin(original)
    _require_descendant_pin(selected)
    if _identity(original) != _identity(selected):
        raise ValueError("reference_cohort descendant producer identity mismatch")
    mutations = _source_mutations(upstream, key)
    entry, expected_count = original, source.records_gold
    while entry != selected:
        payload = _next_source_mutation(mutations, entry, key, source.run_id)
        expected_count = _mutation_count(payload, expected_count)
        entry = _advance(entry, payload, key)
        mutations.remove(payload)
    if mutations:
        raise ValueError("reference_cohort conflicting source mutation lineage")
    return selected, expected_count


def _require_descendant_pin(pin: Mapping[str, object]) -> None:
    version, ancestors = pin.get("version"), pin.get("ancestor_versions", [])
    if (
        type(version) is not int
        or version < 0
        or not isinstance(ancestors, list)
        or any(type(value) is not int or value < 0 for value in ancestors)
    ):
        raise ValueError("reference_cohort invalid descendant version lineage")


def _next_source_mutation(
    mutations: list[Mapping[str, object]],
    entry: Mapping[str, object],
    key: str,
    run_id: str,
) -> Mapping[str, object]:
    candidates = [
        payload
        for payload in mutations
        if isinstance(payload.get("input_snapshots"), Mapping)
        and cast(Mapping[str, object], payload["input_snapshots"]).get(key) == entry
    ]
    if len(candidates) != 1:
        raise ValueError("reference_cohort lacks unambiguous source mutation lineage")
    payload = candidates[0]
    _require_descendant_run_id(payload, run_id)
    return payload


def _require_descendant_run_id(payload: Mapping[str, object], run_id: str) -> None:
    """Keep producer membership validation separate from mutation-chain selection."""
    run_ids = payload.get("source_run_ids")
    if (
        not isinstance(run_ids, list)
        or not run_ids
        or any(not isinstance(value, str) or not value for value in run_ids)
        or run_id not in run_ids
    ):
        raise ValueError("reference_cohort descendant source run mismatch")
