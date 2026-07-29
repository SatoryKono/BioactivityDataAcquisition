# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for replay-capable sink idempotency policy gates."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.composition.runtime_builders.run_manifest_support import (
    validate_reproducible_sink_modes,
)


pytestmark = pytest.mark.unit


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
    result = validate_reproducible_sink_modes(
        yaml_config=_yaml_config(contract="occurrence_only"),
        strict_replay_requested=False,
        replay_capable_family=False,
    )
    assert result is None


def test_append_log_requires_and_accepts_machine_readable_evidence() -> None:
    """Append-log semantics remain valid only with explicit identity evidence."""
    result = validate_reproducible_sink_modes(
        yaml_config=_yaml_config(
            contract="append_log",
            evidence={"append_log_identity_fields": ("run_id", "batch_id")},
        ),
        strict_replay_requested=False,
        replay_capable_family=False,
    )
    assert result is None


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
