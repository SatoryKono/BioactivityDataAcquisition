"""Hash/schema policy helpers for record-processor assembly."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from itertools import chain

from bioetl.application.core.wiring.runtime import (
    BasePipeline,
    ContentHashPolicyByVersion,
    ContentHashVersionPolicy,
)
from bioetl.domain.types import (
    GoldSchemaPolicyByVersion,
    GoldSchemaVersionPolicy,
)

from bioetl.domain.types import GoldSchemaType


def coerce_string_frozenset(value: object | None) -> frozenset[str]:
    """Coerce list/set-like string collections to an immutable set."""
    if value is None or isinstance(value, str | bytes):
        return frozenset()
    if not isinstance(value, Iterable):
        return frozenset()
    return frozenset(item for item in value if isinstance(item, str))


def extract_hash_policy(
    pipeline: BasePipeline,
) -> tuple[frozenset[str], frozenset[str]]:
    """Extract effective content-hash field policy from transformer wiring."""
    transformer = getattr(pipeline, "transformer", None)
    identity = getattr(transformer, "_identity", None)
    contract_policy = getattr(transformer, "_contract_policy", None)

    identity_include = coerce_string_frozenset(
        getattr(identity, "_content_hash_include_fields", None)
    )
    identity_exclude = coerce_string_frozenset(
        getattr(identity, "_content_hash_exclude_fields", None)
    )
    if identity_include or identity_exclude:
        return identity_include, frozenset(
            chain(identity_exclude, ("entity_id", "content_hash"))
        )

    contract_include = coerce_string_frozenset(
        getattr(contract_policy, "hash_include", None)
    )
    contract_exclude = coerce_string_frozenset(
        getattr(contract_policy, "hash_exclude", None)
    )

    include_fields = (
        frozenset(contract_include & identity_include)
        if contract_include and identity_include
        else (contract_include or identity_include)
    )
    exclude_fields = frozenset(
        chain(identity_exclude, contract_exclude, ("entity_id", "content_hash"))
    )
    return include_fields, exclude_fields


def _extract_contract_policy(pipeline: BasePipeline) -> object | None:
    """Extract the contract policy from a pipeline's transformer."""
    transformer = getattr(pipeline, "transformer", None)
    return getattr(transformer, "_contract_policy", None)


def _normalize_version(version: object | None) -> str:
    """Normalize a version string, returning empty string if invalid."""
    return str(version).strip() if version is not None else ""


def _resolve_write_versions(
    active_version: str,
    write_versions: Iterable[object] | None,
) -> tuple[str, ...]:
    """Resolve the ordered tuple of write versions, ensuring active_version is included."""
    if write_versions is None:
        return (active_version,)

    versions = tuple(
        _normalize_version(v) for v in write_versions if _normalize_version(v)
    ) or (active_version,)

    if active_version not in versions:
        return (active_version, *versions)
    return versions


def extract_hash_policy_by_version(
    pipeline: BasePipeline,
    *,
    include_fields: frozenset[str],
    exclude_fields: frozenset[str],
) -> ContentHashPolicyByVersion | None:
    """Build ordered per-version hash policies from rollout-aware contract policy."""
    contract_policy = _extract_contract_policy(pipeline)
    active_version = _normalize_version(getattr(contract_policy, "active_version", None))

    if not active_version:
        return None

    rollout = getattr(contract_policy, "rollout", None)
    versions = _resolve_write_versions(
        active_version,
        getattr(rollout, "write_versions", None)
    )

    affects_hash = bool(getattr(rollout, "affects_hash", False))
    datetime_policy = str(
        getattr(contract_policy, "hash_datetime_policy", "v2_datetime_utc")
        or "v2_datetime_utc"
    ).strip()
    if datetime_policy not in {"v1_date", "v2_datetime_utc"}:
        datetime_policy = "v2_datetime_utc"

    return ContentHashPolicyByVersion(
        active_version=active_version,
        affects_hash=affects_hash,
        policies=tuple(
            ContentHashVersionPolicy(
                version=version,
                include_fields=include_fields,
                exclude_fields=exclude_fields,
                datetime_policy=datetime_policy,
            )
            for version in versions
        ),
    )


def extract_gold_schema_policy_by_version(
    pipeline: BasePipeline,
    *,
    gold_schema: GoldSchemaType,
) -> GoldSchemaPolicyByVersion | None:
    """Build ordered per-version Gold schema routing from rollout-aware policy."""
    contract_policy = _extract_contract_policy(pipeline)
    active_version = _normalize_version(getattr(contract_policy, "active_version", None))

    if not active_version:
        return None

    rollout = getattr(contract_policy, "rollout", None)
    versions = _resolve_write_versions(
        active_version,
        getattr(rollout, "write_versions", None)
    )

    configured_mapping = getattr(pipeline, "gold_schema_by_version", None)
    schema_mapping: dict[str, object] = {}
    if isinstance(configured_mapping, Mapping):
        schema_mapping = {
            _normalize_version(version): schema
            for version, schema in configured_mapping.items()
            if _normalize_version(version) and schema is not None
        }

    for version in versions:
        schema_mapping.setdefault(version, gold_schema)

    return GoldSchemaPolicyByVersion(
        active_version=active_version,
        policies=tuple(
            GoldSchemaVersionPolicy(
                version=version,
                schema=schema_mapping[version],
            )
            for version in versions
        ),
    )
