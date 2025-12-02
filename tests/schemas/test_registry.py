import pytest
from bioetl.domain.schemas.registry import SchemaRegistry

def test_registry_flow():
    registry = SchemaRegistry()
    
    # Test register and get
    registry.register("test", "schema_mock")
    assert registry.get_schema("test") == "schema_mock"
    
    # Test list
    assert "test" in registry.list_schemas()
    
    # Test failure
    with pytest.raises(ValueError):
        registry.get_schema("unknown")
