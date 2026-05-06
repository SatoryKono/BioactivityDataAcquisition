"""Shared helper declarations for ChEMBL normalization profiles."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles._standard_profile_rule_components import (
    RuleComponentSpec,
)
from bioetl.domain.normalization.profiles._standard_profile_spec import (
    StandardProfileSpec,
)
from bioetl.domain.normalization.profiles.base import NormalizationProfile
from bioetl.domain.normalization.profiles._chembl_reference_identifier_rules import (
    chembl_reference_identifier_rules,
)

__all__ = [
    "CHEMBL_META_FIELDS",
    "ChemblProfileFieldGroups",
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


@dataclass(frozen=True, slots=True)
class ChemblProfileFieldGroups:
    """Optional field families used to build ChEMBL normalization profiles."""

    title_fields: Collection[str] = ()
    abstract_fields: Collection[str] = ()
    doi_fields: Collection[str] = ()
    pmid_fields: Collection[str] = ()
    pmc_id_fields: Collection[str] = ()
    date_fields: Collection[str] = ()
    int_fields: Collection[str] = ()
    float_fields: Collection[str] = ()
    set_like_fields: Collection[str] = ()
    json_string_fields: Collection[str] = ()
    boolean_fields: Collection[str] = ()
    flag_fields: Collection[str] = ()
    operator_fields: Collection[str] = ()
    ontology_id_fields: Collection[str] = ()
    enum_fields: Mapping[str, frozenset[str]] | None = None
    case_fields: Mapping[str, frozenset[str] | None] | None = None
    unit_fields: Collection[str] | None = None
    null_fields: Collection[str] | None = None
    special_rules: Mapping[str, RuleComponentSpec] | None = None


def chembl_schema_fields(
    schema_cls: Any,  # Any: schema factories share only a runtime `.to_schema()` protocol.
) -> tuple[
    str, ...
]:  # Any: schema_cls is a class with a .to_schema().columns.keys() protocol
    """Return ordered Pandera schema fields for a ChEMBL profile."""
    return tuple(schema_cls.to_schema().columns.keys())


def build_chembl_profile(
    *,
    entity: str,
    schema_fields: Collection[str],
    description: str | None = None,
    field_groups: ChemblProfileFieldGroups | None = None,
) -> NormalizationProfile:
    """Build a standard ChEMBL profile with shared metadata semantics."""
    groups = field_groups or ChemblProfileFieldGroups()
    special_rules = {
        **chembl_reference_identifier_rules(entity),
        **(groups.special_rules or {}),
    }
    return build_standard_profile(
        StandardProfileSpec(
            profile_name=f"chembl.{entity}",
            description=description
            or (
                "Canonical field-level normalization policy for the "
                f"ChEMBL {entity} Silver schema."
            ),
            schema_fields=schema_fields,
            meta_fields=CHEMBL_META_FIELDS,
            title_fields=groups.title_fields,
            abstract_fields=groups.abstract_fields,
            doi_fields=groups.doi_fields,
            pmid_fields=groups.pmid_fields,
            pmc_id_fields=groups.pmc_id_fields,
            date_fields=groups.date_fields,
            int_fields=groups.int_fields,
            float_fields=groups.float_fields,
            set_like_fields=groups.set_like_fields,
            json_string_fields=groups.json_string_fields,
            boolean_fields=groups.boolean_fields,
            flag_fields=groups.flag_fields,
            operator_fields=groups.operator_fields,
            ontology_id_fields=groups.ontology_id_fields,
            enum_fields=groups.enum_fields,
            case_fields=groups.case_fields,
            unit_fields=groups.unit_fields,
            null_fields=groups.null_fields,
            special_rules=special_rules,
        )
    )
