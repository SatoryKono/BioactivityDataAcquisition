# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Contract matrix for domain schema validators and registered Pandera checks."""

from __future__ import annotations

import pandas as pd
import pandera as pa
import pandera.pandas as ppa
import pytest
from pandera.typing import Series

from bioetl.domain.schemas.validators import (
    JSON_ARRAY_CHECK,
    JSON_CHECK,
    JSON_OBJECT_CHECK,
    in_closed_range,
    is_non_negative,
    is_positive,
    max_str_length,
    rows_are_valid_json,
    rows_are_valid_json_array,
    rows_are_valid_json_object,
    str_matches_pattern,
    str_starts_with,
)

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


class _ValidatorProbeSchema(ppa.DataFrameModel):
    """Tiny schema exercising registered Field-level validators."""

    score: Series[int] = ppa.Field(
        is_non_negative=True, in_closed_range={"min_val": 0, "max_val": 100}
    )
    rank: Series[int] = ppa.Field(is_positive=True)
    label: Series[str] = ppa.Field(max_str_length={"max_len": 5})
    chembl_id: Series[str] = ppa.Field(str_matches_pattern={"pattern": r"^CHEMBL\d+$"})
    inchi: Series[str] = ppa.Field(str_starts_with={"prefix": "InChI="})

    class Config:
        strict = True
        coerce = True


def _probe_df(**overrides: object) -> pd.DataFrame:
    row = {
        "score": 10,
        "rank": 1,
        "label": "ok",
        "chembl_id": "CHEMBL25",
        "inchi": "InChI=1/CH4/h1H4",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_validator_probe_schema_accepts_minimal_valid_row() -> None:
    validated = _ValidatorProbeSchema.validate(_probe_df())
    assert validated["chembl_id"].iloc[0] == "CHEMBL25"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("score", -1),
        ("score", 101),
        ("rank", 0),
        ("label", "toolong"),
        ("chembl_id", "BAD"),
        ("inchi", "SMILES"),
    ],
)
def test_validator_probe_schema_rejects_constraint_violations(
    field: str,
    value: object,
) -> None:
    with pytest.raises(pa.errors.SchemaError):
        _ValidatorProbeSchema.validate(_probe_df(**{field: value}))


def test_rows_are_valid_json_matrix() -> None:
    series = pd.Series(['{"a": 1}', "bad", None])
    assert rows_are_valid_json(series).tolist() == [True, False, True]


def test_rows_are_valid_json_array_matrix() -> None:
    series = pd.Series(["[1]", "{}", None])
    assert rows_are_valid_json_array(series).tolist() == [True, False, True]


def test_rows_are_valid_json_object_matrix() -> None:
    series = pd.Series(["{}", "[]", None])
    assert rows_are_valid_json_object(series).tolist() == [True, False, True]


def test_json_array_and_object_validators_reject_malformed_json() -> None:
    malformed = pd.Series(["not-json"])
    assert rows_are_valid_json_array(malformed).tolist() == [False]
    assert rows_are_valid_json_object(malformed).tolist() == [False]


def test_prebuilt_json_checks_are_named() -> None:
    assert JSON_CHECK.name == "valid_json"
    assert JSON_ARRAY_CHECK.name == "valid_json_array"
    assert JSON_OBJECT_CHECK.name == "valid_json_object"


@pytest.mark.parametrize(
    ("func", "series", "kwargs", "expected"),
    [
        (
            is_non_negative,
            pd.Series([0, 2, None]),
            {"min_value": True},
            [True, True, True],
        ),
        (
            is_non_negative,
            pd.Series([-1, 0, None]),
            {"min_value": 0},
            [False, True, True],
        ),
        (is_positive, pd.Series([1, 2, None]), {"min_value": True}, [True, True, True]),
        (is_positive, pd.Series([0, 1, None]), {"min_value": 1}, [False, True, True]),
        (
            in_closed_range,
            pd.Series([-1, 0, 5, None]),
            {"min_val": 0, "max_val": 5},
            [False, True, True, True],
        ),
        (
            max_str_length,
            pd.Series(["ok", "toolong", None]),
            {"max_len": 5},
            [True, False, True],
        ),
        (
            str_starts_with,
            pd.Series(["InChI=1/CH4", "SMILES", None]),
            {"prefix": "InChI="},
            [True, False, True],
        ),
        (
            str_matches_pattern,
            pd.Series(["CHEMBL1", "BAD", None]),
            {"pattern": r"^CHEMBL\d+$"},
            [True, False, True],
        ),
    ],
)
def test_registered_validator_helpers_cover_null_and_boundary_paths(
    func,
    series: pd.Series,
    kwargs: dict[str, object],
    expected: list[bool],
) -> None:
    assert func(series, **kwargs).tolist() == expected
