"""Publication identity validation and caller-owned vocabularies stay explicit."""

import pytest

from bioetl.domain.mapping.publication_controlled_vocabulary import (
    PublicationControlledVocabularyRegistry,
    publication_controlled_vocabulary_values,
)
from bioetl.domain.mapping.publication_type_classification import _get_lookup
from bioetl.domain.schemas.chembl.similarity_pair import (
    validate_legacy_pair,
    validate_public_pair,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "pair", [(None, "CHEMBL1"), ("CHEMBL1", None), ("1", "CHEMBL2")]
)
def test_public_pair_requires_two_public_identifiers(pair):
    with pytest.raises(ValueError, match="Both public document"):
        validate_public_pair(*pair)


def test_public_pair_rejects_self_similarity():
    with pytest.raises(ValueError, match="similar to itself"):
        validate_public_pair("CHEMBL1", "CHEMBL1")


@pytest.mark.parametrize("pair", [(None, 1), (1, None)])
def test_legacy_pair_requires_both_internal_identifiers(pair):
    with pytest.raises(ValueError, match="Both document identifiers"):
        validate_legacy_pair(*pair)


def test_explicit_vocabulary_is_not_replaced_by_global_registry():
    registry = PublicationControlledVocabularyRegistry(
        {("pubmed", "publication_type"): frozenset({"Review"})}
    )
    assert publication_controlled_vocabulary_values(
        "PUBMED", "publication_type", registry
    ) == frozenset({"Review"})
    assert (
        publication_controlled_vocabulary_values(
            "unknown", "publication_type", registry
        )
        == frozenset()
    )


def test_unsupported_provider_lookup_does_not_invent_a_taxonomy():
    assert _get_lookup("unsupported-provider") is None


@pytest.mark.parametrize("layer", ["silver", "gold"])
def test_similarity_dataframe_requires_complete_distinct_pairs(layer):
    import pandas as pd

    from bioetl.domain.contracts.gold._chembl_reference_publication_schemas import (
        ChEMBLPublicationSimilarityGoldSchema,
    )
    from bioetl.domain.schemas.chembl.publication_similarity import (
        PublicationSimilaritySchema,
    )

    frame = pd.DataFrame(
        [
            {"publication_id1": "CHEMBL1", "publication_id2": "CHEMBL2"},
            {"publication_id1": "CHEMBL1", "publication_id2": None},
            {"publication_id1": "CHEMBL1", "publication_id2": "CHEMBL1"},
        ]
    )
    schema = (
        PublicationSimilaritySchema
        if layer == "silver"
        else ChEMBLPublicationSimilarityGoldSchema
    )
    assert schema.complete_document_pair(frame).tolist() == [True, False, False]
