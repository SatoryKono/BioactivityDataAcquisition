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
"""Tests for VacuumService.

Tests the batch vacuum operations on Delta tables.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.vacuum_service import (
    TableVacuumResult,
    VacuumAllResult,
    VacuumService,
)


@pytest.mark.unit
class TestTableVacuumResult:
    """Test TableVacuumResult dataclass."""

    def test_success_property_when_no_error(self) -> None:
        """Test success property returns True when no error."""
        result = TableVacuumResult(
            table_name="test_table",
            layer="silver",
            files_removed=5,
            error=None,
        )
        assert result.success is True

    def test_success_property_when_error(self) -> None:
        """Test success property returns False when error present."""
        result = TableVacuumResult(
            table_name="test_table",
            layer="silver",
            files_removed=0,
            error="Something went wrong",
        )
        assert result.success is False

    def test_immutability(self) -> None:
        """Test that result is frozen/immutable."""
        result = TableVacuumResult(
            table_name="test",
            layer="silver",
            files_removed=1,
        )
        with pytest.raises(AttributeError):
            result.files_removed = 10  # type: ignore[misc]


@pytest.mark.unit
class TestVacuumAllResult:
    """Test VacuumAllResult dataclass."""

    def test_total_files_removed_property(self) -> None:
        """Test total_files_removed sums all results."""
        results = (
            TableVacuumResult("t1", "silver", 5, None),
            TableVacuumResult("t2", "gold", 3, None),
            TableVacuumResult("t3", "silver", 2, None),
        )
        vacuum_result = VacuumAllResult(results=results, dry_run=False)
        assert vacuum_result.total_files_removed == 10

    def test_total_files_removed_empty(self) -> None:
        """Test total_files_removed with empty results."""
        vacuum_result = VacuumAllResult(results=(), dry_run=False)
        assert vacuum_result.total_files_removed == 0

    def test_failed_tables_property(self) -> None:
        """Test failed_tables returns tables with errors."""
        results = (
            TableVacuumResult("t1", "silver", 5, None),
            TableVacuumResult("t2", "gold", 0, "Error 1"),
            TableVacuumResult("t3", "silver", 0, "Error 2"),
        )
        vacuum_result = VacuumAllResult(results=results, dry_run=False)

        failed = vacuum_result.failed_tables
        assert len(failed) == 2
        assert "gold/t2" in failed
        assert "silver/t3" in failed

    def test_failed_tables_empty_when_all_succeed(self) -> None:
        """Test failed_tables is empty when all succeed."""
        results = (
            TableVacuumResult("t1", "silver", 5, None),
            TableVacuumResult("t2", "gold", 3, None),
        )
        vacuum_result = VacuumAllResult(results=results, dry_run=False)
        assert vacuum_result.failed_tables == []

    def test_success_count_property(self) -> None:
        """Test success_count counts successful tables."""
        results = (
            TableVacuumResult("t1", "silver", 5, None),
            TableVacuumResult("t2", "gold", 0, "Error"),
            TableVacuumResult("t3", "silver", 3, None),
        )
        vacuum_result = VacuumAllResult(results=results, dry_run=False)
        assert vacuum_result.success_count == 2


@pytest.mark.unit
class TestVacuumService:
    """Test VacuumService class."""

    @pytest.fixture
    def mock_lifecycle(self) -> MagicMock:
        """Create mock MedallionLifecycleService."""
        lifecycle = MagicMock()
        lifecycle.vacuum = AsyncMock(return_value=5)
        return lifecycle

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_collector(self) -> MagicMock:
        """Create mock table collector."""
        return MagicMock(return_value=[("table1", "silver"), ("table2", "gold")])

    @pytest.fixture
    def service(
        self,
        mock_lifecycle: MagicMock,
        mock_logger: MagicMock,
        mock_collector: MagicMock,
    ) -> VacuumService:
        """Create VacuumService instance."""
        return VacuumService(
            lifecycle=mock_lifecycle,
            logger=mock_logger,
            table_collector=mock_collector,
        )

    def test_collect_tables_delegates_to_collector(
        self,
        service: VacuumService,
        mock_collector: MagicMock,
    ) -> None:
        """Test collect_tables delegates to injected collector."""
        result = service.collect_tables(layer="silver")

        mock_collector.assert_called_once_with("silver")
        assert result == [("table1", "silver"), ("table2", "gold")]

    def test_collect_tables_default_layer(
        self,
        service: VacuumService,
        mock_collector: MagicMock,
    ) -> None:
        """Test collect_tables uses 'all' as default layer."""
        service.collect_tables()
        mock_collector.assert_called_once_with("all")


@pytest.mark.unit
@pytest.mark.asyncio
class TestVacuumServiceAsync:
    """Test async methods of VacuumService."""

    @pytest.fixture
    def mock_lifecycle(self) -> MagicMock:
        """Create mock MedallionLifecycleService."""
        lifecycle = MagicMock()
        lifecycle.vacuum = AsyncMock(return_value=5)
        return lifecycle

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_collector(self) -> MagicMock:
        """Create mock table collector."""
        return MagicMock(return_value=[])

    @pytest.fixture
    def service(
        self,
        mock_lifecycle: MagicMock,
        mock_logger: MagicMock,
        mock_collector: MagicMock,
    ) -> VacuumService:
        """Create VacuumService instance."""
        return VacuumService(
            lifecycle=mock_lifecycle,
            logger=mock_logger,
            table_collector=mock_collector,
        )

    async def test_vacuum_table_success(
        self,
        service: VacuumService,
        mock_lifecycle: MagicMock,
    ) -> None:
        """Test vacuum_table on successful vacuum."""
        mock_lifecycle.vacuum = AsyncMock(return_value=10)

        result = await service.vacuum_table(
            table_name="test_table",
            layer="silver",
            retention_days=7,
            dry_run=False,
        )

        assert result.success is True
        assert result.table_name == "test_table"
        assert result.layer == "silver"
        assert result.files_removed == 10
        assert result.error is None

        mock_lifecycle.vacuum.assert_called_once_with(
            table="test_table",
            retention_days=7,
            dry_run=False,
        )

    async def test_vacuum_table_dry_run(
        self,
        service: VacuumService,
        mock_lifecycle: MagicMock,
    ) -> None:
        """Test vacuum_table with dry_run=True."""
        mock_lifecycle.vacuum = AsyncMock(return_value=5)

        result = await service.vacuum_table(
            table_name="test_table",
            layer="gold",
            retention_days=14,
            dry_run=True,
        )

        assert result.success is True
        mock_lifecycle.vacuum.assert_called_once_with(
            table="test_table",
            retention_days=14,
            dry_run=True,
        )

    async def test_vacuum_table_failure(
        self,
        service: VacuumService,
        mock_lifecycle: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test vacuum_table handles exceptions."""
        mock_lifecycle.vacuum = AsyncMock(side_effect=Exception("Vacuum failed"))

        result = await service.vacuum_table(
            table_name="test_table",
            layer="silver",
            retention_days=7,
            dry_run=False,
        )

        assert result.success is False
        assert result.files_removed == 0
        assert "Vacuum failed" in result.error  # type: ignore[operator]

        mock_logger.error.assert_called_once()

    async def test_vacuum_service_async__vacuum_all_success__0038a9bb(
        self,
        service: VacuumService,
        mock_lifecycle: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test vacuum_all with all successful vacuums."""
        mock_lifecycle.vacuum = AsyncMock(return_value=5)

        tables = [("table1", "silver"), ("table2", "gold")]
        result = await service.vacuum_all(
            tables=tables,
            retention_days=7,
            dry_run=False,
        )

        assert isinstance(result, VacuumAllResult)
        assert len(result.results) == 2
        assert result.total_files_removed == 10
        assert result.success_count == 2
        assert result.failed_tables == []
        assert result.dry_run is False

        # Verify logging
        assert mock_logger.info.call_count == 2  # start + complete

    async def test_vacuum_all_partial_failure(
        self,
        service: VacuumService,
        mock_lifecycle: MagicMock,
    ) -> None:
        """Test vacuum_all with some failures."""
        # First call succeeds, second fails
        mock_lifecycle.vacuum = AsyncMock(
            side_effect=[5, Exception("Failed")],
        )

        tables = [("table1", "silver"), ("table2", "gold")]
        result = await service.vacuum_all(
            tables=tables,
            retention_days=7,
            dry_run=False,
        )

        assert result.success_count == 1
        assert len(result.failed_tables) == 1
        assert result.total_files_removed == 5

    async def test_vacuum_all_empty_tables(
        self,
        service: VacuumService,
        mock_lifecycle: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test vacuum_all with empty table list."""
        result = await service.vacuum_all(
            tables=[],
            retention_days=7,
            dry_run=False,
        )

        assert len(result.results) == 0
        assert result.total_files_removed == 0
        assert result.success_count == 0

    async def test_vacuum_all_dry_run(
        self,
        service: VacuumService,
        mock_lifecycle: MagicMock,
    ) -> None:
        """Test vacuum_all in dry run mode."""
        mock_lifecycle.vacuum = AsyncMock(return_value=3)

        tables = [("table1", "silver")]
        result = await service.vacuum_all(
            tables=tables,
            retention_days=7,
            dry_run=True,
        )

        assert result.dry_run is True
        mock_lifecycle.vacuum.assert_called_once_with(
            table="table1",
            retention_days=7,
            dry_run=True,
        )
