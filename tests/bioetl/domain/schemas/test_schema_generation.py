import pandas as pd

from bioetl.domain.schemas.generator import generate_schema_from_column_order
from bioetl.domain.schemas.registry import SchemaRegistry
from bioetl.infrastructure.validation.impl.pandera_validator import PanderaValidatorImpl
from bioetl.infrastructure.validation.schemas.generator import (
    load_column_order_from_yaml,
)


def test_generate_schema_from_column_order_validates_missing_columns():
    columns = ["id", "value"]
    schema = generate_schema_from_column_order(columns)
    validator = PanderaValidatorImpl(schema)

    ok_df = pd.DataFrame({"id": [1], "value": ["x"]})
    assert validator.validate(ok_df).is_valid

    invalid_df = pd.DataFrame({"id": [1]})
    result = validator.validate(invalid_df)

    assert not result.is_valid
    assert result.errors


def test_register_schema_from_yaml(tmp_path):
    yaml_path = tmp_path / "columns.yaml"
    yaml_path.write_text("- id\n- name\n", encoding="utf-8")

    column_order = load_column_order_from_yaml(yaml_path)
    registry = SchemaRegistry()
    registry.register("from_yaml", None, column_order=column_order)

    schema = registry.get_schema("from_yaml")
    # Check that schema can be used for validation
    # (works with both old and new Pandera API)
    assert hasattr(schema, "validate") or hasattr(schema, "columns")
    assert registry.get_schema_columns("from_yaml") == ["id", "name"]

    validator = PanderaValidatorImpl(schema)
    result = validator.validate(pd.DataFrame({"id": [1]}))
    assert not result.is_valid
