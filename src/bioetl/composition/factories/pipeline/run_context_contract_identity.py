"""Contract-identity helpers shared by run-context assembly."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders.run_manifest_support import (
    RunManifestContractIdentity,
    resolve_contract_identity,
)
from bioetl.composition.runtime_builders.run_manifest_contract_identity import (
    ensure_complete_contract_identity,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)

if TYPE_CHECKING:
    from bioetl.domain.config import RuntimeConfig

_ContractIdentityTuple = tuple[str, ...]
_ContractIdentityResult = _ContractIdentityTuple | RunManifestContractIdentity
NormalizedContractIdentity = tuple[
    str,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
]
ContractIdentityResolver = Callable[..., _ContractIdentityResult]


def resolve_contract_identity_snapshot(
    provider: str,
    entity: str,
    *,
    strict: bool = False,
) -> NormalizedContractIdentity:
    """Resolve contract identity through the manifest support seam."""
    return resolve_contract_identity(
        provider=provider,
        entity=entity,
        strict=strict,
    )


def _normalize_contract_identity_result(
    result: _ContractIdentityResult,
) -> NormalizedContractIdentity:
    if isinstance(result, RunManifestContractIdentity):
        return (
            result.contract_ref,
            result.contract_version,
            result.contract_schema_hash,
            result.dq_policy_ref,
            result.rule_bundle_version,
            result.normalization_profile_ref,
            result.normalization_profile_version,
            result.normalization_profile_hash,
        )
    if len(result) == 5:
        (
            contract_ref,
            contract_version,
            contract_schema_hash,
            dq_policy_ref,
            rule_bundle_version,
        ) = result
        return (
            contract_ref,
            contract_version,
            contract_schema_hash,
            dq_policy_ref,
            rule_bundle_version,
            None,
            None,
            None,
        )
    if len(result) == 8:
        return result  # type: ignore[return-value]
    raise RuntimeError(
        "Contract identity resolver must return either the legacy 5-field "
        "tuple, the canonical 8-field tuple, or RunManifestContractIdentity"
    )


def runtime_requires_strict_contract_identity(runtime: RuntimeConfig) -> bool:
    """Return whether metadata RunContext must fail closed on partial identity."""
    if bool(getattr(runtime, "exact_replay", False)):
        return True
    profile = getattr(runtime, "required_persistence_profile", None)
    profile_value = getattr(profile, "value", profile)
    if profile_value is None:
        return False
    return str(profile_value).strip().lower() in STRICT_PERSISTENCE_PROFILES


def resolve_contract_identity_for_runtime(
    *,
    resolver: ContractIdentityResolver,
    provider: str,
    entity: str,
    strict: bool,
) -> NormalizedContractIdentity:
    """Resolve identity while preserving legacy two-argument test doubles."""
    if strict:
        try:
            result = _normalize_contract_identity_result(
                resolver(provider, entity, strict=True)
            )
        except TypeError:
            result = _normalize_contract_identity_result(resolver(provider, entity))
        ensure_complete_contract_identity(result[0], result[1:])
        return result
    return _normalize_contract_identity_result(resolver(provider, entity))


__all__ = [
    "ContractIdentityResolver",
    "NormalizedContractIdentity",
    "resolve_contract_identity_for_runtime",
    "resolve_contract_identity_snapshot",
    "runtime_requires_strict_contract_identity",
]
