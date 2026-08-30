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
"""Unit tests for public composition resource-management entrypoints.

Tests the resource management entrypoint functions exposed via
``bioetl.composition.resources_runtime``. Dedicated entrypoint-boundary coverage is
allowed to patch the internal ``bioetl.composition._resource_management`` seam
directly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# Tests for get_quarantine_runtime_service
# =============================================================================


@pytest.mark.unit
class TestGetQuarantineRuntimeService:
    """Tests for get_quarantine_runtime_service function."""

    def test_calls_ensure_registrations_and_bootstrap(self) -> None:
        """Test that get_quarantine_runtime_service calls _ensure_registrations and bootstrap."""
        mock_runtime_service = MagicMock()

        with (
            patch(
                "bioetl.composition._resource_management._ensure_registrations"
            ) as mock_ensure,
            patch(
                "bioetl.composition._resource_management.bootstrap_quarantine_runtime_service",
                return_value=mock_runtime_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.resources_runtime import (
                get_quarantine_runtime_service,
            )

            result = get_quarantine_runtime_service("chembl_activity")

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once_with("chembl_activity")
        assert result is mock_runtime_service

    def test_returns_bootstrap_result(self) -> None:
        """Test that the return value is exactly what bootstrap returns."""
        expected = MagicMock(name="QuarantineRuntimeServiceMock")

        with (
            patch("bioetl.composition._resource_management._ensure_registrations"),
            patch(
                "bioetl.composition._resource_management.bootstrap_quarantine_runtime_service",
                return_value=expected,
            ),
        ):
            from bioetl.composition.resources_runtime import (
                get_quarantine_runtime_service,
            )

            result = get_quarantine_runtime_service("any_pipeline")

        assert result is expected

    def test_passes_pipeline_name_to_bootstrap(self) -> None:
        """Test that pipeline name is forwarded to bootstrap function."""
        with (
            patch("bioetl.composition._resource_management._ensure_registrations"),
            patch(
                "bioetl.composition._resource_management.bootstrap_quarantine_runtime_service"
            ) as mock_bootstrap,
        ):
            from bioetl.composition.resources_runtime import (
                get_quarantine_runtime_service,
            )

            get_quarantine_runtime_service("pubmed_publication")

        mock_bootstrap.assert_called_once_with("pubmed_publication")


# =============================================================================
# Tests for get_checkpoint_runtime_service
# =============================================================================


@pytest.mark.unit
class TestGetCheckpointRuntimeService:
    """Tests for get_checkpoint_runtime_service function."""

    def test_runtime_service__and_bootstrap__0792af84(self) -> None:
        """Test that get_checkpoint_runtime_service calls _ensure_registrations and bootstrap."""
        mock_runtime_service = MagicMock()

        with (
            patch(
                "bioetl.composition._resource_management._ensure_registrations"
            ) as mock_ensure,
            patch(
                "bioetl.composition._resource_management.bootstrap_checkpoint_runtime_service",
                return_value=mock_runtime_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.resources_runtime import (
                get_checkpoint_runtime_service,
            )

            result = get_checkpoint_runtime_service("chembl_activity")

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once_with("chembl_activity")
        assert result is mock_runtime_service

    def test_runtime_service__name_to_bootstrap__872020d5(self) -> None:
        """Test that pipeline name is forwarded to bootstrap function."""
        with (
            patch("bioetl.composition._resource_management._ensure_registrations"),
            patch(
                "bioetl.composition._resource_management.bootstrap_checkpoint_runtime_service"
            ) as mock_bootstrap,
        ):
            from bioetl.composition.resources_runtime import (
                get_checkpoint_runtime_service,
            )

            get_checkpoint_runtime_service("uniprot_protein")

        mock_bootstrap.assert_called_once_with("uniprot_protein")


# =============================================================================
# Tests for get_lifecycle_service
# =============================================================================


@pytest.mark.unit
class TestGetLifecycleService:
    """Tests for get_lifecycle_service function."""

    def test_get_lifecycle_service__and_bootstrap__736ed387(self) -> None:
        """Test that get_lifecycle_service calls _ensure_registrations and bootstrap."""
        mock_service = MagicMock()

        with (
            patch(
                "bioetl.composition._resource_management._ensure_registrations"
            ) as mock_ensure,
            patch(
                "bioetl.composition._resource_management.bootstrap_lifecycle_service",
                return_value=mock_service,
            ) as mock_bootstrap,
        ):
            from bioetl.composition.resources_runtime import get_lifecycle_service

            result = get_lifecycle_service()

        mock_ensure.assert_called_once()
        mock_bootstrap.assert_called_once()
        assert result is mock_service


# =============================================================================
# Tests for vacuum_table (async)
# =============================================================================


@pytest.mark.unit
class TestVacuumTable:
    """Tests for vacuum_table async function."""

    @pytest.mark.asyncio
    async def test_vacuum_table_calls_service_vacuum(self) -> None:
        """Test that vacuum_table delegates to lifecycle service.vacuum."""
        from bioetl.composition.resources_runtime import VacuumOptions

        mock_service = MagicMock()
        mock_service.vacuum = AsyncMock(return_value=42)

        with (
            patch(
                "bioetl.composition._resource_management.get_lifecycle_service",
                return_value=mock_service,
            ),
        ):
            from bioetl.composition.resources_runtime import vacuum_table

            options = VacuumOptions(retention_days=30, dry_run=True)
            result = await vacuum_table("chembl.activity", options)

        mock_service.vacuum.assert_called_once_with(
            table="chembl.activity",
            retention_days=30,
            dry_run=True,
        )
        assert result == 42

    @pytest.mark.asyncio
    async def test_vacuum_table_returns_file_count(self) -> None:
        """Test that vacuum_table returns file count from service."""
        from bioetl.composition.resources_runtime import VacuumOptions

        mock_service = MagicMock()
        mock_service.vacuum = AsyncMock(return_value=7)

        with (
            patch(
                "bioetl.composition._resource_management.get_lifecycle_service",
                return_value=mock_service,
            ),
        ):
            from bioetl.composition.resources_runtime import vacuum_table

            options = VacuumOptions(retention_days=7, dry_run=False)
            result = await vacuum_table("pubchem.compound", options)

        assert result == 7

    @pytest.mark.asyncio
    async def test_vacuum_table_dry_run_mode(self) -> None:
        """Test that vacuum_table respects dry_run option."""
        from bioetl.composition.resources_runtime import VacuumOptions

        mock_service = MagicMock()
        mock_service.vacuum = AsyncMock(return_value=0)

        with (
            patch(
                "bioetl.composition._resource_management.get_lifecycle_service",
                return_value=mock_service,
            ),
        ):
            from bioetl.composition.resources_runtime import vacuum_table

            options = VacuumOptions(retention_days=7, dry_run=True)
            await vacuum_table("some.table", options)

        call_kwargs = mock_service.vacuum.call_args.kwargs
        assert call_kwargs["dry_run"] is True


# =============================================================================
# Tests for archive_table (async)
# =============================================================================


@pytest.mark.unit
class TestArchiveTable:
    """Tests for archive_table async function."""

    @pytest.mark.asyncio
    async def test_archive_table_calls_service_archive(self) -> None:
        """Test that archive_table delegates to lifecycle service.archive."""
        from bioetl.composition.resources_runtime import ArchiveOptions

        mock_service = MagicMock()
        mock_service.archive = AsyncMock(return_value=10)

        with (
            patch(
                "bioetl.composition._resource_management.get_lifecycle_service",
                return_value=mock_service,
            ),
        ):
            from bioetl.composition.resources_runtime import archive_table

            options = ArchiveOptions(target_path="/archive/path", remove_source=False)
            result = await archive_table("chembl.activity", options)

        mock_service.archive.assert_called_once_with(
            table="chembl.activity",
            target_path="/archive/path",
            remove_source=False,
        )
        assert result == 10

    @pytest.mark.asyncio
    async def test_archive_table_with_remove_source(self) -> None:
        """Test that archive_table passes remove_source=True correctly."""
        from bioetl.composition.resources_runtime import ArchiveOptions

        mock_service = MagicMock()
        mock_service.archive = AsyncMock(return_value=5)

        with (
            patch(
                "bioetl.composition._resource_management.get_lifecycle_service",
                return_value=mock_service,
            ),
        ):
            from bioetl.composition.resources_runtime import archive_table

            options = ArchiveOptions(target_path="/cold/storage", remove_source=True)
            await archive_table("old.table", options)

        call_kwargs = mock_service.archive.call_args.kwargs
        assert call_kwargs["remove_source"] is True


# =============================================================================
# Tests for preview_cleanup (async)
# =============================================================================


@pytest.mark.unit
class TestPreviewCleanup:
    """Tests for preview_cleanup async function."""

    @pytest.mark.asyncio
    async def test_preview_cleanup_calls_bootstrap_and_service(self) -> None:
        """Test that preview_cleanup loads config and calls cleanup service."""
        mock_preview = MagicMock()
        mock_preview.total_files = 42

        mock_pipeline_cfg = MagicMock()
        mock_pipeline_cfg.silver_table = None
        mock_pipeline_cfg.gold_table = None
        mock_pipeline_cfg.provider = "chembl"
        mock_pipeline_cfg.entity_type = "activity"

        mock_cleanup_service = MagicMock()
        mock_cleanup_service.preview = AsyncMock(return_value=mock_preview)

        with (
            patch("bioetl.composition._resource_management._ensure_registrations"),
            patch(
                "bioetl.composition._resource_management.load_pipeline_config",
                return_value=mock_pipeline_cfg,
            ),
            patch(
                "bioetl.composition._resource_management.bootstrap_cleanup_service",
                return_value=mock_cleanup_service,
            ),
        ):
            from bioetl.composition.resources_runtime import preview_cleanup

            result = await preview_cleanup("chembl_activity")

        mock_cleanup_service.preview.assert_called_once()
        assert result is mock_preview

    @pytest.mark.asyncio
    async def test_preview_cleanup_uses_configured_silver_table(self) -> None:
        """Test that preview_cleanup uses explicit silver_table from config."""
        mock_preview = MagicMock()

        mock_pipeline_cfg = MagicMock()
        mock_pipeline_cfg.silver_table = "chembl.activity_silver"
        mock_pipeline_cfg.gold_table = "chembl.activity_gold"

        mock_cleanup_service = MagicMock()
        mock_cleanup_service.preview = AsyncMock(return_value=mock_preview)

        with (
            patch("bioetl.composition._resource_management._ensure_registrations"),
            patch(
                "bioetl.composition._resource_management.load_pipeline_config",
                return_value=mock_pipeline_cfg,
            ),
            patch(
                "bioetl.composition._resource_management.bootstrap_cleanup_service",
                return_value=mock_cleanup_service,
            ),
        ):
            from bioetl.composition.resources_runtime import preview_cleanup

            await preview_cleanup("chembl_activity")

        call_kwargs = mock_cleanup_service.preview.call_args.kwargs
        assert call_kwargs["silver_table"] == "chembl.activity_silver"
        assert call_kwargs["gold_table"] == "chembl.activity_gold"

    @pytest.mark.asyncio
    async def test_preview_cleanup_derives_table_names_when_none(self) -> None:
        """Test that preview_cleanup derives table names from provider+entity when None."""
        mock_preview = MagicMock()

        mock_pipeline_cfg = MagicMock()
        mock_pipeline_cfg.silver_table = None
        mock_pipeline_cfg.gold_table = None
        mock_pipeline_cfg.provider = "pubchem"
        mock_pipeline_cfg.entity_type = "compound"

        mock_cleanup_service = MagicMock()
        mock_cleanup_service.preview = AsyncMock(return_value=mock_preview)

        with (
            patch("bioetl.composition._resource_management._ensure_registrations"),
            patch(
                "bioetl.composition._resource_management.load_pipeline_config",
                return_value=mock_pipeline_cfg,
            ),
            patch(
                "bioetl.composition._resource_management.bootstrap_cleanup_service",
                return_value=mock_cleanup_service,
            ),
        ):
            from bioetl.composition.resources_runtime import preview_cleanup

            await preview_cleanup("pubchem_compound")

        call_kwargs = mock_cleanup_service.preview.call_args.kwargs
        assert call_kwargs["silver_table"] == "pubchem.compound"
        assert call_kwargs["gold_table"] == "pubchem.compound"


# =============================================================================
# Tests for inspect_quarantine (async)
# =============================================================================


@pytest.mark.unit
class TestInspectQuarantine:
    """Tests for inspect_quarantine async function."""

    @pytest.mark.asyncio
    async def test_inspect_quarantine_calls_runtime_service_inspect(self) -> None:
        """Test that inspect_quarantine calls runtime_service.inspect with limit."""
        mock_records = [{"error_code": "DQ_MISSING_FIELD", "id": "1"}]

        mock_runtime_service = MagicMock()
        mock_runtime_service.inspect = AsyncMock(return_value=mock_records)

        with (
            patch(
                "bioetl.composition._resource_management.get_quarantine_runtime_service",
                return_value=mock_runtime_service,
            ),
        ):
            from bioetl.composition.resources_runtime import inspect_quarantine

            result = await inspect_quarantine("chembl_activity", limit=50)

        mock_runtime_service.inspect.assert_called_once_with(limit=50)
        assert result == mock_records

    @pytest.mark.asyncio
    async def test_inspect_quarantine_default_limit(self) -> None:
        """Test that inspect_quarantine uses default limit of 100."""
        mock_runtime_service = MagicMock()
        mock_runtime_service.inspect = AsyncMock(return_value=[])

        with (
            patch(
                "bioetl.composition._resource_management.get_quarantine_runtime_service",
                return_value=mock_runtime_service,
            ),
        ):
            from bioetl.composition.resources_runtime import inspect_quarantine

            await inspect_quarantine("chembl_activity")

        mock_runtime_service.inspect.assert_called_once_with(limit=100)


# =============================================================================
# Tests for list_checkpoints (async)
# =============================================================================


@pytest.mark.unit
class TestListCheckpoints:
    """Tests for list_checkpoints async function."""

    @pytest.mark.asyncio
    async def test_list_checkpoints_calls_runtime_service_list_all(self) -> None:
        """Test that list_checkpoints calls runtime_service.list_all."""
        mock_checkpoints = ["checkpoint_2024_01_15", "checkpoint_2024_01_16"]

        mock_runtime_service = MagicMock()
        mock_runtime_service.list_all = AsyncMock(return_value=mock_checkpoints)

        with (
            patch(
                "bioetl.composition._resource_management.get_checkpoint_runtime_service",
                return_value=mock_runtime_service,
            ),
        ):
            from bioetl.composition.resources_runtime import list_checkpoints

            result = await list_checkpoints("chembl_activity")

        mock_runtime_service.list_all.assert_called_once()
        assert result == mock_checkpoints

    @pytest.mark.asyncio
    async def test_list_checkpoints_empty_list(self) -> None:
        """Test that list_checkpoints returns empty list when no checkpoints."""
        mock_runtime_service = MagicMock()
        mock_runtime_service.list_all = AsyncMock(return_value=[])

        with (
            patch(
                "bioetl.composition._resource_management.get_checkpoint_runtime_service",
                return_value=mock_runtime_service,
            ),
        ):
            from bioetl.composition.resources_runtime import list_checkpoints

            result = await list_checkpoints("any_pipeline")

        assert result == []


@pytest.mark.unit
class TestResourceBootstrapLazyImports:
    """#9793: exercise lazy import wrappers instead of patching them away."""

    def test_bootstrap_quarantine_runtime_service_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from bioetl.composition.bootstrap.cli import checkpoint as checkpoint_bootstrap

        monkeypatch.setattr(
            checkpoint_bootstrap,
            "bootstrap_quarantine_runtime_service",
            lambda pipeline: ("quarantine", pipeline),
        )
        from bioetl.composition._resource_management import (
            bootstrap_quarantine_runtime_service,
        )

        assert bootstrap_quarantine_runtime_service("chembl_activity") == (
            "quarantine",
            "chembl_activity",
        )

    def test_bootstrap_checkpoint_runtime_service_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from bioetl.composition.bootstrap.cli import checkpoint as checkpoint_bootstrap

        monkeypatch.setattr(
            checkpoint_bootstrap,
            "bootstrap_checkpoint_runtime_service",
            lambda pipeline: ("checkpoint", pipeline),
        )
        from bioetl.composition._resource_management import (
            bootstrap_checkpoint_runtime_service,
        )

        assert bootstrap_checkpoint_runtime_service("chembl_activity") == (
            "checkpoint",
            "chembl_activity",
        )

    def test_bootstrap_lifecycle_and_cleanup_delegate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from bioetl.composition.bootstrap.cli import storage as storage_bootstrap

        monkeypatch.setattr(
            storage_bootstrap,
            "bootstrap_lifecycle_service",
            lambda: "lifecycle",
        )
        monkeypatch.setattr(
            storage_bootstrap,
            "bootstrap_cleanup_service",
            lambda: "cleanup",
        )
        from bioetl.composition._resource_management import (
            bootstrap_cleanup_service,
            bootstrap_lifecycle_service,
        )

        assert bootstrap_lifecycle_service() == "lifecycle"
        assert bootstrap_cleanup_service() == "cleanup"

    def test_load_pipeline_config_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "bioetl.infrastructure.config.pipeline_config_api.load_pipeline_config",
            lambda pipeline: {"name": pipeline},
        )
        from bioetl.composition._resource_management import load_pipeline_config

        assert load_pipeline_config("chembl_activity") == {"name": "chembl_activity"}
