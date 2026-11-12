"""Invalid nullable values survive normalization so schema checks can reject them."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
import pytest
from bioetl.infrastructure.validation.pandera_validator import PanderaSilverValidator

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "dtype,method",
    [
        (pd.Int64Dtype(), "_normalize_nullable_integer_columns"),
        (pd.BooleanDtype(), "_normalize_nullable_boolean_columns"),
    ],
)
def test_invalid_nullable_lexeme_is_preserved_for_schema_rejection(dtype, method):
    schema = pa.DataFrameSchema({"value": pa.Column(dtype, nullable=True)})
    validator = PanderaSilverValidator(schema=schema)
    frame = pd.DataFrame({"value": ["not-a-valid-lexeme"]}, dtype=object)
    before = frame.copy(deep=True)
    normalized = getattr(validator, method)(frame)
    pd.testing.assert_frame_equal(normalized, before)
    pd.testing.assert_frame_equal(frame, before)
    result = validator.validate(frame.to_dict(orient="records"))
    assert result.valid is False
    assert result.errors
