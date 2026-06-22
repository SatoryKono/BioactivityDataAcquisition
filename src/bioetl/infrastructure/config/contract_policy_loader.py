"""Loader for typed pipeline contract policy files."""

from __future__ import annotations

__all__ = ["load_pipeline_contract_policy"]

from functools import lru_cache
from pathlib import Path

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.base_config_loader import _load_yaml_file
from bioetl.infrastructure.config.contract_policy_validation import (
    validate_contract_policy_registry_alignment,
)
from bioetl.infrastructure.config.contract_registry_loader import (
    try_load_contract_registry_entries,
)
from bioetl.infrastructure.schemas.pipeline_contract_policy import (
    PipelineContractPolicy,
)

_CONFIGS_ROOT = Path("configs")


def _load_base_contract_defaults() -> dict[str, object]:
    """Load contract defaults from consolidated base config if present."""
    base_path = _CONFIGS_ROOT / "base" / "pipeline.yaml"
    if not base_path.exists():
        return {}

    base_raw: JsonDict = _load_yaml_file(base_path)
    defaults = base_raw.get("contract_defaults")
    return defaults if isinstance(defaults, dict) else {}


def _normalize_string_list(value: object) -> list[str] | None:
    """Return a normalized string list when the source value is a YAML list."""
    if not isinstance(value, list):
        return None
    return [str(item) for item in value]


def _merge_ordered_unique_strings(*collections: object) -> list[str]:
    """Merge string collections while preserving first-seen order."""
    merged: list[str] = []
    seen: set[str] = set()
    for collection in collections:
        values = _normalize_string_list(collection)
        if values is None:
            continue
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            merged.append(value)
    return merged


def _root_runtime_hash_selectors(unified_raw: JsonDict) -> dict[str, list[str]]:
    """Extract runtime-authoritative hash selectors from root ``hash_policy``."""
    root = unified_raw.get("hash_policy")
    if not isinstance(root, dict):
        return {}
    nested = root.get("hash_policy")
    if not isinstance(nested, dict):
        return {}

    selectors: dict[str, list[str]] = {}
    include_fields = _normalize_string_list(nested.get("include_fields"))
    if include_fields is not None:
        selectors["hash_include"] = include_fields

    exclude_fields = _normalize_string_list(nested.get("exclude_fields"))
    if exclude_fields is not None:
        selectors["hash_exclude"] = exclude_fields
    return selectors


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


def _build_effective_contract_policy_payload(
    *,
    base_defaults: dict[str, object],
    contracts_section: dict[str, object],
    unified_raw: JsonDict,
) -> dict[str, object]:
    """Build the effective typed contract policy payload for runtime consumers."""
    merged = _merge_contract_sections(base_defaults, contracts_section)
    runtime_hash_selectors = _root_runtime_hash_selectors(unified_raw)
    include_fields = runtime_hash_selectors.get("hash_include")
    if include_fields is not None:
        merged["hash_include"] = include_fields
    exclude_fields = runtime_hash_selectors.get("hash_exclude")
    if exclude_fields is not None:
        merged["hash_exclude"] = _merge_ordered_unique_strings(
            base_defaults.get("hash_exclude"),
            exclude_fields,
        )
    return merged


@lru_cache(maxsize=128)
def load_pipeline_contract_policy(provider: str, entity: str) -> PipelineContractPolicy:
    """Load typed policy from unified entity config contracts section."""
    base_defaults = _load_base_contract_defaults()
    registry_entries = try_load_contract_registry_entries()

    unified_entity_path = _CONFIGS_ROOT / "entities" / provider / f"{entity}.yaml"
    if not unified_entity_path.exists():
        raise ValueError(f"Contract policy file not found: {unified_entity_path}")

    unified_raw: JsonDict = _load_yaml_file(unified_entity_path)
    contracts_section = unified_raw.get("contracts")
    if not isinstance(contracts_section, dict):
        raise ValueError(
            f"Contract policy section 'contracts' not found in {unified_entity_path}"
        )

    del provider, entity
    result = PipelineContractPolicy.model_validate(
        _build_effective_contract_policy_payload(
            base_defaults=base_defaults,
            contracts_section=contracts_section,
            unified_raw=unified_raw,
        )
    )
    validate_contract_policy_registry_alignment(
        result,
        registry_entries=registry_entries,
    )
    validated_policy: PipelineContractPolicy = result
    return validated_policy
