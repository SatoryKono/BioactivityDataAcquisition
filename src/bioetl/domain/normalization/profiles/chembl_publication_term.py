"""Normalization profile for the ChEMBL Publication Term Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._chembl_profile_helpers import (
    ChemblProfileFieldGroups,
    build_chembl_profile,
    chembl_schema_fields,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema
from bioetl.domain.schemas.constants import PUBLICATION_TERM_TYPES

__all__ = [
    "CHEMBL_PUBLICATION_TERM_PROFILE",
    "CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS",
]

CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS = chembl_schema_fields(PublicationTermSchema)
_TITLE_FIELDS = frozenset({"term"})
_ENUM_FIELDS = {"term_type": PUBLICATION_TERM_TYPES}
_NULL_FIELDS = chembl_pseudo_null_fields("publication_term")

CHEMBL_PUBLICATION_TERM_PROFILE = build_chembl_profile(
    entity="publication_term",
    description="Canonical field-level normalization policy for the ChEMBL Publication Term Silver schema.",
    schema_fields=CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS,
    field_groups=ChemblProfileFieldGroups(
        title_fields=_TITLE_FIELDS,
        enum_fields=_ENUM_FIELDS,
        null_fields=_NULL_FIELDS,
    ),
)

CHEMBL_PUBLICATION_TERM_PROFILE.assert_covers_schema(
    CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS
)
