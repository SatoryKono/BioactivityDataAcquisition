"""Prove optional-stage absence from immutable, identity-bound seed inputs."""

from __future__ import annotations

import asyncio
from pathlib import Path

from bioetl.infrastructure.storage.composite_replay_bundle import (
    confined_path,
    verify_bundle,
)
from bioetl.infrastructure.storage.composite_replay_inputs import (
    CompositeReplayInputReader,
)


def verified_empty_optional_stages(config: dict, parent: dict, path: Path) -> set[str]:
    """Accept only declared skips whose captured join keys are all ineligible."""
    artifacts = [
        item
        for item in parent.get("artifacts", [])
        if item.get("kind") == "composite_exact_replay"
    ]
    if len(artifacts) != 1:
        raise ValueError("optional_skip_envelope_missing_or_ambiguous")
    artifact = artifacts[0]
    envelope_path = confined_path(path.parent, artifact["ref"])
    if envelope_path.name != "parent.json":
        raise ValueError("optional_skip_envelope_invalid")
    envelope = verify_bundle(envelope_path.parent, artifact["sha256"])
    if (envelope["pipeline"], envelope["run_id"]) != (
        path.parent.parent.name,
        path.parent.name,
    ):
        raise ValueError("optional_skip_identity_mismatch")
    request = envelope["request"]
    if request["seed_pipeline"] != config["seed"]["pipeline"]:
        raise ValueError("optional_skip_seed_mismatch")
    reader = CompositeReplayInputReader(
        envelope_path.parent / "inputs",
        envelope_sha256=envelope["input_snapshot_fingerprint"],
    )
    seed = asyncio.run(reader.read_table(request["seed_table"]))
    return {
        row["pipeline"]
        for row in config.get("enrichers", [])
        if row.get("required", False) is False
        and request.get("outcomes", {}).get(row["pipeline"]) == "skipped"
        and _has_no_eligible_keys(seed, row.get("join_keys", []))
    }


def _has_no_eligible_keys(seed, keys: list[str]) -> bool:
    """Unknown columns and empty key contracts cannot certify an empty stage."""
    if not keys or not set(keys).issubset(seed.column_names):
        return False
    return not any(
        all(value is not None for value in row.values())
        for row in seed.select(keys).to_pylist()
    )
