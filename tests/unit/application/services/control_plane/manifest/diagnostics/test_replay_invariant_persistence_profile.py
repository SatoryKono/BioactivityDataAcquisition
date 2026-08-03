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
"""Unit coverage for replay persistence-policy invariant facade."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.persistence_policy import (
    _is_composite_execution_context,
    _resolve_applied_checkpoint_compatibility_policy,
    _resolve_exact_replay_support_boundary,
    _resolve_replay_family_contract,
    _resolve_reproducibility_profile,
    _resolve_requested_checkpoint_compatibility_policy,
    _resolve_required_persistence_profile,
)


pytestmark = pytest.mark.unit


def _manifest() -> SimpleNamespace:
    return SimpleNamespace(
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        code_provenance=SimpleNamespace(contract_ref="gold.chembl_activity"),
    )


def test_resolve_reproducibility_profile_uses_source_execution_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = SimpleNamespace(exact_replay_support_boundary="source-boundary")

    monkeypatch.setattr(
        "bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family.build_replay_family_context",
        lambda manifest: SimpleNamespace(
            profile=profile,
            exact_replay_support_boundary="source-boundary",
            replay_family_contract={},
        ),
    )

    assert _resolve_reproducibility_profile(_manifest()) is profile


def test_resolve_replay_family_contract_uses_composite_execution_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = {"contract": "composite_family"}

    monkeypatch.setattr(
        "bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family.build_replay_family_context",
        lambda manifest: SimpleNamespace(
            profile=SimpleNamespace(),
            exact_replay_support_boundary="composite-boundary",
            replay_family_contract=contract,
        ),
    )

    assert _resolve_replay_family_contract(_manifest()) == contract


def test_exact_replay_support_boundary_delegates_to_resolved_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_family.build_replay_family_context",
        lambda manifest: SimpleNamespace(
            exact_replay_support_boundary="strict",
            profile=SimpleNamespace(),
            replay_family_contract={},
        ),
    )

    assert _resolve_exact_replay_support_boundary(_manifest()) == ("strict")


def test_persistence_policy_facade_reexports_policy_helpers() -> None:
    assert callable(_is_composite_execution_context)
    assert callable(_resolve_applied_checkpoint_compatibility_policy)
    assert callable(_resolve_exact_replay_support_boundary)
    assert callable(_resolve_replay_family_contract)
    assert callable(_resolve_reproducibility_profile)
    assert callable(_resolve_requested_checkpoint_compatibility_policy)
    assert callable(_resolve_required_persistence_profile)


@pytest.mark.parametrize(
    ("runtime_config", "expected"),
    [
        (
            {
                "pipeline": {
                    "control_plane": {"checkpoint_compatibility_policy": "soft_fail"}
                }
            },
            "soft_fail",
        ),
        ({"control_plane": {"checkpoint_compatibility_policy": "observe"}}, "observe"),
    ],
)
def test_resolve_requested_checkpoint_policy_reads_canonical_runtime_config_paths(
    runtime_config: dict[str, Any],
    expected: str,
) -> None:
    manifest = _manifest()
    manifest.runtime_config = runtime_config

    assert _resolve_requested_checkpoint_compatibility_policy(manifest) == expected


def test_resolve_requested_checkpoint_policy_ignores_retired_top_level_runtime_config_alias() -> (
    None
):
    manifest = _manifest()
    manifest.runtime_config = {"checkpoint_compatibility_policy": "soft_fail"}

    assert _resolve_requested_checkpoint_compatibility_policy(manifest) is None


def test_resolve_requested_checkpoint_policy_still_accepts_launch_context() -> None:
    manifest = _manifest()
    manifest.launch_context = {"checkpoint_compatibility_policy": "hard_fail"}

    assert _resolve_requested_checkpoint_compatibility_policy(manifest) == "hard_fail"
