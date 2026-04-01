"""Unit tests for composite join-key normalization policy helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import polars as pl
import pytest

from bioetl.application.composite.join_key_normalization import (
    normalize_join_key_dataframe_columns,
    normalize_join_key_text,
    validate_join_key_normalization_policies,
)


@pytest.mark.unit
def test_normalize_join_key_text_applies_trim_and_lowercase_for_doi() -> None:
    assert normalize_join_key_text(" 10.1000/ABC ", key="doi") == "10.1000/abc"


@pytest.mark.unit
def test_normalize_join_key_dataframe_columns_trims_title_without_lowercase() -> None:
    df = pl.DataFrame({"title": ["  Mixed Case Title  "]})

    result = normalize_join_key_dataframe_columns(df=df, join_keys=("title",))

    assert result["title"].to_list() == ["Mixed Case Title"]


@pytest.mark.unit
def test_validate_join_key_normalization_policies_rejects_unknown_join_key() -> None:
    config = cast(
        Any,
        SimpleNamespace(
            enrichers=(SimpleNamespace(join_keys=("mystery_key",)),),
            dependencies=(),
        ),
    )

    with pytest.raises(ValueError, match="mystery_key"):
        validate_join_key_normalization_policies(config)
