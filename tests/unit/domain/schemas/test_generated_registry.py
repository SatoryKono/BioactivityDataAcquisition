# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for generated schema registry."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestCanonicalSchemaRegistryEntry:
    """Tests for CanonicalSchemaRegistryEntry dataclass."""

    def test_import(self) -> None:
        """Test that the module can be imported."""
        from bioetl.domain.schemas.generated import (
            CANONICAL_SCHEMA_REGISTRY,
            CanonicalSchemaRegistryEntry,
        )

        assert CanonicalSchemaRegistryEntry is not None
        assert CANONICAL_SCHEMA_REGISTRY is not None

    def test_schema_registry_entry__registry_is_tuple__3043e502(self) -> None:
        """Test that CANONICAL_SCHEMA_REGISTRY is a tuple."""
        from bioetl.domain.schemas.generated import CANONICAL_SCHEMA_REGISTRY

        assert isinstance(CANONICAL_SCHEMA_REGISTRY, tuple)

    def test_registry_is_non_empty(self) -> None:
        """Test that CANONICAL_SCHEMA_REGISTRY has entries."""
        from bioetl.domain.schemas.generated import CANONICAL_SCHEMA_REGISTRY

        assert len(CANONICAL_SCHEMA_REGISTRY) > 0

    def test_entry_fields(self) -> None:
        """Test that registry entries have required fields."""
        from bioetl.domain.schemas.generated import (
            CANONICAL_SCHEMA_REGISTRY,
            CanonicalSchemaRegistryEntry,
        )

        entry = CANONICAL_SCHEMA_REGISTRY[0]
        assert isinstance(entry, CanonicalSchemaRegistryEntry)
        assert isinstance(entry.provider, str)
        assert isinstance(entry.entity, str)
        assert isinstance(entry.yaml_path, str)
        assert isinstance(entry.column_groups, tuple)

    def test_schema_registry_entry__entry_creation__6c4df3d1(self) -> None:
        """Test creating a CanonicalSchemaRegistryEntry directly."""
        from bioetl.domain.schemas.generated import CanonicalSchemaRegistryEntry

        entry = CanonicalSchemaRegistryEntry(
            provider="chembl",
            entity="activity",
            yaml_path="chembl/activity.yaml",
            column_groups=("system", "business", "dq"),
        )
        assert entry.provider == "chembl"
        assert entry.entity == "activity"
        assert entry.yaml_path == "chembl/activity.yaml"
        assert entry.column_groups == ("system", "business", "dq")

    def test_schema_registry_entry__entry_is_frozen__b9f9ba6a(self) -> None:
        """Test that CanonicalSchemaRegistryEntry is immutable."""
        from bioetl.domain.schemas.generated import CanonicalSchemaRegistryEntry

        entry = CanonicalSchemaRegistryEntry(
            provider="chembl",
            entity="activity",
            yaml_path="chembl/activity.yaml",
            column_groups=("system",),
        )
        with pytest.raises((AttributeError, TypeError)):
            entry.provider = "pubchem"  # type: ignore[misc]

    def test_chembl_activity_entry_exists(self) -> None:
        """Test that ChEMBL activity entry is in the registry."""
        from bioetl.domain.schemas.generated import CANONICAL_SCHEMA_REGISTRY

        providers_entities = {(e.provider, e.entity) for e in CANONICAL_SCHEMA_REGISTRY}
        assert ("chembl", "activity") in providers_entities

    def test_all_entries_have_non_empty_fields(self) -> None:
        """Test that all registry entries have non-empty required fields."""
        from bioetl.domain.schemas.generated import CANONICAL_SCHEMA_REGISTRY

        for entry in CANONICAL_SCHEMA_REGISTRY:
            assert entry.provider, f"Entry has empty provider: {entry}"
            assert entry.entity, f"Entry has empty entity: {entry}"
            assert entry.yaml_path, f"Entry has empty yaml_path: {entry}"
            assert len(entry.column_groups) > 0, (
                f"Entry has empty column_groups: {entry}"
            )
