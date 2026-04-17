"""Unit tests for ColumnOrderer rename functionality."""

from bioetl.application.composite.column_service import (
    ColumnOrderService as ColumnOrderer,
)
from bioetl.domain.composite.config import ColumnGroupConfig, LayerColumnConfig
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


class TestColumnOrdererRenames:
    """Test ColumnOrderer rename functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = NoOpLogger()

    def test_apply_renames_basic(self):
        """Apply basic column renames."""
        orderer = ColumnOrderer(self.logger)
        columns = ["entity_id", "doi", "pmid", "title"]
        rename_map = {"entity_id": "publication_id", "pmid": "pubmed_id"}

        renamed = orderer._apply_renames(columns, rename_map)

        assert renamed == ["publication_id", "doi", "pubmed_id", "title"]

    def test_apply_renames_empty_map(self):
        """Empty rename map returns original columns."""
        orderer = ColumnOrderer(self.logger)
        columns = ["entity_id", "doi", "title"]

        renamed = orderer._apply_renames(columns, {})

        assert renamed == columns

    def test_apply_renames_partial(self):
        """Only specified columns are renamed."""
        orderer = ColumnOrderer(self.logger)
        columns = ["entity_id", "doi", "pmid", "title"]
        rename_map = {"doi": "digital_object_id"}

        renamed = orderer._apply_renames(columns, rename_map)

        assert renamed == ["entity_id", "digital_object_id", "pmid", "title"]

    def test_filter_by_layer_config_with_renames(self):
        """filter_by_layer_config applies renames to explicit columns."""
        orderer = ColumnOrderer(self.logger)
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
        orderer = ColumnOrderer(self.logger, column_groups=column_groups)

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
        orderer = ColumnOrderer(self.logger)
        available = ["entity_id", "doi", "title"]
        layer_config = LayerColumnConfig(columns=["entity_id", "doi"])

        result = orderer.filter_by_layer_config(available, layer_config)

        assert result == ["entity_id", "doi"]

    def test_rename_preserves_order(self):
        """Renames preserve the original column order."""
        orderer = ColumnOrderer(self.logger)
        columns = ["z_field", "a_field", "m_field"]
        rename_map = {"z_field": "renamed_z", "a_field": "renamed_a"}

        renamed = orderer._apply_renames(columns, rename_map)

        assert renamed == ["renamed_z", "renamed_a", "m_field"]

    def test_rename_with_conflicting_names(self):
        """Renames can create conflicts (caller responsibility to avoid)."""
        orderer = ColumnOrderer(self.logger)
        columns = ["field_a", "field_b"]
        rename_map = {"field_a": "same_name", "field_b": "same_name"}

        renamed = orderer._apply_renames(columns, rename_map)

        # Both renamed to same_name (conflict not prevented at this level)
        assert renamed == ["same_name", "same_name"]
