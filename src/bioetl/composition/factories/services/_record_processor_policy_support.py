"""Hash/schema policy helpers for record-processor assembly."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from itertools import chain
from typing import TYPE_CHECKING

from bioetl.application.core.wiring.runtime import (
    BasePipeline,
    ContentHashPolicyByVersion,
    ContentHashVersionPolicy,
)
from bioetl.domain.types import (
    GoldSchemaPolicyByVersion,
    GoldSchemaVersionPolicy,
)

if TYPE_CHECKING:
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


def extract_hash_policy_by_version(
    pipeline: BasePipeline,
    *,
    include_fields: frozenset[str],
    exclude_fields: frozenset[str],
) -> ContentHashPolicyByVersion | None:
    """Build ordered per-version hash policies from rollout-aware contract policy."""
    transformer = getattr(pipeline, "transformer", None)
    contract_policy = getattr(transformer, "_contract_policy", None)
    active_version = getattr(contract_policy, "active_version", None)
    rollout = getattr(contract_policy, "rollout", None)
    write_versions = getattr(rollout, "write_versions", None)
    affects_hash = bool(getattr(rollout, "affects_hash", False))
    datetime_policy = str(
        getattr(contract_policy, "hash_datetime_policy", "v1_date") or "v1_date"
    ).strip()
    if datetime_policy not in {"v1_date", "v2_datetime_utc"}:
        datetime_policy = "v1_date"

    normalized_active_version = (
        str(active_version).strip() if active_version is not None else ""
    )
    if not normalized_active_version:
        return None

    if write_versions is None:
        versions: tuple[str, ...] = (normalized_active_version,)
    else:
        versions = tuple(
            str(version).strip() for version in write_versions if str(version).strip()
        ) or (normalized_active_version,)

    if normalized_active_version not in versions:
        versions = (normalized_active_version, *versions)

    return ContentHashPolicyByVersion(
        active_version=normalized_active_version,
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
    transformer = getattr(pipeline, "transformer", None)
    contract_policy = getattr(transformer, "_contract_policy", None)
    active_version = getattr(contract_policy, "active_version", None)
    rollout = getattr(contract_policy, "rollout", None)
    write_versions = getattr(rollout, "write_versions", None)
    configured_mapping = getattr(pipeline, "gold_schema_by_version", None)

    normalized_active_version = (
        str(active_version).strip() if active_version is not None else ""
    )
    if not normalized_active_version:
        return None

    if write_versions is None:
        versions: tuple[str, ...] = (normalized_active_version,)
    else:
        versions = tuple(
            str(version).strip() for version in write_versions if str(version).strip()
        ) or (normalized_active_version,)

    if normalized_active_version not in versions:
        versions = (normalized_active_version, *versions)

    schema_mapping: dict[str, object] = {}
    if isinstance(configured_mapping, Mapping):
        schema_mapping = {
            str(version).strip(): schema
            for version, schema in configured_mapping.items()
            if str(version).strip() and schema is not None
        }

    for version in versions:
        schema_mapping.setdefault(version, gold_schema)

    return GoldSchemaPolicyByVersion(
        active_version=normalized_active_version,
        policies=tuple(
            GoldSchemaVersionPolicy(
                version=version,
                schema=schema_mapping[version],
            )
            for version in versions
        ),
    )
