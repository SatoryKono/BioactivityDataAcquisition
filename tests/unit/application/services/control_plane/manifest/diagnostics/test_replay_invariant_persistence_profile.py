"""Unit coverage for replay persistence-policy invariant facade."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants import (
    persistence_policy,
)


pytestmark = pytest.mark.unit


def _manifest() -> SimpleNamespace:
    return SimpleNamespace(
        provider="chembl",
        entity="activity",
        code_provenance=SimpleNamespace(contract_ref="gold.chembl_activity"),
    )


def test_resolve_reproducibility_profile_uses_source_execution_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, str]] = []
    profile = SimpleNamespace(exact_replay_support_boundary="source-boundary")

    monkeypatch.setattr(
        persistence_policy,
        "_is_composite_execution_context",
        lambda manifest: False,
    )
    monkeypatch.setattr(
        persistence_policy,
        "resolve_reproducibility_family_profile",
        lambda **kwargs: calls.append(dict(kwargs)) or profile,
    )

    assert persistence_policy._resolve_reproducibility_profile(_manifest()) is profile
    assert calls == [
        {
            "provider": "chembl",
            "entity": "activity",
            "contract_ref": "gold.chembl_activity",
            "execution_context": "source",
        }
    ]


def test_resolve_replay_family_contract_uses_composite_execution_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, str]] = []
    contract = {"contract": "composite_family"}

    monkeypatch.setattr(
        persistence_policy,
        "_is_composite_execution_context",
        lambda manifest: True,
    )
    monkeypatch.setattr(
        persistence_policy,
        "build_replay_family_contract",
        lambda **kwargs: calls.append(dict(kwargs)) or contract,
    )

    assert persistence_policy._resolve_replay_family_contract(_manifest()) == contract
    assert calls == [
        {
            "provider": "chembl",
            "entity": "activity",
            "contract_ref": "gold.chembl_activity",
            "execution_context": "composite",
        }
    ]


def test_exact_replay_support_boundary_delegates_to_resolved_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        persistence_policy,
        "_resolve_reproducibility_profile",
        lambda manifest: SimpleNamespace(exact_replay_support_boundary="strict"),
    )

    assert persistence_policy._resolve_exact_replay_support_boundary(_manifest()) == (
        "strict"
    )


def test_persistence_policy_facade_reexports_policy_helpers() -> None:
    exported = set(persistence_policy.__all__)

    assert {
        "_resolve_applied_checkpoint_compatibility_policy",
        "_resolve_exact_replay_support_boundary",
        "_resolve_replay_family_contract",
        "_resolve_reproducibility_profile",
        "_resolve_requested_checkpoint_compatibility_policy",
        "_resolve_required_persistence_profile",
    } <= exported

    helper_names = [
        "_resolve_applied_checkpoint_compatibility_policy",
        "_resolve_requested_checkpoint_compatibility_policy",
        "_resolve_required_persistence_profile",
    ]
    for name in helper_names:
        helper: Any = getattr(persistence_policy, name)
        assert callable(helper)
