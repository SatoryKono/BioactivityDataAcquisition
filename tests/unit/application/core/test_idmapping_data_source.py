"""Tests for IDMappingDataSource.

Coverage target: ≥80%
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.idmapping_data_source import IDMappingDataSource
from bioetl.domain.types import HealthStatus


class TestIDMappingDataSourceInit:
    """Tests for IDMappingDataSource initialization."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock ID mapping client."""
        return MagicMock()

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    def test_initialization(
        self, mock_client: MagicMock, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        """Test IDMappingDataSource initialization."""
        input_path = tmp_path / "input.csv"
        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=input_path,
            logger=mock_logger,
        )

        assert data_source.provider_name == "uniprot_idmapping"
        assert data_source._input_path == input_path
        assert data_source._from_db == "ChEMBL"
        assert data_source._to_db == "UniProtKB"
        assert data_source._id_column == "target_chembl_id"

    def test_initialization_custom_params(
        self, mock_client: MagicMock, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        """Test IDMappingDataSource with custom parameters."""
        input_path = tmp_path / "input.csv"
        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=input_path,
            logger=mock_logger,
            from_db="UniProtKB",
            to_db="PDB",
            id_column="uniprot_id",
        )

        assert data_source._from_db == "UniProtKB"
        assert data_source._to_db == "PDB"
        assert data_source._id_column == "uniprot_id"

    def test_repr(
        self, mock_client: MagicMock, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        """Test __repr__ method."""
        input_path = tmp_path / "input.csv"
        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=input_path,
            logger=mock_logger,
        )

        repr_str = repr(data_source)
        assert "IDMappingDataSource" in repr_str
        assert "input.csv" in repr_str
        assert "ChEMBL" in repr_str
        assert "UniProtKB" in repr_str


class TestIDMappingDataSourceContextManager:
    """Tests for async context manager."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock ID mapping client."""
        return MagicMock()

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_async_context_manager(
        self, mock_client: MagicMock, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        """Test async context manager enter/exit."""
        input_path = tmp_path / "input.csv"
        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=input_path,
            logger=mock_logger,
        )

        assert data_source._is_open is False

        async with data_source as ds:
            assert ds._is_open is True
            assert ds is data_source

        assert data_source._is_open is False

    @pytest.mark.asyncio
    async def test_aclose(
        self, mock_client: MagicMock, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        """Test aclose method."""
        input_path = tmp_path / "input.csv"
        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=input_path,
            logger=mock_logger,
        )

        data_source._is_open = True
        await data_source.aclose()
        assert data_source._is_open is False


class TestIDMappingDataSourceFetch:
    """Tests for fetch method."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock ID mapping client."""
        client = MagicMock()
        client.map_ids = AsyncMock(
            return_value={
                "CHEMBL204": "P00742",
                "CHEMBL205": "P12345",
            }
        )
        return client

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    @pytest.fixture
    def sample_csv(self, tmp_path: Path) -> Path:
        """Create sample CSV file."""
        csv_path = tmp_path / "targets.csv"
        csv_path.write_text(
            "target_chembl_id,name\n"
            "CHEMBL204,Target 1\n"
            "CHEMBL205,Target 2\n"
            "CHEMBL206,Target 3\n"
        )
        return csv_path

    @pytest.mark.asyncio
    async def test_fetch_success(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        sample_csv: Path,
    ) -> None:
        """Test successful fetch with mapping results."""
        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=sample_csv,
            logger=mock_logger,
        )

        records = []
        async for record in data_source.fetch("idmapping"):
            records.append(record)

        assert len(records) == 3
        assert records[0]["target_chembl_id"] == "CHEMBL204"
        assert records[0]["uniprot_accession"] == "P00742"
        assert records[1]["target_chembl_id"] == "CHEMBL205"
        assert records[1]["uniprot_accession"] == "P12345"
        assert records[2]["target_chembl_id"] == "CHEMBL206"
        assert records[2]["uniprot_accession"] is None  # Not in mapping results

    @pytest.mark.asyncio
    async def test_fetch_with_limit(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        sample_csv: Path,
    ) -> None:
        """Test fetch with limit parameter."""
        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=sample_csv,
            logger=mock_logger,
        )

        records = []
        async for record in data_source.fetch("idmapping", limit=2):
            records.append(record)

        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_fetch_empty_csv(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test fetch with empty CSV (only header)."""
        csv_path = tmp_path / "empty.csv"
        csv_path.write_text("target_chembl_id,name\n")

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
        )

        records = []
        async for record in data_source.fetch("idmapping"):
            records.append(record)

        assert len(records) == 0
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_fetch_wrong_entity_type(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        sample_csv: Path,
    ) -> None:
        """Test fetch logs warning for unexpected entity type."""
        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=sample_csv,
            logger=mock_logger,
        )

        records = []
        async for record in data_source.fetch("wrong_entity_type"):
            records.append(record)

        # Should still work but log warning
        assert len(records) == 3
        mock_logger.warning.assert_called_with(
            "unexpected_entity_type",
            expected="idmapping",
            received="wrong_entity_type",
        )


class TestIDMappingDataSourceReadChEMBLIds:
    """Tests for _read_chembl_ids method."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock ID mapping client."""
        return MagicMock()

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    def test_read_chembl_ids_success(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful reading of ChEMBL IDs."""
        csv_path = tmp_path / "targets.csv"
        csv_path.write_text(
            "target_chembl_id,name\nCHEMBL204,Target 1\nCHEMBL205,Target 2\n"
        )

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
        )

        ids = data_source._read_chembl_ids()
        assert ids == ["CHEMBL204", "CHEMBL205"]

    def test_read_chembl_ids_file_not_found(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test FileNotFoundError when input file doesn't exist."""
        csv_path = tmp_path / "nonexistent.csv"

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
        )

        with pytest.raises(FileNotFoundError, match="Input file not found"):
            data_source._read_chembl_ids()

    def test_read_chembl_ids_missing_column(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test ValueError when required column is missing."""
        csv_path = tmp_path / "missing_col.csv"
        csv_path.write_text("other_column,name\nVAL1,Name1\n")

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
        )

        with pytest.raises(ValueError, match="Missing required column"):
            data_source._read_chembl_ids()

    def test_read_chembl_ids_skips_empty(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that empty IDs are skipped."""
        csv_path = tmp_path / "with_empty.csv"
        csv_path.write_text(
            "target_chembl_id,name\n"
            "CHEMBL204,Target 1\n"
            ",Empty\n"
            "  ,Whitespace\n"
            "CHEMBL205,Target 2\n"
        )

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
        )

        ids = data_source._read_chembl_ids()
        assert ids == ["CHEMBL204", "CHEMBL205"]

    def test_read_chembl_ids_strips_whitespace(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that IDs are stripped of whitespace."""
        csv_path = tmp_path / "with_whitespace.csv"
        csv_path.write_text(
            "target_chembl_id,name\n  CHEMBL204  ,Target 1\nCHEMBL205\t,Target 2\n"
        )

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
        )

        ids = data_source._read_chembl_ids()
        assert ids == ["CHEMBL204", "CHEMBL205"]


class TestIDMappingDataSourceHealthCheck:
    """Tests for health_check method."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock ID mapping client."""
        client = MagicMock()
        client.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
        return client

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_health_check_healthy(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test health_check returns HEALTHY when all checks pass."""
        csv_path = tmp_path / "input.csv"
        csv_path.write_text("target_chembl_id\nCHEMBL1\n")

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
        )

        status = await data_source.health_check()

        assert status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_file_missing(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test health_check returns UNHEALTHY when input file is missing."""
        csv_path = tmp_path / "nonexistent.csv"

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
        )

        status = await data_source.health_check()

        assert status == HealthStatus.UNHEALTHY
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_health_check_api_unhealthy(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test health_check returns API status when file exists but API is unhealthy."""
        csv_path = tmp_path / "input.csv"
        csv_path.write_text("target_chembl_id\nCHEMBL1\n")
        mock_client.health_check = AsyncMock(return_value=HealthStatus.UNHEALTHY)

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
        )

        status = await data_source.health_check()

        assert status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_health_check_api_degraded(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test health_check returns DEGRADED when API is degraded."""
        csv_path = tmp_path / "input.csv"
        csv_path.write_text("target_chembl_id\nCHEMBL1\n")
        mock_client.health_check = AsyncMock(return_value=HealthStatus.DEGRADED)

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
        )

        status = await data_source.health_check()

        assert status == HealthStatus.DEGRADED


class TestIDMappingDataSourceEdgeCases:
    """Edge case tests for IDMappingDataSource."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock ID mapping client."""
        return MagicMock()

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_fetch_with_custom_id_column(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test fetch with custom ID column name."""
        csv_path = tmp_path / "custom.csv"
        csv_path.write_text("custom_id,name\nCHEMBL1,Name1\n")

        mock_client.map_ids = AsyncMock(return_value={"CHEMBL1": "P00001"})

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
            id_column="custom_id",
        )

        records = []
        async for record in data_source.fetch("idmapping"):
            records.append(record)

        assert len(records) == 1
        assert records[0]["target_chembl_id"] == "CHEMBL1"

    @pytest.mark.asyncio
    async def test_fetch_logs_statistics(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that fetch logs mapping statistics."""
        csv_path = tmp_path / "targets.csv"
        csv_path.write_text("target_chembl_id\nCHEMBL1\nCHEMBL2\n")

        mock_client.map_ids = AsyncMock(return_value={"CHEMBL1": "P00001"})

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
        )

        records = []
        async for record in data_source.fetch("idmapping"):
            records.append(record)

        # Check that completion log was called
        mock_logger.info.assert_called()
        # Find the completion call
        info_calls = mock_logger.info.call_args_list
        completion_call = None
        for call in info_calls:
            if "idmapping_fetch_completed" in str(call):
                completion_call = call
                break

        assert completion_call is not None

    @pytest.mark.asyncio
    async def test_fetch_ignores_filter_params(
        self,
        mock_client: MagicMock,
        mock_logger: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that fetch ignores query, filter_ids, filter_field params."""
        csv_path = tmp_path / "targets.csv"
        csv_path.write_text("target_chembl_id\nCHEMBL1\n")

        mock_client.map_ids = AsyncMock(return_value={"CHEMBL1": "P00001"})

        data_source = IDMappingDataSource(
            idmapping_client=mock_client,
            input_path=csv_path,
            logger=mock_logger,
        )

        records = []
        async for record in data_source.fetch(
            "idmapping",
            query="ignored",
            filter_ids=["ignored"],
            filter_field="ignored",
        ):
            records.append(record)

        # Should still work correctly
        assert len(records) == 1
