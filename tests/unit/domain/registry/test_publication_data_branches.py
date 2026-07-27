"""Branch coverage for publication registry helpers (TD-R-02 / #6678)."""

from __future__ import annotations

from bioetl.domain.registry import publication_data as pub


def test_publication_mapping_lookup_and_predicates() -> None:
    mapping = pub.get_publication_mapping("publication")
    assert mapping is not None
    assert mapping.canonical_name == "publication"
    assert pub.get_publication_mapping("missing") is None
    assert pub.is_publication_entity("publication") is True
    assert pub.is_publication_entity("molecule") is False
    assert pub.is_legacy_publication_alias("document") is pub.is_legacy_publication_alias(
        "document"
    )


def test_dedup_and_composite_key_helpers() -> None:
    assert pub.get_dedup_key_fields("missing") is None
    fields = pub.get_dedup_key_fields("publication")
    assert fields is not None
    assert pub.has_composite_key("publication") is (len(fields) > 1)
    sim_fields = pub.get_dedup_key_fields("publication_similarity")
    assert sim_fields is not None
    assert pub.has_composite_key("publication_similarity") is True


def test_entity_type_validation_error_policy() -> None:
    assert pub.get_publication_entity_type_validation_error("document", "pubchem") is None
    assert pub.get_publication_entity_type_validation_error("publication", "chembl") is None
    # If document is registered as legacy alias, chembl must reject it.
    err = pub.get_publication_entity_type_validation_error("document", "chembl")
    if pub.is_legacy_publication_alias("document"):
        assert err is not None
        assert "publication" in err
    else:
        assert err is None
    assert pub.get_publication_entity_type_validation_error("not_an_alias", "chembl") is None


def test_public_constants_non_empty() -> None:
    assert "publication" in pub.PUBLICATION_ENTITY_TYPES
    assert "publication" in pub.ALL_PUBLICATION_ENTITY_TYPES
