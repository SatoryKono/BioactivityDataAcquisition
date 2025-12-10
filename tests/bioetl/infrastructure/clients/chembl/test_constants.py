"""Tests for ChEMBL constants module."""

import pytest

from bioetl.infrastructure.clients.chembl.constants import (
    ENTITY_ENDPOINT_ALIASES,
    SUPPORTED_ENTITIES,
    resolve_endpoint,
)


class TestEntityEndpointAliases:
    """Tests for ENTITY_ENDPOINT_ALIASES mapping."""

    def test_contains_all_expected_entities(self):
        """Verify all expected entities are present in the mapping."""
        expected_entities = {"activity", "assay", "target", "molecule", "publication"}
        assert set(ENTITY_ENDPOINT_ALIASES.keys()) == expected_entities

    def test_publication_maps_to_document(self):
        """
        Verify 'publication' maps to 'document'.

        ChEMBL API uses 'document' endpoint for publication data,
        while our domain uses 'publication' as the entity name.
        """
        assert ENTITY_ENDPOINT_ALIASES["publication"] == "document"

    def test_direct_mappings(self):
        """Verify direct entity-to-endpoint mappings (same name)."""
        direct_mappings = ["activity", "assay", "target", "molecule"]
        for entity in direct_mappings:
            assert ENTITY_ENDPOINT_ALIASES[entity] == entity

    def test_mapping_is_immutable(self):
        """Verify ENTITY_ENDPOINT_ALIASES cannot be modified."""
        with pytest.raises(TypeError):
            ENTITY_ENDPOINT_ALIASES["new_entity"] = "new_endpoint"  # type: ignore[index]

    def test_all_endpoints_are_strings(self):
        """Verify all endpoint values are non-empty strings."""
        for entity, endpoint in ENTITY_ENDPOINT_ALIASES.items():
            assert isinstance(entity, str), f"Entity key {entity!r} is not a string"
            assert isinstance(endpoint, str), f"Endpoint {endpoint!r} is not a string"
            assert entity, "Entity key should not be empty"
            assert endpoint, "Endpoint value should not be empty"


class TestSupportedEntities:
    """Tests for SUPPORTED_ENTITIES frozenset."""

    def test_matches_aliases_keys(self):
        """Verify SUPPORTED_ENTITIES matches ENTITY_ENDPOINT_ALIASES keys."""
        assert SUPPORTED_ENTITIES == frozenset(ENTITY_ENDPOINT_ALIASES.keys())

    def test_is_immutable(self):
        """Verify SUPPORTED_ENTITIES is a frozenset."""
        assert isinstance(SUPPORTED_ENTITIES, frozenset)


class TestResolveEndpoint:
    """Tests for resolve_endpoint function."""

    @pytest.mark.parametrize(
        "entity,expected_endpoint",
        [
            ("activity", "activity"),
            ("assay", "assay"),
            ("target", "target"),
            ("molecule", "molecule"),
            ("publication", "document"),
        ],
    )
    def test_resolves_valid_entities(self, entity: str, expected_endpoint: str):
        """Verify resolve_endpoint returns correct endpoint for valid entities."""
        assert resolve_endpoint(entity) == expected_endpoint

    def test_raises_for_unknown_entity(self):
        """Verify resolve_endpoint raises ValueError for unknown entities."""
        with pytest.raises(ValueError, match="Unknown entity: unknown"):
            resolve_endpoint("unknown")

    def test_raises_for_empty_entity(self):
        """Verify resolve_endpoint raises ValueError for empty entity."""
        with pytest.raises(ValueError, match="Unknown entity: "):
            resolve_endpoint("")
