import pandas as pd
import pandera.pandas as pa

from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.infrastructure.validation.factories import (
    PanderaSchemaProviderFactory,
    default_schema_provider_factory,
    default_validator_factory,
)
from bioetl.infrastructure.validation.impl.pandera_validator import PanderaValidatorImpl


class DummySchema(pa.DataFrameModel):
    id: int = pa.Field(ge=0)
    name: str = pa.Field()


def test_pandera_validator_success():
    validator = PanderaValidatorImpl(DummySchema)
    df = pd.DataFrame({"id": [1], "name": ["a"]})

    result = validator.validate(df)

    assert result.is_valid
    assert result.errors == []
    assert result.validated_df is not None
    pd.testing.assert_frame_equal(result.validated_df, df)


def test_pandera_validator_failure():
    validator = PanderaValidatorImpl(DummySchema)
    df = pd.DataFrame({"id": [-1], "name": ["a"]})

    result = validator.validate(df)

    assert not result.is_valid
    assert result.errors
    assert result.validated_df is None


def test_pandera_validator_exception():
    class BrokenSchema(pa.DataFrameModel):
        id: int = pa.Field()

        @classmethod
        def validate(cls, *_args, **_kwargs):
            raise RuntimeError("boom")

    validator = PanderaValidatorImpl(BrokenSchema)
    result = validator.validate(pd.DataFrame({"id": [1]}))
    assert not result.is_valid
    assert "boom" in result.errors[0]


def test_validator_factory_creates_pandera_validator():
    factory = default_validator_factory()
    validator = factory.create_validator(DummySchema)
    assert isinstance(validator, PanderaValidatorImpl)
    assert validator.is_valid(pd.DataFrame({"id": [1], "name": ["x"]}))


def test_schema_provider_factory_creates_registry():
    default_factory = default_schema_provider_factory()
    provider = default_factory.create_schema_provider()
    assert isinstance(provider, SchemaRegistry)

    provider.register("dummy", DummySchema, column_order=["id", "name"])
    assert provider.get_schema("dummy") is DummySchema
    assert provider.get_schema_columns("dummy") == ["id", "name"]


def test_schema_provider_factory_explicit():
    factory = PanderaSchemaProviderFactory()
    provider = factory.create_schema_provider()
    assert isinstance(provider, SchemaRegistry)
