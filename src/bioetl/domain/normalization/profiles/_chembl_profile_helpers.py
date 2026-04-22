"""Shared helper declarations for ChEMBL normalization profiles."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles._standard_profile_rule_components import (
    RuleComponentSpec,
)
from bioetl.domain.normalization.profiles.base import NormalizationProfile

__all__ = [
    "CHEMBL_META_FIELDS",
    "build_chembl_profile",
    "chembl_schema_fields",
]

CHEMBL_META_FIELDS = frozenset(
    {
        "entity_id",
        "content_hash",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
        "_index",
        "_dq_error",
        "_dq_warn",
    }
)


def chembl_schema_fields(schema_cls: Any) -> tuple[str, ...]:
    """Return ordered Pandera schema fields for a ChEMBL profile."""
    return tuple(schema_cls.to_schema().columns.keys())


def build_chembl_profile(
    *,
    entity: str,
    schema_fields: Collection[str],
    description: str | None = None,
    title_fields: Collection[str] = (),
    abstract_fields: Collection[str] = (),
    doi_fields: Collection[str] = (),
    pmid_fields: Collection[str] = (),
    pmc_id_fields: Collection[str] = (),
    date_fields: Collection[str] = (),
    int_fields: Collection[str] = (),
    float_fields: Collection[str] = (),
    set_like_fields: Collection[str] = (),
    json_string_fields: Collection[str] = (),
    boolean_fields: Collection[str] = (),
    flag_fields: Collection[str] = (),
    operator_fields: Collection[str] = (),
    ontology_id_fields: Collection[str] = (),
    enum_fields: Mapping[str, frozenset[str]] | None = None,
    case_fields: Mapping[str, frozenset[str] | None] | None = None,
    unit_fields: Collection[str] | None = None,
    null_fields: Collection[str] | None = None,
    special_rules: Mapping[str, RuleComponentSpec] | None = None,
) -> NormalizationProfile:
    """Build a standard ChEMBL profile with shared metadata semantics."""
    return build_standard_profile(
        profile_name=f"chembl.{entity}",
        description=description
        or f"Canonical field-level normalization policy for the ChEMBL {entity} Silver schema.",
        schema_fields=schema_fields,
        meta_fields=CHEMBL_META_FIELDS,
        title_fields=title_fields,
        abstract_fields=abstract_fields,
        doi_fields=doi_fields,
        pmid_fields=pmid_fields,
        pmc_id_fields=pmc_id_fields,
        date_fields=date_fields,
        int_fields=int_fields,
        float_fields=float_fields,
        set_like_fields=set_like_fields,
        json_string_fields=json_string_fields,
        boolean_fields=boolean_fields,
        flag_fields=flag_fields,
        operator_fields=operator_fields,
        ontology_id_fields=ontology_id_fields,
        enum_fields=enum_fields,
        case_fields=case_fields,
        unit_fields=unit_fields,
        null_fields=null_fields,
        special_rules=special_rules,
    )
