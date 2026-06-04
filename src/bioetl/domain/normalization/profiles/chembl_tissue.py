"""Normalization profile for the ChEMBL Tissue Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.chembl import (
    BTO_ONTOLOGY_VERSION,
    EFO_ONTOLOGY_VERSION,
    UBERON_ONTOLOGY_VERSION,
)
from bioetl.domain.normalization.profiles._profile_ontology_companion_normalizers import (
    build_obo_companion_iri_normalizer,
    build_obo_companion_mapping_status_normalizer,
    build_obo_companion_version_normalizer,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.schemas.chembl.tissue import TissueSchema

from ._chembl_reference_identifier_rules import chembl_reference_identifier_rules
from ._chembl_vocab import chembl_enum
from .chembl_policy_registry import chembl_ontology_family_fields

__all__ = [
    "CHEMBL_TISSUE_PROFILE",
    "CHEMBL_TISSUE_SCHEMA_FIELDS",
]

CHEMBL_TISSUE_SCHEMA_FIELDS = tuple(TissueSchema.to_schema().columns.keys())

_META_FIELDS = frozenset(
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
_TITLE_FIELDS = frozenset({"pref_name"})
_ONTOLOGY_ID_FIELDS = (
    chembl_ontology_family_fields("bto", entity="tissue")
    | chembl_ontology_family_fields("caloha", entity="tissue")
    | chembl_ontology_family_fields("efo", entity="tissue")
    | chembl_ontology_family_fields("uberon", entity="tissue")
)
_ENUM_FIELDS = {
    "bto_mapping_status": chembl_enum("tissue", "bto_mapping_status"),
    "efo_mapping_status": chembl_enum("tissue", "efo_mapping_status"),
    "uberon_mapping_status": chembl_enum("tissue", "uberon_mapping_status"),
}
_OBO_COMPANION_SPECS = {
    "bto": ("bto_id", "BTO_", BTO_ONTOLOGY_VERSION),
    "efo": ("efo_id", "EFO_", EFO_ONTOLOGY_VERSION),
    "uberon": ("uberon_id", "UBERON_", UBERON_ONTOLOGY_VERSION),
}
_REFERENCE_IDENTIFIER_RULES = chembl_reference_identifier_rules("tissue")
_SPECIAL_RULES = (
    _REFERENCE_IDENTIFIER_RULES
    | {
        f"{family}_iri": (
            build_obo_companion_iri_normalizer(
                source_field=source_field,
                canonical_prefix=canonical_prefix,
                ontology_version=ontology_version,
            ),
            f"Resolve the {family.upper()} ontology companion bundle from sibling "
            "normalized identifiers and emit the canonical OBO IRI.",
        )
        for family, (
            source_field,
            canonical_prefix,
            ontology_version,
        ) in _OBO_COMPANION_SPECS.items()
    }
    | {
        f"{family}_mapping_status": (
            build_obo_companion_mapping_status_normalizer(
                source_field=source_field,
                canonical_prefix=canonical_prefix,
                ontology_version=ontology_version,
            ),
            f"Resolve the {family.upper()} ontology companion bundle from sibling "
            "normalized identifiers and emit the canonical mapping-status enum.",
        )
        for family, (
            source_field,
            canonical_prefix,
            ontology_version,
        ) in _OBO_COMPANION_SPECS.items()
    }
    | {
        f"{family}_ontology_version": (
            build_obo_companion_version_normalizer(
                source_field=source_field,
                canonical_prefix=canonical_prefix,
                ontology_version=ontology_version,
            ),
            f"Resolve the {family.upper()} ontology companion bundle from sibling "
            "normalized identifiers and emit the ontology version when a mapping "
            "context exists.",
        )
        for family, (
            source_field,
            canonical_prefix,
            ontology_version,
        ) in _OBO_COMPANION_SPECS.items()
    }
)

CHEMBL_TISSUE_PROFILE = build_standard_profile(
    profile_name="chembl.tissue",
    description="Canonical field-level normalization policy for the ChEMBL Tissue Silver schema.",
    schema_fields=CHEMBL_TISSUE_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    ontology_id_fields=_ONTOLOGY_ID_FIELDS,
    enum_fields=_ENUM_FIELDS,
    special_rules=_SPECIAL_RULES,
    null_fields=chembl_pseudo_null_fields("tissue"),
)

CHEMBL_TISSUE_PROFILE.assert_covers_schema(CHEMBL_TISSUE_SCHEMA_FIELDS)
