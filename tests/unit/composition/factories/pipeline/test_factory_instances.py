"""Tests for concrete pipeline factory instances registered in composition."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import ANY, MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.composition.factories.pipeline.factory_method_helpers import (
    build_create_pipeline_with_services_request,
)
from bioetl.domain.types import RunType

_STARTED_AT = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)


def _make_settings() -> MagicMock:
    settings = MagicMock()
    settings.env = "staging"
    settings.strict_error_handling = False
    settings.aws = MagicMock()
    settings.aws.endpoint_url = None
    settings.aws.region = "us-east-1"
    settings.aws.access_key_id = None
    settings.aws.secret_access_key = None
    settings.s3 = MagicMock()
    settings.s3.bucket_bronze = "bronze"
    settings.s3.bucket_silver = "silver"
    settings.s3.bucket_gold = "gold"
    settings.s3.bucket_checkpoints = "checkpoints"
    settings.storage_options = {}
    settings.metrics = None
    settings.pipeline = MagicMock()
    settings.pipeline.heartbeat_interval = 30
    return settings


def _make_logger() -> MagicMock:
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger


def _make_services() -> MagicMock:
    services = MagicMock()
    services.data_source = MagicMock()
    services.storage = MagicMock()
    services.lock = MagicMock()
    services.checkpoint = MagicMock()
    services.quarantine = MagicMock()
    services.metrics = MagicMock()
    return services


def _make_pipeline_config() -> MagicMock:
    config = MagicMock()
    config.source = {"api": {"rate_limit": 10.0}}
    config.dq_overrides.soft_fail_threshold = 0.05
    config.dq_overrides.hard_fail_threshold = 0.20
    config.dq_overrides.invalid_record_policy = "quarantine"
    config.dq_overrides.report.format = "json"
    config.dq_overrides.report.output_path = "reports/dq"
    config.dq_overrides.report.enabled = True
    config.dq_overrides.field_validations = []
    config.dq_overrides.cross_field_validations = []
    config.dq_overrides.conditional_validations = []
    return config


@pytest.mark.unit
class TestChemblActivityFactory:
    """Concrete registry instances should behave like GenericPipelineFactory."""

    @pytest.fixture(autouse=True)
    def _restore_factory_state(self) -> Generator[None, None, None]:
        from bioetl.composition.factories.pipeline.registry import (
            chembl_activity_factory,
        )

        original_creator = chembl_activity_factory._create_data_source
        original_class = chembl_activity_factory.pipeline_class
        yield
        chembl_activity_factory._create_data_source = original_creator
        chembl_activity_factory.pipeline_class = original_class

    @patch("bioetl.composition.factories.services.bundle.BaseServicesFactory")
    @patch("bioetl.composition.factories.services.bundle.load_pipeline_config")
    def test_build_services_creates_data_source(
        self,
        mock_load_config: MagicMock,
        mock_base_services: MagicMock,
    ) -> None:
        from bioetl.composition.factories.pipeline.registry import (
            chembl_activity_factory,
        )

        mock_load_config.return_value = _make_pipeline_config()
        mock_base_services.create_common_services.return_value = _make_services()
        chembl_activity_factory._create_data_source = MagicMock(
            return_value=MagicMock()
        )

        services = chembl_activity_factory.build_services(
            settings=_make_settings(),
            logger=_make_logger(),
        )

        assert services is not None
        chembl_activity_factory._create_data_source.assert_called_once()

    @patch("bioetl.composition.factories.services.bundle.BaseServicesFactory")
    @patch("bioetl.composition.factories.services.bundle.load_pipeline_config")
    def test_build_services_calls_base_services_factory(
        self,
        mock_load_config: MagicMock,
        mock_base_services: MagicMock,
    ) -> None:
        from bioetl.composition.factories.pipeline.registry import (
            chembl_activity_factory,
        )

        mock_load_config.return_value = _make_pipeline_config()
        mock_base_services.create_common_services.return_value = _make_services()
        chembl_activity_factory._create_data_source = MagicMock(
            return_value=MagicMock()
        )

        chembl_activity_factory.build_services(
            settings=_make_settings(),
            logger=_make_logger(),
        )

        mock_base_services.create_common_services.assert_called_once()

    @patch("bioetl.composition.factories.services.bundle.BaseServicesFactory")
    @patch("bioetl.composition.factories.services.bundle.load_pipeline_config")
    def test_build_services_uses_provided_config(
        self,
        mock_load_config: MagicMock,
        mock_base_services: MagicMock,
    ) -> None:
        from bioetl.composition.factories.pipeline.registry import (
            chembl_activity_factory,
        )

        mock_base_services.create_common_services.return_value = _make_services()
        chembl_activity_factory._create_data_source = MagicMock(
            return_value=MagicMock()
        )

        chembl_activity_factory.build_services(
            settings=_make_settings(),
            logger=_make_logger(),
            config=_make_pipeline_config(),
        )

        mock_load_config.assert_not_called()

    @patch("bioetl.composition.factories.services.bundle.compute_config_hash")
    @patch("bioetl.composition.factories.services.bundle.yaml_config_to_domain")
    @patch("bioetl.composition.factories.services.bundle.load_pipeline_config")
    @patch("bioetl.composition.factories.services.bundle.BaseServicesFactory")
    def test_create_with_services(
        self,
        mock_base_services: MagicMock,
        mock_load_config: MagicMock,
        mock_yaml_to_domain: MagicMock,
        mock_compute_hash: MagicMock,
    ) -> None:
        from bioetl.composition.factories.pipeline.registry import (
            chembl_activity_factory,
        )
        from bioetl.domain.config import RuntimeConfig

        mock_services = _make_services()
        mock_settings = _make_settings()
        mock_logger = _make_logger()
        mock_pipeline_config = _make_pipeline_config()

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services
        from bioetl.domain.types.dq_contracts import DQDisposition

        mock_domain_config = MagicMock()
        mock_domain_config.dq = MagicMock()
        mock_domain_config.dq.default_disposition_policy = DQDisposition.WARN
        mock_domain_config.dq.disposition_overrides = {}
        mock_domain_config.dq.strictness_mode = "moderate"
        mock_domain_config.dq.contract_ref = None
        mock_domain_config.dq.contract_version = None
        mock_domain_config.dq.rule_bundle_version = None
        mock_domain_config.dq.soft_fail_threshold = 0.05
        mock_domain_config.dq.hard_fail_threshold = 0.20
        mock_domain_config.dq.strict_validation = False
        mock_yaml_to_domain.return_value = mock_domain_config
        mock_compute_hash.return_value = "mock_config_hash_12345"
        chembl_activity_factory._create_data_source = MagicMock(
            return_value=MagicMock()
        )

        mock_pipeline_class = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_class.create.return_value = mock_pipeline
        chembl_activity_factory.pipeline_class = mock_pipeline_class

        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
        run_id = uuid4()

        result = chembl_activity_factory.create_with_services(
            build_create_pipeline_with_services_request(
                run_id=run_id,
                runtime=runtime,
                started_at=_STARTED_AT,
                settings=mock_settings,
                logger=mock_logger,
            )
        )

        mock_pipeline_class.create.assert_called_once_with(
            run_id=run_id,
            runtime=runtime,
            services=mock_services,
            config=mock_domain_config,
            shutdown_signal=ANY,
            started_at=_STARTED_AT,
            transformer=ANY,
        )
        assert result is mock_pipeline
