"""Contract-registry identity helpers for manifested runs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from pathlib import Path

from bioetl.infrastructure.config.contract_registry_loader import (
    DEFAULT_CONTRACT_REGISTRY_PATH,
    load_contract_registry_entries,
)


@dataclass(frozen=True, slots=True)
class RunManifestContractIdentity:
    """Canonical manifest contract identity resolved from the contract registry."""

    contract_ref: str
    contract_version: str | None
    contract_schema_hash: str | None
    dq_policy_ref: str | None
    rule_bundle_version: str | None
    normalization_profile_ref: str | None
    normalization_profile_version: str | None
    normalization_profile_hash: str | None


CONTRACT_IDENTITY_FIELD_NAMES: tuple[str, ...] = tuple(
    field.name for field in fields(RunManifestContractIdentity)
)


def resolve_contract_identity(
    *,
    provider: str,
    entity: str,
    strict: bool = False,
) -> RunManifestContractIdentity:
    """Resolve contract identity fields from canonical registry when available."""
    contract_ref = f"{provider}.{entity}"
    registry_path = DEFAULT_CONTRACT_REGISTRY_PATH
    if not registry_path.exists():
        if strict:
            raise RuntimeError(
                "Strict reproducibility contexts require "
                f"{registry_path.as_posix()} to resolve contract identity for '{contract_ref}'"
            )
        return RunManifestContractIdentity(
            contract_ref, None, None, None, None, None, None, None
        )
    entry = _load_contract_registry_entry(
        registry_path,
        contract_ref,
        strict=strict,
    )
    if entry is None:
        if strict:
            raise RuntimeError(
                "Strict reproducibility contexts require a contract registry entry "
                f"for '{contract_ref}' in {registry_path.as_posix()}"
            )
        return RunManifestContractIdentity(
            contract_ref, None, None, None, None, None, None, None
        )
    fields = _extract_contract_identity_fields(entry)
    if strict:
        _validate_complete_contract_identity(contract_ref, fields)
    return RunManifestContractIdentity(contract_ref, *fields)


def _validate_complete_contract_identity(
    contract_ref: str,
    fields: tuple[
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
    ],
) -> None:
    missing = [
        name
        for name, value in zip(
            CONTRACT_IDENTITY_FIELD_NAMES[1:],
            fields,
            strict=True,
        )
        if value is None
    ]
    if missing:
        missing_text = ", ".join(missing)
        raise RuntimeError(
            "Strict reproducibility contexts require complete contract identity "
            f"for '{contract_ref}'; missing: {missing_text}"
        )


def _load_contract_registry_entry(
    registry_path: Path,
    contract_ref: str,
    *,
    strict: bool,
) -> dict[str, object] | None:
    entries = _read_contract_registry_entries(registry_path, strict=strict)
    if entries is None:
        return None
    entry = entries.get(contract_ref)
    if not isinstance(entry, dict):
        return None
    return entry


def _read_contract_registry_entries(
    registry_path: Path,
    *,
    strict: bool,
) -> dict[str, dict[str, object]] | None:
    try:
        return load_contract_registry_entries(registry_path)
    except (FileNotFoundError, OSError, ValueError) as exc:
        if strict:
            raise RuntimeError(
                "Strict reproducibility contexts require a readable contract "
                f"registry payload at '{registry_path}'"
            ) from exc
        return None


def _extract_contract_identity_fields(
    entry: dict[str, object],
) -> tuple[
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
    str | None,
]:
    identity_payload = _identity_payload(entry)
    contract_version = _coerce_optional_text(identity_payload.get("contract_version"))
    contract_schema_hash = _coerce_optional_text(identity_payload.get("schema_hash"))
    dq_policy_ref = _coerce_optional_text(
        identity_payload.get("dq_policy_ref") or entry.get("dq_policy_ref")
    )
    rule_bundle_version = _coerce_optional_text(
        identity_payload.get("rule_bundle_version") or entry.get("rule_bundle_version")
    )
    normalization_profile_ref = _coerce_optional_text(
        identity_payload.get("normalization_profile_ref")
        or entry.get("normalization_profile_ref")
    )
    normalization_profile_version = _coerce_optional_text(
        identity_payload.get("normalization_profile_version")
        or entry.get("normalization_profile_version")
    )
    normalization_profile_hash = _coerce_optional_text(
        identity_payload.get("normalization_profile_hash")
        or entry.get("normalization_profile_hash")
    )
    return (
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
        normalization_profile_ref,
        normalization_profile_version,
        normalization_profile_hash,
    )


def _identity_payload(entry: Mapping[str, object]) -> Mapping[str, object]:
    identity = entry.get("identity")
    if isinstance(identity, Mapping):
        return identity
    return {}


def _coerce_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
