"""Pipeline-configuration normalization utilities."""

from __future__ import annotations

from bioetl.domain.types import JsonDict


def _project_schema_fields_into_config(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    data_schema: JsonDict,  # Any: YAML config has heterogeneous values
) -> None:
    """Project runtime-relevant schema fields into pipeline config."""
    layer_keys = {
        "columns",
        "column_groups",
        "include_groups",
        "exclude_fields",
        "rename_fields",
    }

    projected_data_schema: JsonDict = {}
    if "column_groups" in data_schema:
        projected_data_schema["column_groups"] = data_schema["column_groups"]
    for layer_name in ("silver", "gold"):
        layer_value = data_schema.get(layer_name)
        if isinstance(layer_value, dict):
            projected_data_schema[layer_name] = {
                key: layer_value[key] for key in layer_keys if key in layer_value
            }

    config["data_schema"] = dict(projected_data_schema)
    if "column_groups" in data_schema:
        config["column_groups"] = data_schema["column_groups"]
    if "content_hash" in data_schema:
        config["content_hash"] = data_schema["content_hash"]


def _is_empty_string_collection(value: object) -> bool:
    """Return True when a config collection is absent or contains no strings."""
    if value is None:
        return True
    if not isinstance(value, list):
        return False
    return not any(str(item).strip() for item in value)


def _project_authoritative_hash_policy_into_config(
    config: JsonDict,
    *,
    entity_config: JsonDict,
    unified_schema: JsonDict | None,
    unified_contracts: JsonDict | None,
    unified_hash_policy: JsonDict | None,
) -> None:
    """Project root hash_policy into the runtime config and guard legacy shims."""
    if not unified_hash_policy:
        return

    provider = str(config.get("provider") or "").strip()
    entity_type = str(config.get("entity_type") or "").strip()
    policy_provider = str(unified_hash_policy.get("provider") or "").strip()
    policy_entity = str(unified_hash_policy.get("entity") or "").strip()
    _validate_hash_policy_identity(
        provider=provider,
        entity_type=entity_type,
        policy_provider=policy_provider,
        policy_entity=policy_entity,
    )
    _validate_schema_hash_policy_shims(unified_schema)
    _validate_contract_hash_policy_shims(unified_contracts)
    config["content_hash_policy"] = _build_content_hash_policy_projection(
        unified_hash_policy=unified_hash_policy,
        provider=provider,
        entity_type=entity_type,
        policy_provider=policy_provider,
        policy_entity=policy_entity,
    )
    _ = entity_config


def _validate_hash_policy_identity(
    *,
    provider: str,
    entity_type: str,
    policy_provider: str,
    policy_entity: str,
) -> None:
    """Ensure root hash-policy identity matches the pipeline config identity."""
    if policy_provider and provider and policy_provider != provider:
        raise ValueError(
            "hash_policy.provider must match pipeline.provider; "
            f"got {policy_provider!r} != {provider!r}"
        )
    if policy_entity and entity_type and policy_entity != entity_type:
        raise ValueError(
            "hash_policy.entity must match pipeline.entity_type; "
            f"got {policy_entity!r} != {entity_type!r}"
        )


def _validate_schema_hash_policy_shims(unified_schema: JsonDict | None) -> None:
    """Forbid legacy schema hash include/exclude shims when root policy exists."""
    schema_content_hash = (
        unified_schema.get("content_hash") if isinstance(unified_schema, dict) else None
    )
    if not isinstance(schema_content_hash, dict):
        return
    if not _is_empty_string_collection(schema_content_hash.get("include")):
        raise ValueError(
            "schema.content_hash.include must be empty when root hash_policy is "
            "present; hash selection is runtime-authoritative only via hash_policy"
        )
    if not _is_empty_string_collection(schema_content_hash.get("exclude")):
        raise ValueError(
            "schema.content_hash.exclude must be empty when root hash_policy is "
            "present; hash selection is runtime-authoritative only via hash_policy"
        )


def _validate_contract_hash_policy_shims(unified_contracts: JsonDict | None) -> None:
    """Forbid legacy contract hash include/exclude shims when root policy exists."""
    if not isinstance(unified_contracts, dict):
        return
    if not _is_empty_string_collection(unified_contracts.get("hash_include")):
        raise ValueError(
            "contracts.hash_include must be empty when root hash_policy is "
            "present; hash selection is runtime-authoritative only via hash_policy"
        )
    if not _is_empty_string_collection(unified_contracts.get("hash_exclude")):
        raise ValueError(
            "contracts.hash_exclude must be empty when root hash_policy is "
            "present; hash selection is runtime-authoritative only via hash_policy"
        )


def _build_content_hash_policy_projection(
    *,
    unified_hash_policy: JsonDict,
    provider: str,
    entity_type: str,
    policy_provider: str,
    policy_entity: str,
) -> JsonDict:
    """Build the runtime content-hash policy projection from root config."""
    nested_policy = unified_hash_policy.get("hash_policy")
    if not isinstance(nested_policy, dict):
        raise ValueError("hash_policy.hash_policy must be a mapping")
    return {
        "provider": policy_provider or provider,
        "entity": policy_entity or entity_type,
        "contract": unified_hash_policy.get("contract", {}),
        **nested_policy,
    }


def _validate_chembl_json_ordering_mirror_shim(
    *,
    provider: str,
    unified_hash_policy: JsonDict | None,
) -> None:
    """Forbid duplicate JSON ordering policy surfaces for ChEMBL."""
    if provider != "chembl" or not isinstance(unified_hash_policy, dict):
        return
    nested_policy = unified_hash_policy.get("hash_policy")
    if not isinstance(nested_policy, dict):
        return
    field_ordering = nested_policy.get("field_ordering")
    if not isinstance(field_ordering, dict) or not field_ordering:
        return
    raise ValueError(
        "hash_policy.hash_policy.field_ordering must be empty for ChEMBL; "
        "JSON ordering semantics are runtime-authoritative only via "
        "src/bioetl/domain/normalization/profiles/chembl_json_ordering_policy.py"
    )


def _validate_column_groups(
    groups: object,
    schema_source: str,
) -> set[str | None]:
    """Validate column_groups is a non-empty list and return group names.

    Returns:
        Set of group name values extracted from valid column group dicts.
    """
    if not isinstance(groups, list) or not groups:
        raise ValueError(
            f"schema '{schema_source}' must define non-empty column_groups"
        )
    return {g.get("name") for g in groups if isinstance(g, dict)}


def _has_business_group(group_names: set[str | None]) -> bool:
    """Check if group names contain a business group.

    Returns:
        True if 'business' is present or any non-system, non-dq group name exists.
    """
    if "business" in group_names:
        return True
    return any(
        isinstance(name, str) and name != "system" and not name.startswith("dq")
        for name in group_names
    )


def _validate_layer_include_groups(
    data_schema: JsonDict,  # Any: YAML config has heterogeneous values
    layer: str,
    schema_source: str,
) -> None:
    """Validate a single layer has proper include_groups config."""
    layer_cfg = data_schema.get(layer)
    if not isinstance(layer_cfg, dict):
        raise ValueError(
            f"schema '{schema_source}' missing '{layer}' layer filter config"
        )
    include_groups = layer_cfg.get("include_groups")
    if not isinstance(include_groups, list) or not include_groups:
        raise ValueError(
            f"schema '{schema_source}' must define non-empty {layer}.include_groups"
        )


def _validate_schema_config(
    data_schema: JsonDict,  # Any: YAML config has heterogeneous values
    schema_source: str,
) -> None:
    """Validate schema configuration has required minimum structure."""
    group_names = _validate_column_groups(
        data_schema.get("column_groups") or [], schema_source
    )

    if not ("system" in group_names and _has_business_group(group_names)):
        raise ValueError(
            f"schema '{schema_source}' must contain system and business groups"
        )

    for layer in ("silver", "gold"):
        _validate_layer_include_groups(data_schema, layer, schema_source)


def apply_pipeline_schema_normalization(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    *,
    entity_config: JsonDict,  # Any: YAML config has heterogeneous values
    config_path: object,
    unified_schema: JsonDict | None = None,  # Any: YAML values are heterogeneous
    unified_contracts: JsonDict | None = None,  # Any: YAML values are heterogeneous
    unified_hash_policy: JsonDict | None = None,  # Any: YAML values are heterogeneous
) -> None:
    """Validate and project canonical `unified_schema` into pipeline config."""
    _ = config_path

    if unified_schema:
        _validate_schema_config(unified_schema, "entities/*/*:schema")
        _project_schema_fields_into_config(config, unified_schema)
    _validate_chembl_json_ordering_mirror_shim(
        provider=str(config.get("provider") or "").strip(),
        unified_hash_policy=unified_hash_policy,
    )
    _project_authoritative_hash_policy_into_config(
        config,
        entity_config=entity_config,
        unified_schema=unified_schema,
        unified_contracts=unified_contracts,
        unified_hash_policy=unified_hash_policy,
    )


__all__ = ["apply_pipeline_schema_normalization"]
