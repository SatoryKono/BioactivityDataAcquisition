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
"""Tests for IDMappingDataSource."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.idmapping_data_source import IDMappingDataSource
from bioetl.domain.types import HealthStatus


@pytest.fixture
def mock_client() -> MagicMock:
    """Create mock ID mapping client."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.map_ids = AsyncMock(
        return_value={
            "CHEMBL204": {"uniprot_accession": "P00742", "reviewed": True},
            "CHEMBL205": {"uniprot_accession": "P12345", "reviewed": True},
        }
    )
    client.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    return client


@pytest.fixture
def mock_reader() -> MagicMock:
    """Create mock source reader."""
    reader = MagicMock()
    reader.read_ids = AsyncMock(return_value=["CHEMBL204", "CHEMBL205", "CHEMBL206"])
    reader.source_exists = AsyncMock(return_value=True)
    return reader


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    return MagicMock()


@pytest.fixture
def data_source(
    mock_client: MagicMock,
    mock_reader: MagicMock,
    mock_logger: MagicMock,
) -> IDMappingDataSource:
    """Create default IDMappingDataSource instance."""
    return IDMappingDataSource(
        idmapping_client=mock_client,
        id_source_reader=mock_reader,
        input_path="data/input/target.csv",
        logger=mock_logger,
    )


@pytest.mark.unit
class TestIDMappingDataSourceInit:
    """Tests for IDMappingDataSource initialization."""

    def test_data_source_init__initialization__c366614c(
        self, data_source: IDMappingDataSource
    ) -> None:
        """Test default initialization."""
        assert data_source.provider_name == "uniprot_idmapping"
        assert data_source._input_path == "data/input/target.csv"
        assert data_source._from_db == "ChEMBL"
        assert data_source._to_db == "UniProtKB"
        assert data_source._id_column == "target_id"

    def test_initialization_custom_params(
        self,
        mock_client: MagicMock,
        mock_reader: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test initialization with custom parameters."""
        ds = IDMappingDataSource(
            idmapping_client=mock_client,
            id_source_reader=mock_reader,
            input_path="data/input/custom.csv",
            logger=mock_logger,
            from_db="UniProtKB",
            to_db="PDB",
            id_column="uniprot_id",
        )

        assert ds._from_db == "UniProtKB"
        assert ds._to_db == "PDB"
        assert ds._id_column == "uniprot_id"

    def test_repr(self, data_source: IDMappingDataSource) -> None:
        """Test __repr__ method."""
        repr_str = repr(data_source)
        assert "IDMappingDataSource" in repr_str
        assert "target.csv" in repr_str
        assert "ChEMBL" in repr_str
        assert "UniProtKB" in repr_str


@pytest.mark.unit
class TestIDMappingDataSourceContextManager:
    """Tests for async context manager behavior."""

    @pytest.mark.asyncio
    async def test_async_context_manager(
        self, data_source: IDMappingDataSource
    ) -> None:
        """Test async context manager enter/exit."""
        assert data_source._is_open is False

        async with data_source as ds:
            assert ds._is_open is True
            assert ds is data_source

        assert data_source._is_open is False

    @pytest.mark.asyncio
    async def test_aclose(self, data_source: IDMappingDataSource) -> None:
        """Test aclose method closes client context."""
        data_source._is_open = True
        await data_source.aclose()
        assert data_source._is_open is False


@pytest.mark.unit
class TestIDMappingDataSourceFetch:
    """Tests for fetch method."""

    @pytest.mark.asyncio
    async def test_fetch_uses_seed_ids_over_filter_and_reader(
        self,
        mock_client: MagicMock,
        mock_reader: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test priority: seed_ids > filter_ids > source reader."""
        await asyncio.sleep(0)
        mock_client.map_ids = AsyncMock(
            return_value={"CHEMBL1": {"uniprot_accession": "P00001"}}
        )
        ds = IDMappingDataSource(
            idmapping_client=mock_client,
            id_source_reader=mock_reader,
            input_path="data/input/target.csv",
            logger=mock_logger,
            seed_ids=["CHEMBL1", "CHEMBL2"],
        )

        records = [
            record async for record in ds.fetch("idmapping", filter_ids=["CHEMBL999"])
        ]

        assert len(records) == 2
        assert records[0]["target_id"] == "CHEMBL1"
        assert records[1]["target_id"] == "CHEMBL2"
        mock_reader.read_ids.assert_not_called()
        mock_client.map_ids.assert_awaited_once_with(
            from_db="ChEMBL",
            to_db="UniProtKB",
            ids=["CHEMBL1", "CHEMBL2"],
        )

    @pytest.mark.asyncio
    async def test_fetch_uses_filter_ids_when_seed_missing(
        self,
        mock_client: MagicMock,
        mock_reader: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test filter_ids are used when seed_ids are absent."""
        await asyncio.sleep(0)
        ds = IDMappingDataSource(
            idmapping_client=mock_client,
            id_source_reader=mock_reader,
            input_path="data/input/target.csv",
            logger=mock_logger,
        )

        records = [
            record async for record in ds.fetch("idmapping", filter_ids=["CHEMBL1"])
        ]

        assert len(records) == 1
        assert records[0]["target_id"] == "CHEMBL1"
        mock_reader.read_ids.assert_not_called()
        mock_client.map_ids.assert_awaited_once_with(
            from_db="ChEMBL",
            to_db="UniProtKB",
            ids=["CHEMBL1"],
        )

    @pytest.mark.asyncio
    async def test_fetch_reads_from_reader_when_no_seed_or_filter(
        self,
        mock_client: MagicMock,
        mock_reader: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test source reader is used in standalone mode."""
        await asyncio.sleep(0)
        ds = IDMappingDataSource(
            idmapping_client=mock_client,
            id_source_reader=mock_reader,
            input_path="data/input/target.csv",
            logger=mock_logger,
        )

        records = [record async for record in ds.fetch("idmapping")]

        assert len(records) == 3
        assert records[0]["uniprot_accession"] == "P00742"
        assert records[2]["uniprot_accession"] is None
        mock_reader.read_ids.assert_awaited_once_with(
            source_path="data/input/target.csv",
            id_column="target_id",
        )

    @pytest.mark.asyncio
    async def test_fetch_applies_limit(self, data_source: IDMappingDataSource) -> None:
        """Test limit truncates IDs before mapping."""
        await asyncio.sleep(0)
        records = [record async for record in data_source.fetch("idmapping", limit=2)]
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_fetch_applies_offset_before_limit(
        self, data_source: IDMappingDataSource, mock_client: MagicMock
    ) -> None:
        """Offset is applied before limit so later pages do not repeat earlier IDs."""
        await asyncio.sleep(0)
        records = [
            record async for record in data_source.fetch("idmapping", limit=1, offset=1)
        ]
        assert len(records) == 1
        assert records[0]["target_id"] == "CHEMBL205"
        mock_client.map_ids.assert_awaited_once_with(
            from_db="ChEMBL",
            to_db="UniProtKB",
            ids=["CHEMBL205"],
        )

    @pytest.mark.asyncio
    async def test_fetch_logs_warning_for_unexpected_entity_type(
        self,
        data_source: IDMappingDataSource,
        mock_logger: MagicMock,
    ) -> None:
        """Test warning when entity_type is not idmapping."""
        await asyncio.sleep(0)
        _ = [record async for record in data_source.fetch("unexpected")]

        mock_logger.warning.assert_any_call(
            "unexpected_entity_type",
            expected="idmapping",
            received="unexpected",
        )

    @pytest.mark.asyncio
    async def test_fetch_returns_empty_when_no_ids(
        self,
        mock_client: MagicMock,
        mock_reader: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test no map request when source has no IDs."""
        await asyncio.sleep(0)
        mock_reader.read_ids = AsyncMock(return_value=[])
        ds = IDMappingDataSource(
            idmapping_client=mock_client,
            id_source_reader=mock_reader,
            input_path="data/input/target.csv",
            logger=mock_logger,
        )

        records = [record async for record in ds.fetch("idmapping")]

        assert records == []
        mock_client.map_ids.assert_not_called()
        mock_logger.warning.assert_any_call(
            "no_ids_to_map", input_path="data/input/target.csv"
        )

    @pytest.mark.asyncio
    async def test_fetch_propagates_reader_errors(
        self,
        mock_client: MagicMock,
        mock_reader: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test FileNotFoundError from reader is propagated."""
        await asyncio.sleep(0)
        mock_reader.read_ids = AsyncMock(side_effect=FileNotFoundError("missing"))
        ds = IDMappingDataSource(
            idmapping_client=mock_client,
            id_source_reader=mock_reader,
            input_path="data/input/missing.csv",
            logger=mock_logger,
        )

        with pytest.raises(FileNotFoundError, match="missing"):
            _ = [record async for record in ds.fetch("idmapping")]


@pytest.mark.unit
class TestIDMappingDataSourceHealthCheck:
    """Tests for health_check behavior."""

    @pytest.mark.asyncio
    async def test_source_health_check__health_check_healthy__37c42c53(
        self, data_source: IDMappingDataSource
    ) -> None:
        """Test healthy status when source exists and API is healthy."""
        status = await data_source.health_check()
        assert status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_when_source_missing(
        self,
        mock_client: MagicMock,
        mock_reader: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test unhealthy status when input source is missing."""
        mock_reader.source_exists = AsyncMock(return_value=False)
        ds = IDMappingDataSource(
            idmapping_client=mock_client,
            id_source_reader=mock_reader,
            input_path="data/input/missing.csv",
            logger=mock_logger,
        )

        status = await ds.health_check()

        assert status == HealthStatus.UNHEALTHY
        mock_client.health_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_health_check_skips_source_check_when_seed_ids_present(
        self,
        mock_client: MagicMock,
        mock_reader: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test source existence check is skipped in composite mode."""
        ds = IDMappingDataSource(
            idmapping_client=mock_client,
            id_source_reader=mock_reader,
            input_path="data/input/target.csv",
            logger=mock_logger,
            seed_ids=["CHEMBL1"],
        )

        status = await ds.health_check()

        assert status == HealthStatus.HEALTHY
        mock_reader.source_exists.assert_not_called()
        mock_client.health_check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_health_check_returns_api_status(
        self,
        mock_client: MagicMock,
        mock_reader: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test non-healthy API status is propagated."""
        mock_client.health_check = AsyncMock(return_value=HealthStatus.DEGRADED)
        ds = IDMappingDataSource(
            idmapping_client=mock_client,
            id_source_reader=mock_reader,
            input_path="data/input/target.csv",
            logger=mock_logger,
        )

        status = await ds.health_check()

        assert status == HealthStatus.DEGRADED
