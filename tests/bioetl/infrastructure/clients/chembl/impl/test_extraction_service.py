"""Tests for ChemblExtractionServiceImpl."""

from unittest.mock import Mock

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.ports.providers import DefaultFieldProviderABC
from bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl import (
    ChemblExtractionServiceImpl,
)


def test_attach_entity_fields_uses_provider():
    """Test that field provider is used to populate fields."""
    import inspect
    import sys

    import bioetl
    from bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl import (
        ChemblExtractionServiceImpl,
    )

    print(f"\nDEBUG: sys.path: {sys.path}")
    print(f"DEBUG: bioetl file: {bioetl.__file__}")
    print(f"DEBUG: Service file: {inspect.getfile(ChemblExtractionServiceImpl)}")
    print(
        f"DEBUG: Init signature: "
        f"{inspect.signature(ChemblExtractionServiceImpl.__init__)}"
    )

    client = Mock(spec=DataClientABC)
    client.provider = "chembl"

    mock_provider = Mock(spec=DefaultFieldProviderABC)
    mock_provider.get_default_fields.return_value = ["col1", "col2"]

    service = ChemblExtractionServiceImpl(client, field_provider=mock_provider)

    # Case 1: entity="assay", no fields provided
    filters = {}
    result = service._attach_entity_fields("assay", filters)

    assert result["fields"] == "col1,col2"
    mock_provider.get_default_fields.assert_called_with("assay")


def test_attach_entity_fields_skips_if_fields_present():
    """Test that provider is ignored if fields are already present."""
    client = Mock(spec=DataClientABC)
    client.provider = "chembl"
    mock_provider = Mock(spec=DefaultFieldProviderABC)

    service = ChemblExtractionServiceImpl(client, field_provider=mock_provider)

    filters = {"fields": "custom"}
    result = service._attach_entity_fields("assay", filters)

    assert result["fields"] == "custom"
    mock_provider.get_default_fields.assert_not_called()


def test_attach_entity_fields_no_provider():
    """Test fallback when no provider is configured."""
    client = Mock(spec=DataClientABC)
    client.provider = "chembl"

    service = ChemblExtractionServiceImpl(client, field_provider=None)

    filters = {}
    result = service._attach_entity_fields("assay", filters)

    assert "fields" not in result


if __name__ == "__main__":
    import os
    import sys

    # Add src to sys.path
    src_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../../../src")
    )
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    print(f"DEBUG: sys.path[0]: {sys.path[0]}")

    import inspect

    from bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl import (
        ChemblExtractionServiceImpl,
    )

    print(f"DEBUG: Service file: {inspect.getfile(ChemblExtractionServiceImpl)}")
    print(
        f"DEBUG: Init signature: "
        f"{inspect.signature(ChemblExtractionServiceImpl.__init__)}"
    )

    try:
        test_attach_entity_fields_uses_provider()
        print("Test passed!")
    except Exception as e:
        print(f"Test failed: {e}")
