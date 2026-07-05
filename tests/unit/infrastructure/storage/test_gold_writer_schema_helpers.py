"""Unit tests for Gold writer schema helper functions."""

from __future__ import annotations

from collections import OrderedDict
from types import SimpleNamespace

import pytest

from bioetl.domain.types import GoldSchemaPolicyByVersion, GoldSchemaVersionPolicy
from bioetl.infrastructure.storage.gold.writer_schema_helpers import (
    _project_records_for_gold_schema,
    _resolve_active_gold_schema,
    _schema_column_names,
)


@pytest.mark.unit
class TestGoldWriterSchemaHelpers:
    """Coverage boost for pure Gold schema projection helpers."""

    def test_schema_column_names_prefers_to_schema_and_falls_back_to_columns(
        self,
    ) -> None:
        schema_builder = SimpleNamespace(
            to_schema=lambda: SimpleNamespace(
                columns=OrderedDict((("entity_id", object()), ("value", object())))
            )
        )
        assert _schema_column_names(schema_builder) == ("entity_id", "value")

        broken_builder = SimpleNamespace(
            to_schema=lambda: (_ for _ in ()).throw(RuntimeError("broken")),
            columns=OrderedDict((("fallback", object()),)),
        )
        assert _schema_column_names(broken_builder) == ("fallback",)
        assert _schema_column_names(SimpleNamespace(columns="bad")) == ()

    def test_project_records_for_gold_schema_adds_dq_defaults_when_present(
        self,
    ) -> None:
        schema = SimpleNamespace(
            columns=OrderedDict(
                (
                    ("entity_id", object()),
                    ("_dq_warn", object()),
                    ("_dq_error", object()),
                )
            )
        )

        projected = _project_records_for_gold_schema(
            [{"entity_id": "CHEMBL1"}],
            schema=schema,
        )

        assert projected == [
            {
                "entity_id": "CHEMBL1",
                "_dq_warn": False,
                "_dq_error": False,
            }
        ]
        records = [{"entity_id": "CHEMBL2"}]
        assert _project_records_for_gold_schema(records, schema=object()) is records

    def test_resolve_active_gold_schema_handles_version_policy(self) -> None:
        legacy_schema = object()
        active_schema = object()
        policy = GoldSchemaPolicyByVersion(
            active_version="v2",
            policies=(
                GoldSchemaVersionPolicy(version="v1", schema=legacy_schema),
                GoldSchemaVersionPolicy(version="v2", schema=active_schema),
            ),
        )

        assert _resolve_active_gold_schema(policy) is active_schema
        assert _resolve_active_gold_schema(active_schema) is active_schema
