"""Unit tests for composition/bootstrap/runtime/assembly.py.

Tests pure assembly functions for pipeline bootstrap configuration.
These tests verify the deterministic behavior of configuration assembly
without requiring I/O or DI.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from bioetl.composition.bootstrap.runtime.assembly import (
    ResolvedVacuumSettings as AssemblyVacuumSettings,
    assemble_filter_config,
    assemble_runtime_config,
    assemble_vacuum_settings,
)
from bioetl.domain.context import (
    InputFilterContext,
    PipelineRunContext,
    VacuumSettings,
)
from bioetl.domain.types import RunType
from bioetl.infrastructure.schemas.pipeline_config import (
    InputFilterYamlConfig as YamlInputFilter,
    MaintenanceConfig,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def yaml_maintenance_default() -> MaintenanceConfig:
    """Create default maintenance config from YAML."""
    return MaintenanceConfig(auto_vacuum=False, vacuum_retention_days=7)


@pytest.fixture
def yaml_maintenance_enabled() -> MaintenanceConfig:
    """Create maintenance config with vacuum enabled."""
    return MaintenanceConfig(auto_vacuum=True, vacuum_retention_days=14)


@pytest.fixture
def yaml_filter_disabled() -> YamlInputFilter:
    """Create disabled filter config from YAML."""
    return YamlInputFilter(enabled=False)


@pytest.fixture
def yaml_filter_enabled() -> YamlInputFilter:
    """Create enabled filter config from YAML."""
    return YamlInputFilter(
        enabled=True,
        source_path="/path/to/filter.csv",
        column_name="compound_id",
        filter_field="chembl_id",
    )


@pytest.fixture
def base_context() -> PipelineRunContext:
    """Create base pipeline run context for tests."""
    return PipelineRunContext(
        pipeline_name="test_pipeline",
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
    )


# =============================================================================
# Tests for VacuumSettings
# =============================================================================


@pytest.mark.unit
class TestVacuumSettings:
    """Tests for assembly VacuumSettings dataclass."""

    def test_vacuum_settings_is_frozen(self):
        """Test that VacuumSettings is immutable."""
        settings = AssemblyVacuumSettings(enabled=True, retention_days=7)
        with pytest.raises(AttributeError):
            settings.enabled = False  # type: ignore[misc]

    def test_vacuum_settings_equality(self):
        """Test that VacuumSettings supports equality comparison."""
        s1 = AssemblyVacuumSettings(enabled=True, retention_days=7)
        s2 = AssemblyVacuumSettings(enabled=True, retention_days=7)
        s3 = AssemblyVacuumSettings(enabled=False, retention_days=7)

        assert s1 == s2
        assert s1 != s3


# =============================================================================
# Tests for assemble_vacuum_settings
# =============================================================================


@pytest.mark.unit
class TestAssembleVacuumSettings:
    """Tests for assemble_vacuum_settings function."""

    def test_cli_none_uses_yaml_auto_vacuum_false(
        self, yaml_maintenance_default: MaintenanceConfig
    ):
        """Test that CLI enabled=None uses YAML auto_vacuum=False."""
        cli_vacuum = VacuumSettings(enabled=None, retention_days=7)

        result = assemble_vacuum_settings(
            cli_vacuum=cli_vacuum,
            yaml_maintenance=yaml_maintenance_default,
        )

        assert result.enabled is False
        assert result.retention_days == 7

    def test_cli_none_uses_yaml_auto_vacuum_true(
        self, yaml_maintenance_enabled: MaintenanceConfig
    ):
        """Test that CLI enabled=None uses YAML auto_vacuum=True."""
        cli_vacuum = VacuumSettings(enabled=None, retention_days=3)

        result = assemble_vacuum_settings(
            cli_vacuum=cli_vacuum,
            yaml_maintenance=yaml_maintenance_enabled,
        )

        assert result.enabled is True
        # When CLI doesn't override, use YAML retention days
        assert result.retention_days == 14

    def test_cli_true_overrides_yaml_false(
        self, yaml_maintenance_default: MaintenanceConfig
    ):
        """Test that CLI enabled=True overrides YAML auto_vacuum=False."""
        cli_vacuum = VacuumSettings(enabled=True, retention_days=5)

        result = assemble_vacuum_settings(
            cli_vacuum=cli_vacuum,
            yaml_maintenance=yaml_maintenance_default,
        )

        assert result.enabled is True
        assert result.retention_days == 5

    def test_cli_false_overrides_yaml_true(
        self, yaml_maintenance_enabled: MaintenanceConfig
    ):
        """Test that CLI enabled=False overrides YAML auto_vacuum=True."""
        cli_vacuum = VacuumSettings(enabled=False, retention_days=3)

        result = assemble_vacuum_settings(
            cli_vacuum=cli_vacuum,
            yaml_maintenance=yaml_maintenance_enabled,
        )

        assert result.enabled is False
        assert result.retention_days == 3

    def test_cli_override_uses_cli_retention_days(
        self, yaml_maintenance_enabled: MaintenanceConfig
    ):
        """Test that CLI override uses CLI retention_days value."""
        cli_vacuum = VacuumSettings(enabled=True, retention_days=30)

        result = assemble_vacuum_settings(
            cli_vacuum=cli_vacuum,
            yaml_maintenance=yaml_maintenance_enabled,
        )

        # CLI explicit override -> use CLI retention days
        assert result.retention_days == 30

    def test_returns_vacuum_settings_type(
        self, yaml_maintenance_default: MaintenanceConfig
    ):
        """Test that function returns VacuumSettings type."""
        cli_vacuum = VacuumSettings(enabled=None, retention_days=7)

        result = assemble_vacuum_settings(
            cli_vacuum=cli_vacuum,
            yaml_maintenance=yaml_maintenance_default,
        )

        assert isinstance(result, AssemblyVacuumSettings)


# =============================================================================
# Tests for assemble_runtime_config
# =============================================================================


@pytest.mark.unit
class TestAssembleRuntimeConfig:
    """Tests for assemble_runtime_config function."""

    def test_assembles_basic_config(self):
        """Test that assemble_runtime_config creates basic RuntimeConfig."""
        vacuum = VacuumSettings(enabled=False, retention_days=7)

        result = assemble_runtime_config(
            run_type=RunType.INCREMENTAL,
            resume=False,
            limit=None,
            query=None,
            dry_run=False,
            heartbeat_interval=30,
            vacuum=vacuum,
        )

        assert result.run_type == RunType.INCREMENTAL
        assert result.resume is False
        assert result.limit is None
        assert result.query is None
        assert result.dry_run is False
        assert result.heartbeat_interval == 30
        assert result.vacuum_after_run is False
        assert result.vacuum_retention_days == 7
        assert (
            result.silver_filter_compatibility_mode
            == "structural_only_auto_promote"
        )

    def test_assembles_config_with_limit(self):
        """Test that assemble_runtime_config handles limit parameter."""
        vacuum = VacuumSettings(enabled=False, retention_days=7)

        result = assemble_runtime_config(
            run_type=RunType.BACKFILL,
            resume=True,
            limit=100,
            query="test_query",
            dry_run=True,
            heartbeat_interval=60,
            vacuum=vacuum,
        )

        assert result.run_type == RunType.BACKFILL
        assert result.resume is True
        assert result.limit == 100
        assert result.query == "test_query"
        assert result.dry_run is True
        assert result.heartbeat_interval == 60

    def test_assembles_config_with_vacuum_enabled(self):
        """Test that vacuum settings are properly transferred."""
        vacuum = VacuumSettings(enabled=True, retention_days=14)

        result = assemble_runtime_config(
            run_type=RunType.REBUILD,
            resume=False,
            limit=None,
            query=None,
            dry_run=False,
            heartbeat_interval=30,
            vacuum=vacuum,
        )

        assert result.vacuum_after_run is True
        assert result.vacuum_retention_days == 14

    def test_config_is_immutable(self):
        """Test that returned RuntimeConfig is immutable (frozen)."""
        vacuum = VacuumSettings(enabled=False, retention_days=7)

        result = assemble_runtime_config(
            run_type=RunType.INCREMENTAL,
            resume=False,
            limit=None,
            query=None,
            dry_run=False,
            heartbeat_interval=30,
            vacuum=vacuum,
        )

        with pytest.raises(AttributeError):
            result.limit = 50  # type: ignore[misc]

    def test_all_run_types_supported(self):
        """Test that all RunType values are supported."""
        vacuum = VacuumSettings(enabled=False, retention_days=7)

        for run_type in RunType:
            result = assemble_runtime_config(
                run_type=run_type,
                resume=False,
                limit=None,
                query=None,
                dry_run=False,
                heartbeat_interval=30,
                vacuum=vacuum,
            )
            assert result.run_type == run_type


# =============================================================================
# Tests for assemble_filter_config
# =============================================================================


@pytest.mark.unit
class TestAssembleFilterConfig:
    """Tests for assemble_filter_config function."""

    def test_disabled_yaml_filter_returns_none(
        self, yaml_filter_disabled: YamlInputFilter, base_context: PipelineRunContext
    ):
        """Test that disabled YAML filter returns None."""
        result = assemble_filter_config(
            yaml_filter=yaml_filter_disabled,
            ctx=base_context,
            test_mode=False,
        )

        assert result is None

    def test_enabled_yaml_filter_returns_config(
        self, yaml_filter_enabled: YamlInputFilter, base_context: PipelineRunContext
    ):
        """Test that enabled YAML filter returns InputFilterConfig."""
        result = assemble_filter_config(
            yaml_filter=yaml_filter_enabled,
            ctx=base_context,
            test_mode=False,
        )

        assert result is not None
        assert result.enabled is True
        assert result.source_path == "/path/to/filter.csv"
        assert result.column_name == "compound_id"
        assert result.filter_field == "chembl_id"

    def test_test_mode_disables_yaml_filter(
        self, yaml_filter_enabled: YamlInputFilter, base_context: PipelineRunContext
    ):
        """Test that test_mode=True disables YAML-based filter."""
        result = assemble_filter_config(
            yaml_filter=yaml_filter_enabled,
            ctx=base_context,
            test_mode=True,
        )

        assert result is None

    def test_cli_filter_overrides_yaml(self, yaml_filter_enabled: YamlInputFilter):
        """Test that CLI input_filter overrides YAML config."""
        ctx = PipelineRunContext(
            pipeline_name="test_pipeline",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            input_filter=InputFilterContext.from_csv(
                source_path="/cli/path/to/filter.csv",
                column_name="cli_column",
                filter_field="cli_field",
            ),
        )

        result = assemble_filter_config(
            yaml_filter=yaml_filter_enabled,
            ctx=ctx,
            test_mode=False,
        )

        assert result is not None
        assert result.source_path == "/cli/path/to/filter.csv"
        assert result.column_name == "cli_column"
        assert result.filter_field == "cli_field"

    def test_ignore_yaml_filter_flag(self, yaml_filter_enabled: YamlInputFilter):
        """Test that ignore_yaml_filter flag disables YAML filter."""
        ctx = PipelineRunContext(
            pipeline_name="test_pipeline",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            ignore_yaml_filter=True,
        )

        result = assemble_filter_config(
            yaml_filter=yaml_filter_enabled,
            ctx=ctx,
            test_mode=False,
        )

        assert result is None

    def test_direct_filter_ids_takes_precedence(
        self, yaml_filter_enabled: YamlInputFilter
    ):
        """Test that direct_filter_ids takes precedence over YAML."""
        ctx = PipelineRunContext(
            pipeline_name="test_pipeline",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            input_filter=InputFilterContext.from_ids(
                filter_ids=("ID1", "ID2", "ID3"),
                filter_field="doi",
            ),
        )

        result = assemble_filter_config(
            yaml_filter=yaml_filter_enabled,
            ctx=ctx,
            test_mode=False,
        )

        assert result is not None
        assert result.direct_filter_ids == ("ID1", "ID2", "ID3")
        assert result.filter_field == "doi"


# =============================================================================
# Integration Tests (assembly functions working together)
# =============================================================================


@pytest.mark.unit
class TestAssemblyIntegration:
    """Integration tests for assembly functions working together."""

    def test_full_assembly_flow_with_defaults(
        self,
        yaml_maintenance_default: MaintenanceConfig,
        yaml_filter_disabled: YamlInputFilter,
        base_context: PipelineRunContext,
    ):
        """Test full assembly flow with default configurations."""
        # Step 1: Assemble vacuum settings
        vacuum = assemble_vacuum_settings(
            cli_vacuum=base_context.vacuum,
            yaml_maintenance=yaml_maintenance_default,
        )
        assert vacuum.enabled is False

        # Step 2: Assemble runtime config
        runtime = assemble_runtime_config(
            run_type=base_context.run_type,
            resume=base_context.resume,
            limit=base_context.limit,
            query=base_context.query,
            dry_run=base_context.dry_run,
            heartbeat_interval=30,
            vacuum=vacuum,
        )
        assert runtime.vacuum_after_run is False

        # Step 3: Assemble filter config
        filter_cfg = assemble_filter_config(
            yaml_filter=yaml_filter_disabled,
            ctx=base_context,
            test_mode=False,
        )
        assert filter_cfg is None

    def test_full_assembly_flow_with_overrides(
        self,
        yaml_maintenance_enabled: MaintenanceConfig,
        yaml_filter_enabled: YamlInputFilter,
    ):
        """Test full assembly flow with CLI overrides."""
        ctx = PipelineRunContext(
            pipeline_name="test_pipeline",
            run_id=uuid4(),
            run_type=RunType.BACKFILL,
            resume=True,
            limit=500,
            vacuum=VacuumSettings(enabled=False, retention_days=3),
            input_filter=InputFilterContext.from_csv(
                source_path="/cli/filter.csv",
                column_name="my_col",
                filter_field="my_field",
            ),
        )

        # Step 1: Vacuum CLI override (False) takes precedence over YAML (True)
        vacuum = assemble_vacuum_settings(
            cli_vacuum=ctx.vacuum,
            yaml_maintenance=yaml_maintenance_enabled,
        )
        assert vacuum.enabled is False
        assert vacuum.retention_days == 3

        # Step 2: Runtime config uses resolved vacuum
        runtime = assemble_runtime_config(
            run_type=ctx.run_type,
            resume=ctx.resume,
            limit=ctx.limit,
            query=ctx.query,
            dry_run=ctx.dry_run,
            heartbeat_interval=45,
            vacuum=vacuum,
        )
        assert runtime.run_type == RunType.BACKFILL
        assert runtime.resume is True
        assert runtime.limit == 500
        assert runtime.vacuum_after_run is False

        # Step 3: Filter CLI override takes precedence
        filter_cfg = assemble_filter_config(
            yaml_filter=yaml_filter_enabled,
            ctx=ctx,
            test_mode=False,
        )
        assert filter_cfg is not None
        assert filter_cfg.source_path == "/cli/filter.csv"
