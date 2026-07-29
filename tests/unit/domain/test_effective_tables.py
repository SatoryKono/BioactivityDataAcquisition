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
"""Unit tests for effective Silver/Gold table name properties."""

from __future__ import annotations

import pytest

from bioetl.domain.config import PipelineConfig, TableConfig


pytestmark = pytest.mark.unit


def test_effective_silver_table_uses_explicit_value() -> None:
    config = PipelineConfig(
        pipeline_name="p1",
        provider="chembl",
        entity_type="activity",
        table=TableConfig(primary_keys=("id",), silver_table="custom.silver"),
    )

    assert config.effective_silver_table == "custom.silver"


def test_effective_silver_table_falls_back_to_provider_entity() -> None:
    config = PipelineConfig(
        pipeline_name="p1",
        provider="chembl",
        entity_type="activity",
        table=TableConfig(primary_keys=("id",), silver_table=None),
    )

    assert config.effective_silver_table == "chembl.activity"


def test_effective_gold_table_uses_explicit_value() -> None:
    config = PipelineConfig(
        pipeline_name="p1",
        provider="chembl",
        entity_type="activity",
        table=TableConfig(primary_keys=("id",), gold_table="custom.gold"),
    )

    assert config.effective_gold_table == "custom.gold"


def test_effective_gold_table_falls_back_to_provider_entity() -> None:
    config = PipelineConfig(
        pipeline_name="p1",
        provider="chembl",
        entity_type="activity",
        table=TableConfig(primary_keys=("id",), gold_table=None),
    )

    assert config.effective_gold_table == "chembl.activity"
