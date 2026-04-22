"""Normalization profile for the ChEMBL Publication Similarity Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._chembl_profile_helpers import (
    build_chembl_profile,
    chembl_schema_fields,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.schemas.chembl.publication_similarity import (
    PublicationSimilaritySchema,
)

__all__ = [
    "CHEMBL_PUBLICATION_SIMILARITY_PROFILE",
    "CHEMBL_PUBLICATION_SIMILARITY_SCHEMA_FIELDS",
]

CHEMBL_PUBLICATION_SIMILARITY_SCHEMA_FIELDS = chembl_schema_fields(
    PublicationSimilaritySchema
)
_PMID_FIELDS = frozenset({"pubmed_id1", "pubmed_id2"})
_INT_FIELDS = frozenset({"sim_id", "doc_1", "doc_2"})
_FLOAT_FIELDS = frozenset({"tid_tani", "mol_tani", "avg_tani", "max_tani"})

CHEMBL_PUBLICATION_SIMILARITY_PROFILE = build_chembl_profile(
    entity="publication_similarity",
    description="Canonical field-level normalization policy for the ChEMBL Publication Similarity Silver schema.",
    schema_fields=CHEMBL_PUBLICATION_SIMILARITY_SCHEMA_FIELDS,
    pmid_fields=_PMID_FIELDS,
    int_fields=_INT_FIELDS,
    float_fields=_FLOAT_FIELDS,
    null_fields=chembl_pseudo_null_fields("publication_similarity"),
)

CHEMBL_PUBLICATION_SIMILARITY_PROFILE.assert_covers_schema(
    CHEMBL_PUBLICATION_SIMILARITY_SCHEMA_FIELDS
)
