"""Loader for typed pipeline contract policy files."""

from __future__ import annotations

__all__ = ["load_pipeline_contract_policy"]

from functools import lru_cache
from pathlib import Path

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.base_config_loader import _load_yaml_file
from bioetl.infrastructure.config.contract_policy_validation import (
    load_contract_registry_entries,
    validate_contract_policy_registry_alignment,
)
from bioetl.infrastructure.schemas.pipeline_contract_policy import (
    PipelineContractPolicy,
)

_CONFIGS_ROOT = Path("configs")


def _is_empty_hash_shim(value: object) -> bool:
    """Return True when deprecated contract hash shims are absent or empty."""
    if value is None:
        return True
    if not isinstance(value, list):
        return False
    return not any(str(item).strip() for item in value)


def _validate_root_hash_policy_compatibility(
    unified_raw: JsonDict,
    *,
    unified_entity_path: Path,
) -> None:
    """Ensure legacy contract hash surfaces stay empty when root hash_policy exists."""
    root_hash_policy = unified_raw.get("hash_policy")
    if not isinstance(root_hash_policy, dict):
        return
    contracts_section = unified_raw.get("contracts")
    if not isinstance(contracts_section, dict):
        return

    if not _is_empty_hash_shim(contracts_section.get("hash_include")):
        raise ValueError(
            "contracts.hash_include must be empty when root hash_policy is present "
            f"in {unified_entity_path}"
        )
    if not _is_empty_hash_shim(contracts_section.get("hash_exclude")):
        raise ValueError(
            "contracts.hash_exclude must be empty when root hash_policy is present "
            f"in {unified_entity_path}"
        )


def _load_base_contract_defaults() -> dict[str, object]:
    """Load contract defaults from consolidated base config if present."""
    base_path = _CONFIGS_ROOT / "base" / "pipeline.yaml"
    if not base_path.exists():
        return {}

    base_raw: JsonDict = _load_yaml_file(base_path)
    defaults = base_raw.get("contract_defaults")
    return defaults if isinstance(defaults, dict) else {}


def _merge_contract_sections(
    base_defaults: dict[str, object],
    contracts_section: dict[str, object],
) -> dict[str, object]:
    """Merge base defaults and entity contract config, including nested rollout."""
    merged = {**base_defaults, **contracts_section}
    base_rollout = base_defaults.get("rollout")
    entity_rollout = contracts_section.get("rollout")
    if isinstance(base_rollout, dict) or isinstance(entity_rollout, dict):
        merged["rollout"] = {
            **(base_rollout if isinstance(base_rollout, dict) else {}),
            **(entity_rollout if isinstance(entity_rollout, dict) else {}),
        }
    return merged


def _default_contract_identity(
    *,
    provider: str,
    entity: str,
    registry_entries: dict[str, dict[str, object]],
) -> tuple[str, str]:
    """Resolve default contract_ref and active_version from registry when available."""
    contract_ref = f"{provider}.{entity}"
    entry = registry_entries.get(contract_ref)
    if not isinstance(entry, dict):
        return contract_ref, "1.0.0"

    identity = entry.get("identity")
    identity_payload = identity if isinstance(identity, dict) else {}
    contract_version = identity_payload.get("contract_version")
    if isinstance(contract_version, str) and contract_version.strip():
        return contract_ref, contract_version.strip()

    supported_versions = entry.get("supported_versions")
    if isinstance(supported_versions, list):
        for version in supported_versions:
            if isinstance(version, str) and version.strip():
                return contract_ref, version.strip()
    return contract_ref, "1.0.0"


def _apply_rollout_defaults(
    raw: dict[str, object],
    *,
    provider: str,
    entity: str,
    registry_entries: dict[str, dict[str, object]],
) -> dict[str, object]:
    """Fill rollout defaults so legacy entity configs remain valid."""
    contract_ref, default_active_version = _default_contract_identity(
        provider=provider,
        entity=entity,
        registry_entries=registry_entries,
    )
    active_version = str(raw.get("active_version") or default_active_version).strip()
    rollout = raw.get("rollout")
    rollout_payload = rollout if isinstance(rollout, dict) else {}
    mode = str(rollout_payload.get("mode") or "single").strip() or "single"
    read_order = rollout_payload.get("read_order")
    write_versions = rollout_payload.get("write_versions")
    affects_hash = bool(rollout_payload.get("affects_hash", False))

    normalized = dict(raw)
    normalized["contract_ref"] = str(raw.get("contract_ref") or contract_ref).strip()
    normalized["active_version"] = active_version
    normalized["rollout"] = {
        "mode": mode,
        "read_order": list(read_order)
        if isinstance(read_order, list)
        else [active_version],
        "write_versions": list(write_versions)
        if isinstance(write_versions, list)
        else [active_version],
        "affects_hash": affects_hash,
    }
    return normalized


@lru_cache(maxsize=128)
def load_pipeline_contract_policy(provider: str, entity: str) -> PipelineContractPolicy:
    """Load typed policy from unified entity config contracts section."""
    base_defaults = _load_base_contract_defaults()
    registry_entries = load_contract_registry_entries()

    unified_entity_path = _CONFIGS_ROOT / "entities" / provider / f"{entity}.yaml"
    if not unified_entity_path.exists():
        raise ValueError(f"Contract policy file not found: {unified_entity_path}")

    unified_raw: JsonDict = _load_yaml_file(unified_entity_path)
    _validate_root_hash_policy_compatibility(
        unified_raw,
        unified_entity_path=unified_entity_path,
    )
    contracts_section = unified_raw.get("contracts")
    if not isinstance(contracts_section, dict):
        raise ValueError(
            f"Contract policy section 'contracts' not found in {unified_entity_path}"
        )

    raw = _merge_contract_sections(base_defaults, contracts_section)
    normalized = _apply_rollout_defaults(
        raw,
        provider=provider,
        entity=entity,
        registry_entries=registry_entries,
    )
    result = PipelineContractPolicy.model_validate(normalized)
    validate_contract_policy_registry_alignment(
        result,
        registry_entries=registry_entries,
    )
    validated_policy: PipelineContractPolicy = result
    return validated_policy
