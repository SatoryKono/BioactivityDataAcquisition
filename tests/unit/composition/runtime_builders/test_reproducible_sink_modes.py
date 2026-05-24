"""Tests for replay-capable sink idempotency policy gates."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.composition.runtime_builders.run_manifest_support import (
    validate_reproducible_sink_modes,
)


def _yaml_config(*, contract: str, evidence: dict[str, object] | None = None) -> object:
    layer: dict[str, object] = {
        "enabled": True,
        "mode": "append",
        "idempotency_contract": contract,
    }
    if evidence is not None:
        layer["idempotency_evidence"] = evidence
    return SimpleNamespace(sink={"silver": layer}, business_primary_keys=("id",))


def test_replay_capable_family_rejects_occurrence_only_append_output() -> None:
    """Replay-capable families must not launch with occurrence-only semantic sinks."""
    with pytest.raises(RuntimeError, match="Replay-capable pipeline families"):
        validate_reproducible_sink_modes(
            yaml_config=_yaml_config(contract="occurrence_only"),
            strict_replay_requested=False,
            replay_capable_family=True,
        )


def test_non_replay_family_may_keep_occurrence_only_append_output() -> None:
    """Degraded/debug-only families can still classify append output as occurrence-only."""
    validate_reproducible_sink_modes(
        yaml_config=_yaml_config(contract="occurrence_only"),
        strict_replay_requested=False,
        replay_capable_family=False,
    )


def test_append_log_requires_and_accepts_machine_readable_evidence() -> None:
    """Append-log semantics remain valid only with explicit identity evidence."""
    validate_reproducible_sink_modes(
        yaml_config=_yaml_config(
            contract="append_log",
            evidence={"append_log_identity_fields": ("run_id", "batch_id")},
        ),
        strict_replay_requested=False,
        replay_capable_family=False,
    )


def test_strict_replay_rejects_append_output_even_with_evidence() -> None:
    """Strict profiles reject append-mode semantic sinks regardless of evidence."""
    with pytest.raises(RuntimeError, match="Replay-capable pipeline families"):
        validate_reproducible_sink_modes(
            yaml_config=_yaml_config(
                contract="append_log",
                evidence={"append_log_identity_fields": ("run_id", "batch_id")},
            ),
            strict_replay_requested=True,
            replay_capable_family=False,
        )
