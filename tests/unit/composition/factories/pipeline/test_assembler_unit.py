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
"""Unit tests for GenericPipelineFactory assembler."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import ANY, MagicMock, patch

import pytest

from bioetl.composition.factories.pipeline.assembler import (
    GenericPipelineFactory,
    _extract_entity_type,
    assemble_runner,
    create_pipeline_factory,
)
from bioetl.domain.ports.noop import NoOpAudit
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    build_create_pipeline_with_services_request,
)
from bioetl.composition.observability import ObservabilityBundle
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.types import RunType
from bioetl.domain.ports.runtime.runner import PipelineCreateRunnerRequest
from bioetl.infrastructure.config._base import Settings

_STARTED_AT = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)


def _make_runtime(*, strict_gold_validation: bool = False) -> RuntimeConfig:
    return RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        strict_gold_validation=strict_gold_validation,
    )


def _make_settings(**overrides: object) -> Settings:
    defaults = {"env": "dev", "test_mode": False}
    defaults.update(overrides)
    return cast(Settings, SimpleNamespace(**defaults))


def _make_observability() -> ObservabilityBundle:
    return ObservabilityBundle(
        logger=MagicMock(),
        tracer=MagicMock(),
        metrics=MagicMock(),
        audit=NoOpAudit(),
        dq_monitor=MagicMock(),
    )


@pytest.mark.unit
class TestExtractEntityType:
    """Tests for _extract_entity_type helper."""

    def test_extracts_suffix_after_underscore(self) -> None:
        assert _extract_entity_type("chembl_activity") == "activity"

    def test_returns_none_when_no_underscore(self) -> None:
        assert _extract_entity_type("chembl") is None

    def test_handles_multiple_underscores(self) -> None:
        assert _extract_entity_type("chembl_compound_record") == "record"


@pytest.mark.unit
class TestGenericPipelineFactory:
    """Tests for GenericPipelineFactory construction."""

    def test_raises_without_gold_schema(self) -> None:
        """gold_schema is required; raises ValueError when None."""
        with pytest.raises(ValueError, match="gold_schema is required"):
            GenericPipelineFactory(
                pipeline_name="chembl_activity",
                pipeline_class=MagicMock(),
                provider="chembl",
                gold_schema=None,
            )

    def test_stores_attributes(self) -> None:
        """Factory stores all constructor arguments as attributes."""
        gold_schema = MagicMock()
        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            gold_schema=gold_schema,
            silver_schema=MagicMock(),
        )

        assert factory.pipeline_name == "chembl_activity"
        assert factory.provider == "chembl"
        assert factory.gold_schema is gold_schema

    @patch(
        "bioetl.composition.factories.pipeline._assembler_factory.get_data_source_creator"
    )
    def test_resolves_default_data_source_creator(
        self, mock_get_creator: MagicMock
    ) -> None:
        """When no data_source_creator provided, resolves via provider name."""
        mock_creator = MagicMock()
        mock_get_creator.return_value = mock_creator

        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            gold_schema=MagicMock(),
        )

        assert factory._create_data_source is mock_creator
        mock_get_creator.assert_called_once_with(
            "chembl",
            provider_registry=None,
        )

    def test_uses_custom_data_source_creator(self) -> None:
        """Explicit data_source_creator is used instead of resolved one."""
        explicit_data_source_creator = MagicMock()
        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            gold_schema=MagicMock(),
            data_source_creator=explicit_data_source_creator,
        )

        assert factory._create_data_source is explicit_data_source_creator

    def test_create_transformer_delegates(self) -> None:
        """create_transformer delegates to create_transformer_instance helper."""
        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            gold_schema=MagicMock(),
            data_source_creator=MagicMock(),
            transformer_class=None,
        )

        result = factory.create_transformer()
        assert result is None

    @patch("bioetl.composition.factories.pipeline.assembler.build_factory_services")
    def test_build_services_forwards_filter_and_observability(
        self,
        mock_build_factory_services: MagicMock,
    ) -> None:
        """build_services should forward optional filter/tracing seams unchanged."""
        expected_services = MagicMock()
        mock_build_factory_services.return_value = expected_services
        data_source_creator = MagicMock()
        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            gold_schema=MagicMock(),
            data_source_creator=data_source_creator,
        )
        settings = MagicMock()
        logger = MagicMock()
        config = MagicMock()
        filter_config = MagicMock()
        tracer = MagicMock()
        dq_monitor = MagicMock()

        result = factory.build_services(
            settings=settings,
            logger=logger,
            config=config,
            filter_config=filter_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
            audit=MagicMock(),
        )

        assert result is expected_services
        call_kwargs = mock_build_factory_services.call_args.kwargs
        assert call_kwargs["factory_context"].pipeline_name == "chembl_activity"
        assert (
            call_kwargs["factory_context"].create_data_source_fn is data_source_creator
        )
        assert call_kwargs["request"].settings is settings
        assert call_kwargs["request"].logger is logger
        assert call_kwargs["request"].config is config
        assert call_kwargs["request"].filter_config is filter_config
        assert call_kwargs["request"].tracer is tracer
        assert call_kwargs["request"].dq_monitor is dq_monitor

    @patch(
        "bioetl.composition.factories.pipeline.assembler.create_pipeline_instance_with_services"
    )
    def test_create_with_services_forwards_cached_bronze_and_metrics(
        self,
        mock_create_pipeline_with_services: MagicMock,
    ) -> None:
        """create_with_services should preserve optional runtime dependencies."""
        expected_pipeline = MagicMock()
        mock_create_pipeline_with_services.return_value = expected_pipeline
        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            gold_schema=MagicMock(),
            pandera_silver_schema=MagicMock(),
            data_source_creator=MagicMock(),
            transformer_class=MagicMock(),
        )
        run_id = "run-1"
        runtime = MagicMock()
        settings = MagicMock()
        logger = MagicMock()
        config = MagicMock()
        filter_config = MagicMock()
        tracer = MagicMock()
        dq_monitor = MagicMock()
        metrics = MagicMock()
        cached_bronze = MagicMock()
        audit = MagicMock()

        result = factory.create_with_services(
            build_create_pipeline_with_services_request(
                run_id=run_id,
                runtime=runtime,
                started_at=_STARTED_AT,
                settings=settings,
                logger=logger,
                audit=audit,
                config=config,
                filter_config=filter_config,
                tracer=tracer,
                dq_monitor=dq_monitor,
                metrics=metrics,
                cached_bronze=cached_bronze,
            )
        )

        assert result is expected_pipeline
        call_kwargs = mock_create_pipeline_with_services.call_args.kwargs
        assert call_kwargs["factory_context"].pipeline_name == "chembl_activity"
        assert call_kwargs["factory_context"].pipeline_class is factory.pipeline_class
        assert call_kwargs["factory_context"].provider == "chembl"
        assert (
            call_kwargs["factory_context"].create_data_source_fn
            is factory._create_data_source
        )
        assert (
            call_kwargs["factory_context"].transformer_class
            is factory.transformer_class
        )
        assert (
            call_kwargs["factory_context"].pandera_silver_schema
            is factory.pandera_silver_schema
        )
        assert call_kwargs["request"].run_id == run_id
        assert call_kwargs["request"].runtime is runtime
        assert call_kwargs["request"].settings is settings
        assert call_kwargs["request"].logger is logger
        assert call_kwargs["request"].config is config
        assert call_kwargs["request"].filter_config is filter_config
        assert call_kwargs["request"].tracer is tracer
        assert call_kwargs["request"].dq_monitor is dq_monitor
        assert call_kwargs["request"].metrics is metrics
        assert call_kwargs["request"].cached_bronze is cached_bronze

    @patch(
        "bioetl.composition.factories.pipeline.factory_method_helpers.load_pipeline_config"
    )
    @patch("bioetl.composition.factories.pipeline.assembler.assemble_runner")
    def test_create_runner_loads_yaml_config_and_forwards_runtime_support_when_omitted(
        self,
        mock_assemble_runner: MagicMock,
        mock_load_pipeline_config: MagicMock,
    ) -> None:
        """Implicit config path should load YAML once and preserve runtime support seams."""
        yaml_config = MagicMock()
        pipeline = MagicMock()
        runner = MagicMock()
        mock_load_pipeline_config.return_value = yaml_config
        mock_assemble_runner.return_value = runner
        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            data_source_creator=MagicMock(),
        )
        factory.create_with_services = MagicMock(return_value=pipeline)  # type: ignore[method-assign]
        runtime = _make_runtime(strict_gold_validation=False)
        settings = _make_settings(env="dev", test_mode=False)
        observability = _make_observability()
        filter_config = MagicMock()
        cached_bronze = MagicMock()

        result = factory.create_runner(
            PipelineCreateRunnerRequest(
                run_id="run-load-path",
                runtime=runtime,
                started_at=_STARTED_AT,
                settings=settings,
                observability=observability,
                filter_config=filter_config,
                cached_bronze=cached_bronze,
            )
        )

        assert result is runner
        mock_load_pipeline_config.assert_called_once_with("chembl_activity")
        factory.create_with_services.assert_called_once()
        create_request = factory.create_with_services.call_args[0][0]
        assert create_request.run_id == "run-load-path"
        assert create_request.runtime is runtime
        assert create_request.settings is settings
        assert create_request.logger is observability.logger
        assert create_request.config is yaml_config
        assert create_request.filter_config is filter_config
        assert create_request.tracer is observability.tracer
        assert create_request.dq_monitor is observability.dq_monitor
        assert create_request.metrics is observability.metrics
        assert create_request.cached_bronze is cached_bronze
        mock_assemble_runner.assert_called_once_with(
            pipeline=pipeline,
            observability=observability,
            silver_schema=factory.silver_schema,
            gold_schema=factory.gold_schema,
            strict_gold_validation=False,
            yaml_config=yaml_config,
            dq_configs_extractor=ANY,
        )

    @patch(
        "bioetl.composition.factories.pipeline.factory_method_helpers.load_pipeline_config"
    )
    @patch("bioetl.composition.factories.pipeline.assembler.assemble_runner")
    def test_create_runner_uses_explicit_config_and_observability_contract(
        self,
        mock_assemble_runner: MagicMock,
        mock_load_pipeline_config: MagicMock,
    ) -> None:
        """create_runner should wire observability and preserve explicit config."""
        pipeline = MagicMock()
        runner = MagicMock()
        mock_assemble_runner.return_value = runner
        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            data_source_creator=MagicMock(),
        )
        factory.create_with_services = MagicMock(return_value=pipeline)  # type: ignore[method-assign]
        runtime = _make_runtime(strict_gold_validation=False)
        settings = _make_settings(env="dev", test_mode=False)
        observability = _make_observability()
        config = MagicMock()
        filter_config = MagicMock()
        cached_bronze = MagicMock()

        result = factory.create_runner(
            PipelineCreateRunnerRequest(
                run_id="run-1",
                runtime=runtime,
                started_at=_STARTED_AT,
                settings=settings,
                observability=observability,
                filter_config=filter_config,
                config=config,
                cached_bronze=cached_bronze,
            )
        )

        assert result is runner
        mock_load_pipeline_config.assert_not_called()
        factory.create_with_services.assert_called_once()
        create_request = factory.create_with_services.call_args[0][0]
        assert create_request.run_id == "run-1"
        assert create_request.runtime is runtime
        assert create_request.settings is settings
        assert create_request.logger is observability.logger
        assert create_request.config is config
        assert create_request.filter_config is filter_config
        assert create_request.tracer is observability.tracer
        assert create_request.dq_monitor is observability.dq_monitor
        assert create_request.metrics is observability.metrics
        assert create_request.cached_bronze is cached_bronze
        mock_assemble_runner.assert_called_once_with(
            pipeline=pipeline,
            observability=observability,
            silver_schema=factory.silver_schema,
            gold_schema=factory.gold_schema,
            strict_gold_validation=False,
            yaml_config=config,
            dq_configs_extractor=ANY,
        )

    @patch(
        "bioetl.composition.factories.pipeline.factory_method_helpers.load_pipeline_config"
    )
    @patch("bioetl.composition.factories.pipeline.assembler.assemble_runner")
    def test_create_runner_forces_strict_gold_validation_in_prod(
        self,
        mock_assemble_runner: MagicMock,
        mock_load_pipeline_config: MagicMock,
    ) -> None:
        """create_runner should force strict gold validation in prod."""
        yaml_config = MagicMock()
        pipeline = MagicMock()
        mock_load_pipeline_config.return_value = yaml_config
        mock_assemble_runner.return_value = MagicMock()
        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            data_source_creator=MagicMock(),
        )
        factory.create_with_services = MagicMock(return_value=pipeline)  # type: ignore[method-assign]
        runtime = _make_runtime(strict_gold_validation=False)
        settings = _make_settings(env="prod", test_mode=False)
        observability = _make_observability()

        factory.create_runner(
            PipelineCreateRunnerRequest(
                run_id="run-2",
                runtime=runtime,
                started_at=_STARTED_AT,
                settings=settings,
                observability=observability,
            )
        )

        mock_load_pipeline_config.assert_called_once_with("chembl_activity")
        factory.create_with_services.assert_called_once()
        mock_assemble_runner.assert_called_once_with(
            pipeline=pipeline,
            observability=observability,
            silver_schema=factory.silver_schema,
            gold_schema=factory.gold_schema,
            strict_gold_validation=True,
            yaml_config=yaml_config,
            dq_configs_extractor=ANY,
        )


@pytest.mark.unit
class TestCreatePipelineFactory:
    """Tests for create_pipeline_factory convenience function."""

    @patch(
        "bioetl.composition.factories.pipeline._assembler_factory.get_data_source_creator"
    )
    def test_returns_generic_pipeline_factory(
        self, mock_get_creator: MagicMock
    ) -> None:
        """create_pipeline_factory returns a GenericPipelineFactory instance."""
        mock_get_creator.return_value = MagicMock()
        factory = create_pipeline_factory(
            pipeline_name="test_pipeline",
            pipeline_class=MagicMock,
            provider="test",
            gold_schema=MagicMock(),
        )

        assert isinstance(factory, GenericPipelineFactory)
        assert factory.pipeline_name == "test_pipeline"


@pytest.mark.unit
class TestAssembleRunner:
    """Tests for assemble_runner top-level function."""

    @patch("bioetl.composition.factories.pipeline.assembler._assemble_runner_impl")
    @patch("bioetl.composition.factories.pipeline.assembler._extract_dq_configs")
    def test_delegates_to_impl(self, mock_dq: MagicMock, mock_impl: MagicMock) -> None:
        """assemble_runner delegates to _assemble_runner_impl with dq extractor."""
        expected_runner = MagicMock()
        mock_impl.return_value = expected_runner

        pipeline = MagicMock()
        obs = MagicMock()
        gold = MagicMock()

        result = assemble_runner(
            pipeline=pipeline,
            observability=obs,
            silver_schema=None,
            gold_schema=gold,
            strict_gold_validation=True,
        )

        assert result is expected_runner
        mock_impl.assert_called_once()
        call_kwargs = mock_impl.call_args[1]
        assert call_kwargs["pipeline"] is pipeline
        assert call_kwargs["dq_configs_extractor"] is mock_dq
