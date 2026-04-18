#!/usr/bin/env python3
"""Test script for SilverMaintenanceOperations."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, 'src')

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.silver.operations.maintenance_operations import (
    SilverMaintenanceOperations,
)


def test_maintenance_operations():
    """Test that maintenance operations work correctly."""
    print("Testing SilverMaintenanceOperations...")

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
        audit=mock_audit
    )

    print("✓ SilverMaintenanceOperations instance created")

    # Test maybe_export_csv with exporter
    print("Testing maybe_export_csv with exporter...")
    mock_csv_exporter.export = AsyncMock()

    import pyarrow as pa
    table_data = pa.table({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

    # This should call the exporter
    maintenance_ops.maybe_export_csv("test_table", table_data, "/tmp/test", mode="append")

    # Verify exporter was called
    mock_csv_exporter.export.assert_called_once()
    print("✓ CSV export called correctly")

    # Test maybe_export_csv without exporter
    print("Testing maybe_export_csv without exporter...")
    maintenance_ops_no_exporter = SilverMaintenanceOperations(
        csv_exporter=None,
        retention_manager=mock_retention_manager,
        metrics=mock_metrics,
        audit=mock_audit
    )

    # This should not call anything
    maintenance_ops_no_exporter.maybe_export_csv("test_table", table_data, "/tmp/test", mode="append")
    print("✓ CSV export handled None exporter correctly")

    # Test vacuum operation
    print("Testing vacuum operation...")
    mock_retention_manager.vacuum = AsyncMock(return_value({"files_removed": 2, "status": "success"}))

    result = maintenance_ops.vacuum("test_table", retention_hours=24)

    # Verify vacuum was called
    mock_retention_manager.vacuum.assert_called_once_with("test_table", retention_hours=24, dry_run=False)
    assert result["files_removed"] == 2
    print("✓ Vacuum operation works correctly")

    # Test optimize operation
    print("Testing optimize operation...")
    result = maintenance_ops.optimize("test_table")
    assert result["table"] == "test_table"
    assert result["status"] == "success"
    print("✓ Optimize operation works correctly")

    print("\n✅ All maintenance operations tests passed!")


if __name__ == "__main__":
    test_maintenance_operations()
