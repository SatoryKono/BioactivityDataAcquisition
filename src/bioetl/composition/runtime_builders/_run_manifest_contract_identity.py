"""Contract-registry identity helpers for manifested runs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml


def resolve_contract_identity(
    *,
    provider: str,
    entity: str,
    strict: bool = False,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Resolve contract identity fields from canonical registry when available."""
    contract_ref = f"{provider}.{entity}"
    registry_path = Path("configs/base/contract_registry.yaml")
    if not registry_path.exists():
        if strict:
            raise RuntimeError(
                "Strict reproducibility contexts require configs/base/"
                f"contract_registry.yaml to resolve contract identity for '{contract_ref}'"
            )
        return contract_ref, None, None, None, None
    entry = _load_contract_registry_entry(
        registry_path,
        contract_ref,
        strict=strict,
    )
    if entry is None:
        if strict:
            raise RuntimeError(
                "Strict reproducibility contexts require a contract registry entry "
                f"for '{contract_ref}' in configs/base/contract_registry.yaml"
            )
        return contract_ref, None, None, None, None
    return (contract_ref, *_extract_contract_identity_fields(entry))


def _load_contract_registry_entry(
    registry_path: Path,
    contract_ref: str,
    *,
    strict: bool,
) -> dict[str, object] | None:
    payload = _read_contract_registry_payload(registry_path, strict=strict)
    if payload is None:
        return None
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        if strict:
            raise RuntimeError(
                "Strict reproducibility contexts require "
                "configs/base/contract_registry.yaml to expose a top-level "
                "'entries' mapping"
            )
        return None
    entry = entries.get(contract_ref)
    if not isinstance(entry, dict):
        return None
    return entry


def _read_contract_registry_payload(
    registry_path: Path,
    *,
    strict: bool,
) -> dict[str, object] | None:
    try:
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        if strict:
            raise RuntimeError(
                "Strict reproducibility contexts require a readable contract "
                f"registry payload at '{registry_path}'"
            ) from exc
        return None
    if not isinstance(payload, dict):
        if strict:
            raise RuntimeError(
                "Strict reproducibility contexts require "
                "configs/base/contract_registry.yaml to parse into a mapping"
            )
        return None
    return payload


def _extract_contract_identity_fields(
    entry: dict[str, object],
) -> tuple[str | None, str | None, str | None, str | None]:
    identity_payload = _identity_payload(entry)
    contract_version = _coerce_optional_text(identity_payload.get("contract_version"))
    contract_schema_hash = _coerce_optional_text(identity_payload.get("schema_hash"))
    dq_policy_ref = _coerce_optional_text(
        identity_payload.get("dq_policy_ref") or entry.get("dq_policy_ref")
    )
    rule_bundle_version = _coerce_optional_text(
        identity_payload.get("rule_bundle_version") or entry.get("rule_bundle_version")
    )
    return (
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
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
