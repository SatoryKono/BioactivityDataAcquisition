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
"""Unit tests for IDMappingCsvReaderAdapter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.adapters.input.idmapping_csv_reader_adapter import (
    IDMappingCsvReaderAdapter,
)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock LoggerPort."""
    return MagicMock()


@pytest.fixture
def csv_reader(mock_logger: MagicMock) -> IDMappingCsvReaderAdapter:
    """Create ID mapping CSV reader adapter."""
    return IDMappingCsvReaderAdapter(logger=mock_logger)


@pytest.mark.unit
class TestIDMappingCsvReaderAdapter:
    """Tests for source reader adapter behavior."""

    @staticmethod
    def _write_csv(tmp_path: Path, name: str, content: str) -> str:
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    async def test_read_ids_success(
        self, csv_reader: IDMappingCsvReaderAdapter, tmp_path: Path
    ) -> None:
        """Test successful ID loading from CSV."""
        path = self._write_csv(
            tmp_path,
            "ids.csv",
            "target_id,name\nCHEMBL204,Target 1\n,Empty\nCHEMBL205,Target 2\n",
        )

        ids = await csv_reader.read_ids(path, "target_id")
        assert ids == ["CHEMBL204", "CHEMBL205"]

    async def test_read_ids_file_not_found(
        self, csv_reader: IDMappingCsvReaderAdapter
    ) -> None:
        """Test FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            await csv_reader.read_ids("/missing/input.csv", "target_id")

    async def test_read_ids_missing_column(
        self, csv_reader: IDMappingCsvReaderAdapter, tmp_path: Path
    ) -> None:
        """Test ValueError when configured column does not exist."""
        path = self._write_csv(
            tmp_path,
            "missing-column.csv",
            "other_column,name\nVALUE,Name\n",
        )

        with pytest.raises(ValueError, match="Missing required column"):
            await csv_reader.read_ids(path, "target_id")

    async def test_source_exists(
        self, csv_reader: IDMappingCsvReaderAdapter, tmp_path: Path
    ) -> None:
        """Test source existence checks."""
        path = self._write_csv(tmp_path, "exists.csv", "target_id\nCHEMBL1\n")

        assert await csv_reader.source_exists(path) is True
        assert await csv_reader.source_exists(f"{path}.missing") is False
