"""Unit tests for pipeline-construction protocol contracts."""

from __future__ import annotations

import pytest

from typing import Protocol
from typing import get_type_hints

from bioetl.composition.factories.pipeline import construction_types


pytestmark = pytest.mark.unit

def test_pipeline_construction_protocols_expose_expected_public_contracts() -> None:
    """Construction protocol module should expose stable callable contracts."""
    assert issubclass(construction_types.EntityTypeExtractor, Protocol)
    assert issubclass(construction_types.DomainConfigMapper, Protocol)
    assert issubclass(construction_types.ContractPolicyLoader, Protocol)
    assert issubclass(construction_types._SchemaBuilder, Protocol)


def test_pipeline_construction_protocols_preserve_expected_return_hints() -> None:
    """Construction protocol call signatures should keep their typed return contracts."""
    entity_hints = get_type_hints(construction_types.EntityTypeExtractor.__call__)
    schema_hints = get_type_hints(construction_types._SchemaBuilder.to_schema)

    assert entity_hints["return"] == str | None
    assert schema_hints["return"] is object
