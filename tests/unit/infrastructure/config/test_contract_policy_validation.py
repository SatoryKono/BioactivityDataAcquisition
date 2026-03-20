"""Unit tests for canonical contract policy validation helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.config.contract_policy_validation import (
    resolve_silver_columns,
    schema_columns,
    validate_pipeline_contract_policy,
)


@pytest.mark.unit
def test_schema_columns_extracts_column_names() -> None:
    schema_cls = MagicMock()
    resolved = MagicMock()
    resolved.columns = {"col_a": MagicMock(), "col_b": MagicMock()}
    schema_cls.to_schema.return_value = resolved

    result = schema_columns(schema_cls)

    assert result == {"col_a", "col_b"}


@pytest.mark.unit
def test_schema_columns_raises_when_schema_has_no_to_schema() -> None:
    with pytest.raises(ValueError, match="does not expose to_schema"):
        schema_columns(SimpleNamespace())


@pytest.mark.unit
def test_resolve_silver_columns_prefers_pandera_schema() -> None:
    pandera_schema = MagicMock()
    resolved = MagicMock()
    resolved.columns = {"x": MagicMock()}
    pandera_schema.to_schema.return_value = resolved

    result = resolve_silver_columns(
        provider="test",
        entity_type="entity",
        pandera_silver_schema=pandera_schema,
        silver_schema=MagicMock(),
    )

    assert result == {"x"}


@pytest.mark.unit
def test_validate_pipeline_contract_policy_raises_when_keys_missing() -> None:
    pandera_schema = MagicMock()
    pandera_resolved = MagicMock()
    pandera_resolved.columns = {"pk": MagicMock()}
    pandera_schema.to_schema.return_value = pandera_resolved

    gold_schema = MagicMock()
    gold_resolved = MagicMock()
    gold_resolved.columns = {"pk": MagicMock()}
    gold_schema.to_schema.return_value = gold_resolved

    with pytest.raises(ValueError, match="Invalid contract policy"):
        validate_pipeline_contract_policy(
            provider="test",
            entity_type="entity",
            pandera_silver_schema=pandera_schema,
            silver_schema=None,
            gold_schema=gold_schema,
            load_policy=lambda _provider, _entity: SimpleNamespace(
                primary_key=["pk", "missing_key"],
                merge_keys=[],
            ),
        )
