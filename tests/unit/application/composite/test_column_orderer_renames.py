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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for ColumnOrderService rename functionality."""

import pytest
from unittest.mock import MagicMock

from bioetl.application.composite.column_service import (
    ColumnOrderService,
)
from bioetl.application.composite.column_orderer_group_flow import (
    filter_columns_by_groups,
    order_by_yaml_groups,
)
from bioetl.domain.composite.config import ColumnGroupConfig, LayerColumnConfig


pytestmark = pytest.mark.unit


class TestColumnOrderServiceRenames:
    """Test ColumnOrderService rename functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = MagicMock()

    def test_apply_renames_basic(self):
        """Apply basic column renames."""
        orderer = ColumnOrderService(self.logger)
        columns = ["entity_id", "doi", "pmid", "title"]
        rename_map = {"entity_id": "publication_id", "pmid": "pubmed_id"}

        renamed = orderer._apply_renames(columns, rename_map)

        assert renamed == ["publication_id", "doi", "pubmed_id", "title"]

    def test_apply_renames_empty_map(self):
        """Empty rename map returns original columns."""
        orderer = ColumnOrderService(self.logger)
        columns = ["entity_id", "doi", "title"]

        renamed = orderer._apply_renames(columns, {})

        assert renamed == columns

    def test_apply_renames_partial(self):
        """Only specified columns are renamed."""
        orderer = ColumnOrderService(self.logger)
        columns = ["entity_id", "doi", "pmid", "title"]
        rename_map = {"doi": "digital_object_id"}

        renamed = orderer._apply_renames(columns, rename_map)

        assert renamed == ["entity_id", "digital_object_id", "pmid", "title"]

    def test_filter_by_layer_config_with_renames(self):
        """filter_by_layer_config applies renames to explicit columns."""
        orderer = ColumnOrderService(self.logger)
        available = ["entity_id", "doi", "pmid", "title", "abstract"]
        layer_config = LayerColumnConfig(
            columns=["entity_id", "doi", "title"],
            rename_fields={"entity_id": "publication_id", "doi": "digital_object_id"},
        )

        result = orderer.filter_by_layer_config(available, layer_config)

        assert result == ["publication_id", "digital_object_id", "title"]

    def test_filter_by_layer_config_groups_with_renames(self):
        """filter_by_layer_config applies renames with group filtering."""
        column_groups = [
            ColumnGroupConfig(name="system", fields=["entity_id", "_run_id"]),
            ColumnGroupConfig(name="identifiers", fields=["doi", "pmid"]),
            ColumnGroupConfig(name="title", fields=["title"]),
        ]
        orderer = ColumnOrderService(self.logger, column_groups=column_groups)

        available = ["entity_id", "_run_id", "doi", "pmid", "title", "abstract"]
        layer_config = LayerColumnConfig(
            include_groups=["system", "identifiers"],
            rename_fields={"_run_id": "pipeline_run_id", "pmid": "pubmed_id"},
        )

        result = orderer.filter_by_layer_config(available, layer_config)

        # Should include system + identifiers groups, with renames applied
        assert "entity_id" in result
        assert "pipeline_run_id" in result
        assert "_run_id" not in result
        assert "doi" in result
        assert "pubmed_id" in result
        assert "pmid" not in result
        assert "title" not in result  # Not in include_groups

    def test_filter_by_layer_config_no_renames(self):
        """filter_by_layer_config works without renames."""
        orderer = ColumnOrderService(self.logger)
        available = ["entity_id", "doi", "title"]
        layer_config = LayerColumnConfig(columns=["entity_id", "doi"])

        result = orderer.filter_by_layer_config(available, layer_config)

        assert result == ["entity_id", "doi"]

    def test_rename_preserves_order(self):
        """Renames preserve the original column order."""
        orderer = ColumnOrderService(self.logger)
        columns = ["z_field", "a_field", "m_field"]
        rename_map = {"z_field": "renamed_z", "a_field": "renamed_a"}

        renamed = orderer._apply_renames(columns, rename_map)

        assert renamed == ["renamed_z", "renamed_a", "m_field"]

    def test_rename_with_conflicting_names(self):
        """Renames can create conflicts (caller responsibility to avoid)."""
        orderer = ColumnOrderService(self.logger)
        columns = ["field_a", "field_b"]
        rename_map = {"field_a": "same_name", "field_b": "same_name"}

        renamed = orderer._apply_renames(columns, rename_map)

        # Both renamed to same_name (conflict not prevented at this level)
        assert renamed == ["same_name", "same_name"]


class TestColumnOrdererGroupFlowBranches:
    """Cover empty configuration, DQ suffix, and exclusion behavior."""

    def test_order_by_yaml_groups_without_groups_preserves_input_order(self) -> None:
        """Absent YAML groups are a transparent no-op rather than a sort."""
        columns = ["z", "a", "entity_id"]

        assert order_by_yaml_groups(
            columns=columns,
            column_groups=None,
            collect_group_columns=MagicMock(),
            logger=MagicMock(),
        ) == columns

    def test_order_by_yaml_groups_logs_ungrouped_and_moves_dq_suffix(self) -> None:
        """Ungrouped fields are stable-sorted while DQ fields stay last exactly once."""
        logger = MagicMock()
        group = ColumnGroupConfig(name="core", fields=["entity_id", "_dq_error"])

        def _collect(available: set[str], _group: ColumnGroupConfig) -> list[str]:
            return [name for name in ("entity_id", "_dq_error") if name in available]

        result = order_by_yaml_groups(
            columns=["zeta", "entity_id", "alpha", "_dq_warn", "_dq_error"],
            column_groups=[group],
            collect_group_columns=_collect,
            logger=logger,
        )

        assert result == ["entity_id", "alpha", "zeta", "_dq_error", "_dq_warn"]
        logger.debug.assert_called_once_with(
            "Ungrouped columns added at end",
            count=2,
            sample=["alpha", "zeta"],
        )

    def test_filter_columns_by_groups_without_definitions_warns_and_preserves(self) -> (
        None
    ):
        """An include request without configured groups remains lossless and visible."""
        logger = MagicMock()
        config = LayerColumnConfig(include_groups=["identifiers"])
        columns = ["entity_id", "value"]

        result = filter_columns_by_groups(
            columns=columns,
            layer_config=config,
            column_groups=None,
            collect_group_columns=MagicMock(),
            logger=logger,
        )

        assert result == columns
        logger.warning.assert_called_once_with(
            "include_groups specified but no column_groups configured",
            include_groups=config.include_groups,
        )

    def test_filter_columns_by_groups_applies_exclusions_and_renames(self) -> None:
        """Glob exclusions run before deterministic ordering and output renames."""
        group = ColumnGroupConfig(
            name="identifiers",
            fields=["entity_id", "public_id", "private_secret"],
        )
        config = LayerColumnConfig(
            include_groups=["identifiers"],
            exclude_fields=["*_secret"],
            rename_fields={"public_id": "external_id"},
        )

        def _collect(available: set[str], _group: ColumnGroupConfig) -> list[str]:
            return [
                name
                for name in ("entity_id", "public_id", "private_secret")
                if name in available
            ]

        result = filter_columns_by_groups(
            columns=["entity_id", "public_id", "private_secret", "ignored"],
            layer_config=config,
            column_groups=[group],
            collect_group_columns=_collect,
            logger=MagicMock(),
        )

        assert result == ["entity_id", "external_id"]
