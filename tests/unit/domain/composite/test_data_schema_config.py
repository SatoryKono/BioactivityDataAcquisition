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
"""Unit tests for DataSchemaConfig and LayerColumnConfig."""

import pytest

from bioetl.domain.composite.config import (
    ColumnGroupConfig,
    DataSchemaConfig,
    LayerColumnConfig,
)
from bioetl.domain.immutability import FrozenDict


pytestmark = pytest.mark.unit


class TestLayerColumnConfig:
    """Test LayerColumnConfig validation and behavior."""

    def test_explicit_columns_mode(self):
        """LayerColumnConfig with explicit columns."""
        config = LayerColumnConfig(
            columns=["entity_id", "doi", "title", "year"],
        )
        assert config.columns == ("entity_id", "doi", "title", "year")
        assert config.column_groups is None
        assert config.include_groups is None
        assert config.exclude_fields is None

    def test_group_filtering_mode(self):
        """LayerColumnConfig with group filtering."""
        config = LayerColumnConfig(
            include_groups=["system", "identifiers", "title"],
            exclude_fields=["_dq_*", "abstract"],
        )
        assert config.include_groups == ("system", "identifiers", "title")
        assert config.exclude_fields == ("_dq_*", "abstract")
        assert config.columns is None
        assert config.column_groups is None

    def test_layer_specific_groups_mode(self):
        """LayerColumnConfig with layer-specific column groups."""
        groups = [
            ColumnGroupConfig(name="system", fields=["entity_id", "content_hash"]),
            ColumnGroupConfig(name="identifiers", fields=["doi", "pmid"]),
        ]
        config = LayerColumnConfig(column_groups=groups)
        assert len(config.column_groups) == 2
        assert config.column_groups[0].name == "system"
        assert config.columns is None
        assert config.include_groups is None

    def test_list_to_tuple_conversion_columns(self):
        """Lists are converted to tuples for columns mode."""
        config = LayerColumnConfig(
            columns=["entity_id", "doi"],
        )
        assert isinstance(config.columns, tuple)

    def test_list_to_tuple_conversion_groups(self):
        """Lists are converted to tuples for group filtering mode."""
        config = LayerColumnConfig(
            include_groups=["system", "identifiers"],
            exclude_fields=["_dq_*"],
        )
        assert isinstance(config.include_groups, tuple)
        assert isinstance(config.exclude_fields, tuple)

    def test_dict_to_column_group_conversion(self):
        """Dicts in column_groups are converted to ColumnGroupConfig."""
        config = LayerColumnConfig(
            column_groups=[
                {"name": "system", "fields": ["entity_id"]},
                {"name": "identifiers", "fields": ["doi"]},
            ]
        )
        assert len(config.column_groups) == 2
        assert isinstance(config.column_groups[0], ColumnGroupConfig)
        assert config.column_groups[0].name == "system"

    def test_mutually_exclusive_modes_validation(self):
        """Only one mode can be specified at a time."""
        with pytest.raises(
            ValueError,
            match="only one of columns/include_groups/column_groups allowed",
        ):
            LayerColumnConfig(
                columns=["entity_id", "doi"],
                include_groups=["system"],
            )

        with pytest.raises(
            ValueError,
            match="only one of columns/include_groups/column_groups allowed",
        ):
            LayerColumnConfig(
                columns=["entity_id"],
                column_groups=[ColumnGroupConfig(name="system", fields=["entity_id"])],
            )

    def test_empty_config_allowed(self):
        """Empty LayerColumnConfig is valid (no filtering)."""
        config = LayerColumnConfig()
        assert config.columns is None
        assert config.column_groups is None
        assert config.include_groups is None
        assert config.exclude_fields is None


class TestDataSchemaConfig:
    """Test DataSchemaConfig validation and behavior."""

    def test_legacy_format_only_column_groups(self):
        """Backward compatible: only column_groups defined."""
        groups = [
            ColumnGroupConfig(name="system", fields=["entity_id"]),
            ColumnGroupConfig(name="identifiers", fields=["doi", "pmid"]),
        ]
        config = DataSchemaConfig(column_groups=groups)
        assert len(config.column_groups) == 2
        assert config.silver is None
        assert config.gold is None

    def test_layer_specific_configs(self):
        """Layer-specific silver/gold configurations."""
        config = DataSchemaConfig(
            column_groups=[
                ColumnGroupConfig(name="system", fields=["entity_id"]),
                ColumnGroupConfig(name="identifiers", fields=["doi"]),
                ColumnGroupConfig(name="abstract", fields=["abstract"]),
            ],
            silver=LayerColumnConfig(
                include_groups=["system", "identifiers", "abstract"],
            ),
            gold=LayerColumnConfig(
                include_groups=["system", "identifiers"],
                exclude_fields=["_dq_*"],
            ),
        )
        assert len(config.column_groups) == 3
        assert config.silver is not None
        assert config.silver.include_groups == ("system", "identifiers", "abstract")
        assert config.gold is not None
        assert config.gold.include_groups == ("system", "identifiers")
        assert config.gold.exclude_fields == ("_dq_*",)

    def test_dict_conversion_for_layers(self):
        """Dict values for silver/gold are converted to LayerColumnConfig."""
        config = DataSchemaConfig(
            column_groups=[],
            silver={"columns": ["entity_id", "doi", "title"]},
            gold={"columns": ["entity_id", "doi"]},
        )
        assert isinstance(config.silver, LayerColumnConfig)
        assert isinstance(config.gold, LayerColumnConfig)
        assert config.silver.columns == ("entity_id", "doi", "title")
        assert config.gold.columns == ("entity_id", "doi")

    def test_get_layer_groups_with_layer_specific(self):
        """get_layer_groups returns layer-specific groups when defined."""
        shared_groups = [ColumnGroupConfig(name="system", fields=["entity_id"])]
        gold_groups = [ColumnGroupConfig(name="identifiers", fields=["doi"])]

        config = DataSchemaConfig(
            column_groups=shared_groups,
            gold=LayerColumnConfig(column_groups=gold_groups),
        )

        assert config.get_layer_groups("silver") == tuple(shared_groups)
        assert config.get_layer_groups("gold") == tuple(gold_groups)

    def test_get_layer_groups_fallback_to_shared(self):
        """get_layer_groups falls back to shared groups when no layer config."""
        shared_groups = [ColumnGroupConfig(name="system", fields=["entity_id"])]
        config = DataSchemaConfig(column_groups=shared_groups)

        assert config.get_layer_groups("silver") == tuple(shared_groups)
        assert config.get_layer_groups("gold") == tuple(shared_groups)

    def test_should_include_group_no_filter(self):
        """should_include_group returns True when no filter specified."""
        config = DataSchemaConfig(
            column_groups=[ColumnGroupConfig(name="system", fields=["entity_id"])],
        )
        assert config.should_include_group("silver", "system") is True
        assert config.should_include_group("silver", "anything") is True

    def test_should_include_group_with_filter(self):
        """should_include_group respects include_groups filter."""
        config = DataSchemaConfig(
            column_groups=[
                ColumnGroupConfig(name="system", fields=["entity_id"]),
                ColumnGroupConfig(name="identifiers", fields=["doi"]),
                ColumnGroupConfig(name="abstract", fields=["abstract"]),
            ],
            gold=LayerColumnConfig(
                include_groups=["system", "identifiers"],
            ),
        )
        assert config.should_include_group("gold", "system") is True
        assert config.should_include_group("gold", "identifiers") is True
        assert config.should_include_group("gold", "abstract") is False

    def test_data_schema_config__empty_config_allowed__3851e270(self):
        """Empty DataSchemaConfig is valid."""
        config = DataSchemaConfig()
        assert config.column_groups == ()
        assert config.silver is None
        assert config.gold is None

    def test_list_to_tuple_conversion_column_groups(self):
        """column_groups list is converted to tuple."""
        config = DataSchemaConfig(
            column_groups=[
                {"name": "system", "fields": ["entity_id"]},
                {"name": "identifiers", "fields": ["doi"]},
            ]
        )
        assert isinstance(config.column_groups, tuple)
        assert len(config.column_groups) == 2
        assert isinstance(config.column_groups[0], ColumnGroupConfig)


class TestLayerColumnConfigRenames:
    """Test rename_fields functionality in LayerColumnConfig."""

    def test_rename_fields_basic(self):
        """LayerColumnConfig with rename_fields mapping."""
        config = LayerColumnConfig(
            columns=["entity_id", "doi", "title"],
            rename_fields={"entity_id": "publication_id", "doi": "digital_object_id"},
        )
        assert config.rename_fields == {
            "entity_id": "publication_id",
            "doi": "digital_object_id",
        }

    def test_rename_fields_with_group_filtering(self):
        """Combine group filtering with renames."""
        config = LayerColumnConfig(
            include_groups=["system", "identifiers"],
            exclude_fields=["_dq_*"],
            rename_fields={"_run_id": "pipeline_run_id", "pmid": "pubmed_id"},
        )
        assert config.include_groups == ("system", "identifiers")
        assert config.rename_fields == {
            "_run_id": "pipeline_run_id",
            "pmid": "pubmed_id",
        }

    def test_rename_fields_empty_dict(self):
        """Empty rename_fields is valid."""
        config = LayerColumnConfig(columns=["entity_id", "doi"])
        assert config.rename_fields == {}

    def test_rename_fields_converts_to_frozen_dict(self):
        """rename_fields is detached into an immutable mapping."""
        config = LayerColumnConfig(
            columns=["entity_id"],
            rename_fields={"entity_id": "pub_id"},
        )
        assert isinstance(config.rename_fields, FrozenDict)


class TestDataSchemaConfigIntegration:
    """Integration tests for DataSchemaConfig with real-world scenarios."""

    def test_publication_composite_schema(self):
        """Realistic composite publication schema with layer filtering."""
        config = DataSchemaConfig(
            column_groups=[
                ColumnGroupConfig(name="system", fields=["entity_id", "_run_id"]),
                ColumnGroupConfig(name="identifiers", fields=["doi", "pmid"]),
                ColumnGroupConfig(name="title", fields=["title"]),
                ColumnGroupConfig(
                    name="abstract", fields=["abstract", "abstract_structured"]
                ),
                ColumnGroupConfig(name="dq", pattern="^_dq_"),
            ],
            silver=LayerColumnConfig(
                include_groups=["system", "identifiers", "title", "abstract", "dq"],
            ),
            gold=LayerColumnConfig(
                include_groups=["system", "identifiers", "title"],
                exclude_fields=["_dq_*", "_composite_*"],
            ),
        )

        # Silver includes all groups
        assert config.should_include_group("silver", "system") is True
        assert config.should_include_group("silver", "abstract") is True
        assert config.should_include_group("silver", "dq") is True

        # Gold excludes abstract and dq
        assert config.should_include_group("gold", "system") is True
        assert config.should_include_group("gold", "identifiers") is True
        assert config.should_include_group("gold", "title") is True
        assert config.should_include_group("gold", "abstract") is False
        assert config.should_include_group("gold", "dq") is False

        # Get effective groups per layer
        silver_groups = config.get_layer_groups("silver")
        gold_groups = config.get_layer_groups("gold")
        assert len(silver_groups) == 5
        assert (
            len(gold_groups) == 5
        )  # Shared groups, filtering applied by should_include_group

    def test_explicit_gold_columns_minimal(self):
        """Gold with explicit minimal column set."""
        config = DataSchemaConfig(
            column_groups=[
                ColumnGroupConfig(name="system", fields=["entity_id"]),
                ColumnGroupConfig(name="identifiers", fields=["doi", "pmid"]),
                ColumnGroupConfig(name="title", fields=["title"]),
                ColumnGroupConfig(name="abstract", fields=["abstract"]),
            ],
            gold=LayerColumnConfig(
                columns=["entity_id", "doi", "title"],
            ),
        )

        assert config.gold.columns == ("entity_id", "doi", "title")
        # Shared groups still available for silver
        assert len(config.column_groups) == 4
