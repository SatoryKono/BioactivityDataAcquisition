"""Tests for check_delta_integrity.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.ops.data.check_delta_integrity import main

pytestmark = pytest.mark.unit


class TestCheckDeltaIntegrity:
    """Test Delta table integrity checking."""

    @patch("scripts.ops.data.check_delta_integrity.DeltaTable")
    @patch("scripts.ops.data.check_delta_integrity.pl")
    def test_check_delta_integrity_success(self, mock_pl, mock_delta_table):
        """Test successful Delta table integrity check."""
        # Setup mocks
        mock_dt = Mock()
        mock_dt.version.return_value = 1
        mock_dt.files.return_value = ["file1.parquet", "file2.parquet"]
        mock_delta_table.return_value = mock_dt

        mock_df = Mock()
        mock_df.shape = (100, 10)
        mock_pl.read_delta.return_value = mock_df

        # Test
        result = main("data/output/silver/chembl/molecule")

        # Assertions
        assert result == 0
        mock_delta_table.assert_called_once_with("data/output/silver/chembl/molecule")
        mock_dt.version.assert_called_once()
        mock_dt.files.assert_called_once()
        mock_pl.read_delta.assert_called_once_with("data/output/silver/chembl/molecule")

    @patch("scripts.ops.data.check_delta_integrity.DeltaTable")
    @patch("scripts.ops.data.check_delta_integrity.pl")
    def test_check_delta_integrity_default_path(self, mock_pl, mock_delta_table):
        """Test Delta table integrity check with default path."""
        # Setup mocks
        mock_dt = Mock()
        mock_dt.version.return_value = 1
        mock_dt.files.return_value = ["file1.parquet"]
        mock_delta_table.return_value = mock_dt

        mock_df = Mock()
        mock_df.shape = (50, 5)
        mock_pl.read_delta.return_value = mock_df

        # Test with None (should use default)
        result = main(None)

        # Assertions
        assert result == 0
        mock_delta_table.assert_called_once_with("data/output/silver/chembl/molecule")

    @patch("scripts.ops.data.check_delta_integrity.DeltaTable")
    def test_check_delta_integrity_delta_error(self, mock_delta_table):
        """Test Delta table integrity check with Delta error."""
        # Setup mock to raise exception
        mock_delta_table.side_effect = Exception("Delta table not found")

        # Test
        result = main("invalid/path")

        # Assertions
        assert result == 1

    @patch("scripts.ops.data.check_delta_integrity.DeltaTable")
    @patch("scripts.ops.data.check_delta_integrity.pl")
    def test_check_delta_integrity_polars_error(self, mock_pl, mock_delta_table):
        """Test Delta table integrity check with Polars error."""
        # Setup mocks
        mock_dt = Mock()
        mock_dt.version.return_value = 1
        mock_dt.files.return_value = ["file1.parquet"]
        mock_delta_table.return_value = mock_dt

        mock_pl.read_delta.side_effect = Exception("Polars read error")

        # Test
        result = main("data/output/silver/chembl/molecule")

        # Assertions
        assert result == 1
