<<<<<<< Updated upstream
"""Tests for additional publication/compound normalization profiles."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import (
    CROSSREF_PUBLICATION_PROFILE,
    PUBCHEM_COMPOUND_PROFILE,
    PUBMED_PUBLICATION_PROFILE,
)
from bioetl.infrastructure.schemas.silver import (
    CROSSREF_PUBLICATION_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
)


def test_crossref_publication_profile_covers_schema_exactly() -> None:
    CROSSREF_PUBLICATION_PROFILE.assert_covers_schema(CROSSREF_PUBLICATION_SCHEMA.names)


def test_pubmed_publication_profile_covers_schema_exactly() -> None:
    PUBMED_PUBLICATION_PROFILE.assert_covers_schema(PUBMED_PUBLICATION_SCHEMA.names)


def test_pubchem_compound_profile_covers_schema_exactly() -> None:
    PUBCHEM_COMPOUND_PROFILE.assert_covers_schema(PUBCHEM_COMPOUND_SCHEMA.names)


def test_publication_profiles_exclude_meta_fields_from_hash() -> None:
    assert "_run_id" in CROSSREF_PUBLICATION_PROFILE.hash_excluded_fields
    assert "_dq_error" in PUBMED_PUBLICATION_PROFILE.hash_excluded_fields


def test_pubchem_compound_profile_uses_smiles_and_float_specific_rules() -> None:
    assert (
        PUBCHEM_COMPOUND_PROFILE.rule_for("canonical_smiles").normalizer.__name__
        == "<lambda>"
    )
    assert (
        PUBCHEM_COMPOUND_PROFILE.rule_for("molecular_weight").normalizer.__name__
        == "normalize_profile_float"
    )
||||||| Stash base
=======
"""Tests for additional shipped normalization profiles."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import (
    CROSSREF_PUBLICATION_PROFILE,
    CROSSREF_PUBLICATION_SCHEMA_FIELDS,
    PUBCHEM_COMPOUND_PROFILE,
    PUBCHEM_COMPOUND_SCHEMA_FIELDS,
    PUBMED_PUBLICATION_PROFILE,
    PUBMED_PUBLICATION_SCHEMA_FIELDS,
)


def test_crossref_publication_profile_covers_schema_exactly() -> None:
    CROSSREF_PUBLICATION_PROFILE.assert_covers_schema(CROSSREF_PUBLICATION_SCHEMA_FIELDS)


def test_pubmed_publication_profile_covers_schema_exactly() -> None:
    PUBMED_PUBLICATION_PROFILE.assert_covers_schema(PUBMED_PUBLICATION_SCHEMA_FIELDS)


def test_pubchem_compound_profile_covers_schema_exactly() -> None:
    PUBCHEM_COMPOUND_PROFILE.assert_covers_schema(PUBCHEM_COMPOUND_SCHEMA_FIELDS)


def test_meta_fields_are_excluded_from_hash_across_shipped_profiles() -> None:
    assert "_run_id" in CROSSREF_PUBLICATION_PROFILE.hash_excluded_fields
    assert "_run_id" in PUBMED_PUBLICATION_PROFILE.hash_excluded_fields
    assert "_run_id" in PUBCHEM_COMPOUND_PROFILE.hash_excluded_fields


def test_pubchem_smiles_rules_use_domain_smiles_normalization() -> None:
    canonical_rule = PUBCHEM_COMPOUND_PROFILE.rule_for("canonical_smiles")
    isomeric_rule = PUBCHEM_COMPOUND_PROFILE.rule_for("isomeric_smiles")

    assert canonical_rule is not None
    assert canonical_rule.apply(" C ") == "C"
    assert isomeric_rule is not None
    assert isomeric_rule.apply(" C ") == "C"
>>>>>>> Stashed changes
