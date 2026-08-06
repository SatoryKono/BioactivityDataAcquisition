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
"""Unit tests for ConfigService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.services.ops.config_service import (
    ConfigService,
    PipelineInfo,
    SettingsInfo,
)
from bioetl.domain.config import PipelineConfig, TableConfig


def _make_mock_settings() -> MagicMock:
    """Create a mock Settings object with model_dump()."""
    settings = MagicMock()
    settings.env = "dev"
    settings.data_dir = "/data"
    settings.bronze_path = "/data/bronze"
    settings.silver_path = "/data/silver"
    settings.gold_path = "/data/gold"
    settings.checkpoint_path = "/data/checkpoint"
    settings.quarantine_path = "/data/quarantine"
    settings.debug = False
    settings.test_mode = True
    settings.metrics_enabled = False
    settings.metrics_port = 9090
    settings.pipeline = MagicMock(batch_size=500)
    settings.model_dump.return_value = {
        "env": "dev",
        "data_dir": "/data",
        "debug": False,
        "test_mode": True,
        "metrics_enabled": False,
        "metrics_port": 9090,
        "pipeline": {"batch_size": 500},
        "extra_key": "extra_value",
    }
    return settings


def _make_mock_yaml_config(
    provider: str = "chembl",
    entity_type: str = "activity",
    silver_table: str = "chembl_activity_silver",
    gold_table: str | None = "chembl_activity_gold",
) -> MagicMock:
    """Create a mock PipelineYamlConfig object."""
    config = MagicMock()
    config.provider = provider
    config.entity_type = entity_type
    config.silver_table = silver_table
    config.gold_table = gold_table
    config.model_dump.return_value = {
        "provider": provider,
        "entity_type": entity_type,
        "silver_table": silver_table,
        "gold_table": gold_table,
    }
    return config


@pytest.fixture
def mock_logger() -> MagicMock:
    return MagicMock()


@pytest.fixture
def config_service(mock_logger: MagicMock) -> ConfigService:
    """Create ConfigService with mock dependencies."""
    return ConfigService(
        logger=mock_logger,
        _settings_loader=MagicMock(return_value=_make_mock_settings()),
        _pipeline_config_loader=MagicMock(return_value=_make_mock_yaml_config()),
        _domain_config_mapper=MagicMock(
            return_value=PipelineConfig(
                pipeline_name="chembl_activity",
                provider="chembl",
                entity_type="activity",
                table=TableConfig(
                    primary_keys=("activity_id",),
                    silver_table="chembl_activity_silver",
                ),
            )
        ),
        _registry_accessor=MagicMock(
            return_value=MagicMock(
                list_pipelines=MagicMock(
                    return_value=["chembl_activity", "chembl_assay"]
                )
            )
        ),
    )


@pytest.mark.unit
class TestConfigServiceGetSettings:
    """Tests for get_settings method."""

    def test_returns_settings_info(self, config_service: ConfigService) -> None:
        result = config_service.get_settings()

        assert isinstance(result, SettingsInfo)
        assert result.env == "dev"
        assert result.data_dir == "/data"
        assert result.bronze_path == "/data/bronze"
        assert result.silver_path == "/data/silver"
        assert result.gold_path == "/data/gold"
        assert result.checkpoint_path == "/data/checkpoint"
        assert result.quarantine_path == "/data/quarantine"
        assert result.debug is False
        assert result.test_mode is True
        assert result.metrics_enabled is False
        assert result.metrics_port == 9090
        assert result.batch_size == 500

    def test_additional_fields_exclude_standard_keys(
        self, config_service: ConfigService
    ) -> None:
        result = config_service.get_settings()

        # 'env', 'data_dir', 'debug', 'test_mode', 'metrics_enabled',
        # 'metrics_port', 'pipeline' should be excluded from additional
        assert "env" not in result.additional
        assert "pipeline" not in result.additional
        assert result.additional["extra_key"] == "extra_value"

    def test_calls_settings_loader(self, config_service: ConfigService) -> None:
        config_service.get_settings()
        config_service._settings_loader.assert_called_once()

    def test_logs_debug_and_info(
        self, config_service: ConfigService, mock_logger: MagicMock
    ) -> None:
        config_service.get_settings()
        mock_logger.debug.assert_called_once()
        mock_logger.info.assert_called_once()


@pytest.mark.unit
class TestConfigServiceLoadPipelineConfig:
    """Tests for load_pipeline_config method."""

    def test_returns_pipeline_config(self, config_service: ConfigService) -> None:
        result = config_service.load_pipeline_config("chembl_activity")

        assert isinstance(result, PipelineConfig)
        assert result.provider == "chembl"
        assert result.entity_type == "activity"

    def test_calls_loader_and_mapper(self, config_service: ConfigService) -> None:
        config_service.load_pipeline_config("chembl_activity")

        config_service._pipeline_config_loader.assert_called_once_with(
            "chembl_activity"
        )
        config_service._domain_config_mapper.assert_called_once()

    def test_logs_pipeline_name(
        self, config_service: ConfigService, mock_logger: MagicMock
    ) -> None:
        config_service.load_pipeline_config("chembl_activity")
        mock_logger.info.assert_called_once()


@pytest.mark.unit
class TestConfigServiceGetPipelineYamlConfig:
    """Tests for get_pipeline_yaml_config method."""

    def test_returns_dict_from_model_dump(self, config_service: ConfigService) -> None:
        result = config_service.get_pipeline_yaml_config("chembl_activity")

        assert isinstance(result, dict)
        assert result["provider"] == "chembl"
        assert result["entity_type"] == "activity"

    def test_fallback_to_dict_when_no_model_dump(self, mock_logger: MagicMock) -> None:
        """When yaml_config has no model_dump, falls back to dict()."""
        yaml_obj = {"provider": "pubchem", "entity_type": "compound"}
        service = ConfigService(
            logger=mock_logger,
            _settings_loader=MagicMock(),
            _pipeline_config_loader=MagicMock(return_value=yaml_obj),
            _domain_config_mapper=MagicMock(),
            _registry_accessor=MagicMock(),
        )

        result = service.get_pipeline_yaml_config("pubchem_compound")

        assert result == {"provider": "pubchem", "entity_type": "compound"}


@pytest.mark.unit
class TestConfigServiceValidatePipelineConfig:
    """Tests for validate_pipeline_config method."""

    def test_returns_pipeline_info(self, config_service: ConfigService) -> None:
        result = config_service.validate_pipeline_config("chembl_activity")

        assert isinstance(result, PipelineInfo)
        assert result.name == "chembl_activity"
        assert result.provider == "chembl"
        assert result.entity_type == "activity"
        assert result.silver_table == "chembl_activity_silver"
        assert result.gold_table == "chembl_activity_gold"

    def test_pipeline_info_with_no_gold_table(self, mock_logger: MagicMock) -> None:
        yaml_config = _make_mock_yaml_config(gold_table=None)
        service = ConfigService(
            logger=mock_logger,
            _settings_loader=MagicMock(),
            _pipeline_config_loader=MagicMock(return_value=yaml_config),
            _domain_config_mapper=MagicMock(),
            _registry_accessor=MagicMock(),
        )

        result = service.validate_pipeline_config("chembl_target")

        assert result.gold_table is None


@pytest.mark.unit
class TestConfigServiceListPipelines:
    """Tests for list_pipelines method."""

    def test_returns_pipeline_names(self, config_service: ConfigService) -> None:
        result = config_service.list_pipelines()

        assert result == ["chembl_activity", "chembl_assay"]

    def test_calls_registry_accessor(self, config_service: ConfigService) -> None:
        config_service.list_pipelines()
        config_service._registry_accessor.assert_called_once()
