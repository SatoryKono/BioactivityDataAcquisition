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
"""Unit tests for workflow row reconciliation domain contracts."""

from __future__ import annotations

import pytest

from bioetl.domain.ports import (
    RowReconciliationConfig,
    RowReconciliationConfigError,
    RowReconciliationLayer,
    RowReconciliationTypePolicy,
)

pytestmark = pytest.mark.unit


def test_row_reconciliation_config_normalizes_valid_values() -> None:
    config = RowReconciliationConfig(
        layer=" SILVER ",
        left_table=" chembl.activity ",
        right_table=" chembl.target ",
        left_columns=(" target_id ",),
        right_columns=(" target_id ",),
        left_primary_keys=(" activity_id ",),
        type_policy="STRICT",
        workflow_name=" nightly ",
    )

    assert config.layer is RowReconciliationLayer.SILVER
    assert config.type_policy is RowReconciliationTypePolicy.STRICT
    assert config.left_table == "chembl.activity"
    assert config.right_table == "chembl.target"
    assert config.left_columns == ("target_id",)
    assert config.right_columns == ("target_id",)
    assert config.left_primary_keys == ("activity_id",)
    assert config.workflow_name == "nightly"


def test_row_reconciliation_config_rejects_bronze_layer() -> None:
    with pytest.raises(RowReconciliationConfigError, match=r"silver.*gold"):
        RowReconciliationConfig(
            layer="bronze",
            left_table="chembl.activity",
            right_table="chembl.target",
            left_columns=("target_id",),
            right_columns=("target_id",),
            left_primary_keys=("activity_id",),
        )


def test_row_reconciliation_config_rejects_mismatched_key_cardinality() -> None:
    with pytest.raises(RowReconciliationConfigError, match="same length"):
        RowReconciliationConfig(
            layer="silver",
            left_table="chembl.activity",
            right_table="chembl.target",
            left_columns=("target_id", "assay_id"),
            right_columns=("target_id",),
            left_primary_keys=("activity_id",),
        )


def test_row_reconciliation_config_rejects_duplicate_names_per_side() -> None:
    with pytest.raises(RowReconciliationConfigError, match="left_columns"):
        RowReconciliationConfig(
            layer="silver",
            left_table="chembl.activity",
            right_table="chembl.target",
            left_columns=("target_id", "target_id"),
            right_columns=("target_id", "target_type"),
            left_primary_keys=("activity_id",),
        )


def test_row_reconciliation_config_rejects_unsupported_type_policy() -> None:
    with pytest.raises(RowReconciliationConfigError, match="type_policy"):
        RowReconciliationConfig(
            layer="gold",
            left_table="chembl.activity",
            right_table="chembl.target",
            left_columns=("target_id",),
            right_columns=("target_id",),
            left_primary_keys=("activity_id",),
            type_policy="coerce",
        )
