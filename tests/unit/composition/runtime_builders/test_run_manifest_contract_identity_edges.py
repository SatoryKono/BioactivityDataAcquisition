"""Fail-closed and compatibility edges for manifest contract identity."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.composition.runtime_builders import (
    run_manifest_contract_identity as identity,
)

pytestmark = pytest.mark.unit


def _set_registry_path(
    monkeypatch: pytest.MonkeyPatch,
    registry_path: Path,
) -> None:
    monkeypatch.setattr(identity, "DEFAULT_CONTRACT_REGISTRY_PATH", registry_path)


def test_missing_registry_returns_compatibility_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-strict callers retain a stable ref when the registry is absent."""
    _set_registry_path(monkeypatch, tmp_path / "missing-registry.yaml")

    result = identity.resolve_contract_identity(provider="chembl", entity="activity")

    assert result == identity.RunManifestContractIdentity(
        "chembl.activity",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )


def test_missing_registry_fails_closed_in_strict_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strict reproducibility cannot proceed without the registry artifact."""
    registry_path = tmp_path / "missing-registry.yaml"
    _set_registry_path(monkeypatch, registry_path)

    with pytest.raises(RuntimeError, match="require.*contract identity"):
        identity.resolve_contract_identity(
            provider="chembl",
            entity="activity",
            strict=True,
        )


@pytest.mark.parametrize("strict", [False, True])
def test_non_mapping_registry_entry_is_absent_or_fails_closed(
    strict: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed entry shapes never masquerade as resolved identity."""
    registry_path = tmp_path / "contract-registry.yaml"
    registry_path.touch()
    _set_registry_path(monkeypatch, registry_path)
    monkeypatch.setattr(
        identity,
        "load_contract_registry_entries",
        lambda _path: {"chembl.activity": "not-a-mapping"},
    )

    if strict:
        with pytest.raises(RuntimeError, match="registry entry"):
            identity.resolve_contract_identity(
                provider="chembl",
                entity="activity",
                strict=True,
            )
    else:
        result = identity.resolve_contract_identity(
            provider="chembl",
            entity="activity",
        )
        assert result.contract_ref == "chembl.activity"
        assert result.contract_version is None


def test_top_level_compatibility_fields_are_used_when_identity_is_not_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy top-level identity fields remain readable without an identity map."""
    registry_path = tmp_path / "contract-registry.yaml"
    registry_path.touch()
    _set_registry_path(monkeypatch, registry_path)
    monkeypatch.setattr(
        identity,
        "load_contract_registry_entries",
        lambda _path: {
            "chembl.activity": {
                "identity": ["invalid-shape"],
                "dq_policy_ref": "chembl.activity.policy",
                "rule_bundle_version": "2026.08",
            }
        },
    )

    result = identity.resolve_contract_identity(provider="chembl", entity="activity")

    assert result.contract_version is None
    assert result.dq_policy_ref == "chembl.activity.policy"
    assert result.rule_bundle_version == "2026.08"
