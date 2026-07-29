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
"""Tests for registered Pandera check methods in validators.py."""

from __future__ import annotations

import pandas as pd
import pytest

from bioetl.domain.schemas import validators as validators_module
from bioetl.domain.schemas.validators import (
    in_closed_range,
    is_non_negative,
    is_positive,
    max_str_length,
    str_matches_pattern,
    str_starts_with,
)

pytestmark = pytest.mark.unit


class TestRegisteredNumericChecks:
    def test_is_non_negative_allows_nulls(self) -> None:
        series = pd.Series([None, -1.0, 0.0, 1.5])
        result = is_non_negative(series, min_value=True)
        assert result.tolist() == [True, False, True, True]

    def test_is_positive_allows_nulls(self) -> None:
        series = pd.Series([None, 0, 1, 2])
        result = is_positive(series, min_value=True)
        assert result.tolist() == [True, False, True, True]

    def test_in_closed_range_bounds(self) -> None:
        series = pd.Series([None, -1, 0, 50, 100, 101])
        result = in_closed_range(series, min_val=0, max_val=100)
        assert result.tolist() == [True, False, True, True, True, False]


class TestRegisteredStringChecks:
    def test_max_str_length(self) -> None:
        series = pd.Series([None, "ab", "abcd"])
        result = max_str_length(series, max_len=3)
        assert result.tolist() == [True, True, False]

    def test_str_starts_with(self) -> None:
        series = pd.Series([None, "InChI=1", "SMILES"])
        result = str_starts_with(series, prefix="InChI=")
        assert result.tolist() == [True, True, False]

    def test_str_matches_pattern(self) -> None:
        series = pd.Series([None, "CHEMBL25", "BAD"])
        result = str_matches_pattern(series, pattern=r"^CHEMBL\d+$")
        assert result.tolist() == [True, True, False]


class TestPrebuiltJsonChecks:
    def test_json_check_names_are_registered(self) -> None:
        assert validators_module.JSON_CHECK.name == "valid_json"
        assert validators_module.JSON_ARRAY_CHECK.name == "valid_json_array"
        assert validators_module.JSON_OBJECT_CHECK.name == "valid_json_object"
