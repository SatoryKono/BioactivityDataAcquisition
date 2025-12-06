from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.domain.validation.factories import (
    default_schema_provider,
    default_validator,
)
from bioetl.domain.validation.impl.pandera_validator import PanderaValidatorImpl


def test_default_validator():
    schema = "dummy"
    validator = default_validator(schema)
    assert isinstance(validator, PanderaValidatorImpl)
    assert validator.schema == schema

def test_default_schema_provider():
    provider = default_schema_provider()
    assert isinstance(provider, SchemaRegistry)
