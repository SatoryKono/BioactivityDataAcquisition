"""Same-path owner tests for generated schema registry module."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from bioetl.domain.schemas.generated.registry import (
    CANONICAL_SCHEMA_REGISTRY,
    CanonicalSchemaRegistryEntry,
)


pytestmark = pytest.mark.unit

def test_generated_registry_exposes_entries_for_canonical_schema_inventory() -> None:
    assert CANONICAL_SCHEMA_REGISTRY
    assert all(
        isinstance(entry, CanonicalSchemaRegistryEntry)
        for entry in CANONICAL_SCHEMA_REGISTRY
    )
    assert any(
        entry.provider == "pubchem" and entry.entity == "compound"
        for entry in CANONICAL_SCHEMA_REGISTRY
    )


def test_generated_registry_entry_dataclass_is_frozen() -> None:
    entry = CANONICAL_SCHEMA_REGISTRY[0]
    with pytest.raises(FrozenInstanceError):
        entry.provider = "mutated"  # type: ignore[misc]
