#!/usr/bin/env python3
"""Simple test script for SilverMaintenanceOperations without external dependencies."""

import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, "src")

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.silver.operations.maintenance_operations import (
    SilverMaintenanceOperations,
)


def test_maintenance_operations_simple():
    """Test that maintenance operations work correctly without PyArrow."""
    print("Testing SilverMaintenanceOperations (simple)...")
    with tempfile.TemporaryDirectory(prefix="silver-maintenance-") as temp_dir:
        export_path = f"{temp_dir}/test"

        # Create mock dependencies
        mock_csv_exporter = MagicMock()
        mock_retention_manager = MagicMock()
        mock_metrics = MagicMock()
        mock_audit = MagicMock()

        # Create maintenance operations instance
        maintenance_ops = SilverMaintenanceOperations(
            csv_exporter=mock_csv_exporter,
            retention_manager=mock_retention_manager,
            metrics=mock_metrics,
            audit=mock_audit,
        )

        print("✓ SilverMaintenanceOperations instance created")

        # Test maybe_export_csv with exporter
        print("Testing maybe_export_csv with exporter...")
        mock_csv_exporter.export = AsyncMock()

        # Mock PyArrow table
        mock_table = MagicMock()
        mock_table.__len__.return_value = 3

        # This should call the exporter
        maintenance_ops.maybe_export_csv(
            "test_table", mock_table, export_path, mode="append"
        )

        # Verify exporter was called
        mock_csv_exporter.export.assert_called_once()
        print("✓ CSV export called correctly")

        # Test maybe_export_csv without exporter
        print("Testing maybe_export_csv without exporter...")
        maintenance_ops_no_exporter = SilverMaintenanceOperations(
            csv_exporter=None,
            retention_manager=mock_retention_manager,
            metrics=mock_metrics,
            audit=mock_audit,
        )

        # This should not call anything
        maintenance_ops_no_exporter.maybe_export_csv(
            "test_table", mock_table, export_path, mode="append"
        )
        print("✓ CSV export handled None exporter correctly")

        # Test vacuum operation
        print("Testing vacuum operation...")
        mock_retention_manager.vacuum = AsyncMock(
            return_value({"files_removed": 2, "status": "success"})
        )

        result = maintenance_ops.vacuum("test_table", retention_hours=24)

        # Verify vacuum was called
        mock_retention_manager.vacuum.assert_called_once_with(
            "test_table", retention_hours=24, dry_run=False
        )
        assert result["files_removed"] == 2
        print("✓ Vacuum operation works correctly")

        # Test optimize operation
        print("Testing optimize operation...")
        result = maintenance_ops.optimize("test_table")
        assert result["table"] == "test_table"
        assert result["status"] == "success"
        print("✓ Optimize operation works correctly")

        # Test metrics and audit calls
        print("Testing metrics and audit instrumentation...")
        maintenance_ops.vacuum("test_table", retention_hours=24)

        # Verify metrics and audit were called
        mock_metrics.increment_counter.assert_any_call("silver.vacuum_start")
        mock_metrics.increment_counter.assert_any_call("silver.vacuum_success")
        mock_metrics.gauge.assert_called_with("silver.vacuum_files_removed", 2)
        mock_audit.log_event.assert_called()
        print("✓ Metrics and audit instrumentation works correctly")

        print("\n✅ All maintenance operations tests passed!")


if __name__ == "__main__":
    test_maintenance_operations_simple()
