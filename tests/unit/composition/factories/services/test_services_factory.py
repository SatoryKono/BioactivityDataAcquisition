"""Unit tests for composition.services_factory branch coverage."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.services.callbacks import (
    create_data_normalization_service,
    extract_pipeline_callbacks,
)
from bioetl.composition.factories.services._builder_record_processor_support import (
    _RecordProcessorBuildRequest,
)
from bioetl.composition.factories.services.factory import (
    BaseServicesFactory,
    ServicesBuilder,
)
from bioetl.domain.behavior import DataNormalizationConfig, DefaultDataNormalizer
from bioetl.composition.factories.services.port_factories import (
    create_metrics,
)
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


def _make_settings(**overrides: object) -> Settings:
    defaults = {
        "env": "dev",
        "test_mode": True,
        "metrics_enabled": False,
        "data_dir": MagicMock(),
    }
    defaults.update(overrides)
    return cast(Settings, SimpleNamespace(**defaults))


def _make_pipeline_config(**overrides: object) -> PipelineYamlConfig:
    defaults = {
        "pipeline_name": "chembl_activity",
        "sink": {},
    }
    defaults.update(overrides)
    return cast(PipelineYamlConfig, SimpleNamespace(**defaults))


@pytest.mark.unit
def test_extract_pipeline_callbacks_uses_transformer_when_present() -> None:
    transformer = SimpleNamespace(
        transform=MagicMock(name="transform"),
        should_write_gold=MagicMock(name="gold_filter"),
        transform_for_gold=MagicMock(name="gold_transform"),
    )
    pipeline = SimpleNamespace(transformer=transformer)

    callbacks = extract_pipeline_callbacks(pipeline)

    assert callbacks.transform is transformer.transform
    assert callbacks.gold_filter is transformer.should_write_gold
    assert callbacks.gold_transform is transformer.transform_for_gold


@pytest.mark.unit
def test_extract_pipeline_callbacks_prefers_pre_silver_transform_when_available() -> (
    None
):
    transformer = SimpleNamespace(
        transform=MagicMock(name="transform"),
        transform_pre_silver=MagicMock(name="transform_pre_silver"),
        should_write_gold=MagicMock(name="gold_filter"),
        transform_for_gold=MagicMock(name="gold_transform"),
    )
    pipeline = SimpleNamespace(transformer=transformer)

    callbacks = extract_pipeline_callbacks(pipeline)

    assert callbacks.transform is transformer.transform_pre_silver


@pytest.mark.unit
def test_extract_pipeline_callbacks_legacy_defaults() -> None:
    transform_cb = MagicMock(name="transform")
    pipeline = SimpleNamespace(
        transformer=None,
        transform_bronze_to_silver=transform_cb,
    )

    callbacks = extract_pipeline_callbacks(pipeline)

    assert callbacks.transform is transform_cb
    assert callbacks.gold_filter(None, {"x": 1}) is True
    sample = {"id": "A"}
    assert callbacks.gold_transform(None, sample) == sample


@pytest.mark.unit
def test_extract_pipeline_callbacks_legacy_requires_transform_method() -> None:
    pipeline = SimpleNamespace(transformer=None)

    with pytest.raises(AttributeError):
        extract_pipeline_callbacks(pipeline)


@pytest.mark.unit
def test_create_common_services_requires_silver_validator_in_prod() -> None:
    settings = _make_settings(env="prod", test_mode=False)
    pipeline_config = _make_pipeline_config()

    with pytest.raises(ValueError, match="Silver validator is required"):
        BaseServicesFactory.create_common_services(
            settings=settings,
            logger=MagicMock(),
            data_source=MagicMock(),
            pipeline_config=pipeline_config,
            pipeline_name="test_pipeline",
            audit=MagicMock(),
            silver_validator=None,
        )


@pytest.mark.unit
@patch("bioetl.composition.factories.services.factory.StorageFactory.create")
@patch("bioetl.composition.factories.services.factory.create_lock")
@patch("bioetl.composition.factories.services.factory.create_checkpoint")
@patch("bioetl.composition.factories.services.factory.create_quarantine")
@patch.object(BaseServicesFactory, "_create_dq_services")
def test_create_common_services_uses_noop_tracing_when_not_provided(
    mock_create_dq_services: MagicMock,
    mock_create_quarantine: MagicMock,
    mock_create_checkpoint: MagicMock,
    mock_create_lock: MagicMock,
    mock_storage_create: MagicMock,
) -> None:
    settings = _make_settings()
    data_source = MagicMock()
    logger = MagicMock()
    pipeline_config = _make_pipeline_config()

    storage_ctx = SimpleNamespace(
        adapter=MagicMock(), checkpoints_path="test-output/checkpoints"
    )
    mock_storage_create.return_value = storage_ctx
    mock_create_lock.return_value = MagicMock()
    mock_create_checkpoint.return_value = MagicMock()
    mock_create_quarantine.return_value = MagicMock()
    mock_create_dq_services.return_value = {}

    services = BaseServicesFactory.create_common_services(
        settings=settings,
        logger=logger,
        data_source=data_source,
        pipeline_config=pipeline_config,
        pipeline_name="test_pipeline",
        audit=MagicMock(),
        metrics=MagicMock(),
        tracer=None,
    )

    assert services.tracing is not None
    assert services.data_source is data_source


@pytest.mark.unit
def test_create_metrics_returns_noop_when_disabled() -> None:
    settings = SimpleNamespace(metrics_enabled=False)

    metrics = create_metrics(settings)

    assert metrics.__class__.__name__ == "NoOpMetrics"


@pytest.mark.unit
@patch("bioetl.composition.factories.services.port_factories.resolve_metrics_port")
def test_create_metrics_returns_prometheus_when_enabled(
    mock_resolve_metrics_port: MagicMock,
) -> None:
    settings = SimpleNamespace(metrics_enabled=True)
    expected = MagicMock()
    mock_resolve_metrics_port.return_value = expected

    metrics = create_metrics(settings)

    assert metrics is expected


@pytest.mark.unit
def test_get_output_root_uses_bronze_path_when_available() -> None:
    settings = _make_settings(test_mode=False, data_dir=MagicMock())
    pipeline_config = _make_pipeline_config(
        sink={
            "bronze": SimpleNamespace(path="data/output/bronze/chembl/activity"),
        }
    )

    output_root = BaseServicesFactory._get_output_root(settings, pipeline_config)

    assert output_root.as_posix().endswith("data/output")


@pytest.mark.unit
def test_get_output_root_falls_back_to_settings_data_dir() -> None:
    settings = _make_settings(
        test_mode=True,
        data_dir=SimpleNamespace(name="data"),
    )
    pipeline_config = _make_pipeline_config(
        sink={"bronze": SimpleNamespace(path="x/y/z")}
    )

    output_root = BaseServicesFactory._get_output_root(settings, pipeline_config)

    assert output_root is settings.data_dir


@pytest.mark.unit
def test_create_dq_services_returns_empty_when_disabled() -> None:
    settings = _make_settings()
    pipeline_config = _make_pipeline_config(
        sink={"bronze": None, "silver": None, "gold": None}
    )

    result = BaseServicesFactory._create_dq_services(
        settings=settings,
        pipeline_config=pipeline_config,
        logger=MagicMock(),
    )

    assert result == {}


@pytest.mark.unit
def test_is_dq_report_enabled_false_when_all_disabled() -> None:
    pipeline_config = _make_pipeline_config(
        sink={
            "bronze": SimpleNamespace(dq_report=SimpleNamespace(enabled=False)),
            "silver": None,
            "gold": None,
        }
    )

    assert BaseServicesFactory._is_dq_report_enabled(pipeline_config) is False


@pytest.mark.unit
def test_get_flat_structure_false_when_not_configured() -> None:
    pipeline_config = _make_pipeline_config(sink={"silver": None, "gold": None})

    assert BaseServicesFactory._get_flat_structure(pipeline_config) is False


@pytest.mark.unit
def test_is_dq_report_enabled_true_when_any_layer_enabled() -> None:
    pipeline_config = _make_pipeline_config(
        sink={
            "bronze": None,
            "silver": SimpleNamespace(dq_report=SimpleNamespace(enabled=True)),
            "gold": None,
        }
    )

    assert BaseServicesFactory._is_dq_report_enabled(pipeline_config) is True


@pytest.mark.unit
def test_get_flat_structure_true_when_gold_enabled() -> None:
    pipeline_config = _make_pipeline_config(
        sink={
            "silver": SimpleNamespace(flat_structure=False),
            "gold": SimpleNamespace(flat_structure=True),
        }
    )

    assert BaseServicesFactory._get_flat_structure(pipeline_config) is True


@pytest.mark.unit
@patch("bioetl.application.services.dq_report_service.DQReportService")
@patch(
    "bioetl.composition.factories.dq.context_resolver.DQServicesFactory.create_report_writer"
)
@patch(
    "bioetl.composition.factories.dq.context_resolver.DQServicesFactory.create_gold_analyzer"
)
@patch(
    "bioetl.composition.factories.dq.context_resolver.DQServicesFactory.create_silver_analyzer"
)
@patch(
    "bioetl.composition.factories.dq.context_resolver.DQServicesFactory.create_bronze_analyzer"
)
@patch(
    "bioetl.composition.factories.dq.context_resolver.get_flat_structure",
    return_value=True,
)
@patch("bioetl.composition.factories.dq.context_resolver.get_output_root")
@patch(
    "bioetl.composition.factories.dq.context_resolver.is_dq_report_enabled",
    return_value=True,
)
def test_create_dq_services_builds_enabled_stack(
    _mock_enabled: MagicMock,
    mock_output_root: MagicMock,
    _mock_flat_structure: MagicMock,
    mock_bronze_analyzer: MagicMock,
    mock_silver_analyzer: MagicMock,
    mock_gold_analyzer: MagicMock,
    mock_report_writer: MagicMock,
    mock_report_service: MagicMock,
) -> None:
    settings = _make_settings()
    pipeline_config = _make_pipeline_config(sink={})
    logger = MagicMock()

    mock_bronze_analyzer.return_value = "bronze"
    mock_silver_analyzer.return_value = "silver"
    mock_gold_analyzer.return_value = "gold"
    mock_report_writer.return_value = "writer"
    mock_report_service.return_value = "service"
    mock_output_root.return_value = Path("data/output")

    result = BaseServicesFactory._create_dq_services(
        settings=settings,
        pipeline_config=pipeline_config,
        logger=logger,
    )

    assert result["bronze_analyzer"] == "bronze"
    assert result["silver_analyzer"] == "silver"
    assert result["gold_analyzer"] == "gold"
    assert result["report_writer"] == "writer"
    assert result["report_service"] == "service"


@pytest.mark.unit
@patch(
    "bioetl.composition.factories.services.pipeline_record_processor_builder.RecordProcessor"
)
@patch(
    "bioetl.composition.factories.services.pipeline_record_processor_builder.PanderaGoldValidator"
)
@patch(
    "bioetl.composition.factories.services.pipeline_record_processor_builder.RecordProcessorConfig"
)
@patch(
    "bioetl.composition.factories.services.pipeline_record_processor_builder.TableConfig"
)
def test_create_record_processor_builds_dependencies(
    mock_table_config: MagicMock,
    mock_processor_config: MagicMock,
    mock_gold_validator: MagicMock,
    mock_record_processor: MagicMock,
) -> None:
    services = MagicMock()
    context = MagicMock()

    result = ServicesBuilder.create_record_processor(
        request=_RecordProcessorBuildRequest(
            create_batch_processing_components_fn=(
                ServicesBuilder.create_batch_processing_components
            ),
            services=services,
            context=context,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=MagicMock(),
            primary_keys=("activity_id",),
            silver_table="activity",
            gold_table="activity_gold",
            silver_write_mode="merge",
            gold_write_mode="overwrite",
            on_schema_mismatch="error",
            transform_callback=MagicMock(),
            gold_filter_callback=MagicMock(),
            gold_transform_callback=MagicMock(),
            tracer=None,
            strict_gold_validation=True,
            lock_validator=None,
            column_groups=(),
            scd_config=None,
            content_hash_include_fields=frozenset(),
            content_hash_exclude_fields=frozenset(),
            content_hash_policy_by_version=None,
            gold_schema_policy_by_version=None,
            record_processor_config_cls=mock_processor_config,
            table_config_cls=mock_table_config,
            gold_validator_factory=mock_gold_validator,
            record_processor_cls=mock_record_processor,
        ),
    )

    assert result is mock_record_processor.return_value
    mock_table_config.assert_called_once()
    mock_processor_config.assert_called_once()
    mock_gold_validator.assert_called_once()
    mock_record_processor.assert_called_once()


@pytest.mark.unit
def test_create_record_processor_from_pipeline_delegates() -> None:
    pipeline = SimpleNamespace(
        services=MagicMock(),
        context=MagicMock(),
        config=SimpleNamespace(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            dq=MagicMock(),
            table=SimpleNamespace(
                primary_keys=("activity_id",),
                silver_write_mode="merge",
                gold_write_mode="overwrite",
                on_schema_mismatch="error",
            ),
            effective_silver_table="activity",
            effective_gold_table="activity_gold",
            column_groups=(),
            scd_config=None,
        ),
    )
    callbacks = SimpleNamespace(
        transform=MagicMock(),
        gold_filter=MagicMock(),
        gold_transform=MagicMock(),
    )

    with (
        patch(
            "bioetl.composition.factories.services.builder.extract_pipeline_callbacks"
        ) as mock_extract,
        patch.object(ServicesBuilder, "create_record_processor") as mock_create,
    ):
        mock_extract.return_value = callbacks
        mock_create.return_value = MagicMock()

        ServicesBuilder.create_record_processor_from_pipeline(
            pipeline=pipeline,
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )

    mock_extract.assert_called_once_with(pipeline)
    mock_create.assert_called_once()


@pytest.mark.unit
def test_create_data_normalization_service_uses_default_config() -> None:
    result = create_data_normalization_service(config=None)

    assert isinstance(result, DefaultDataNormalizer)
    assert isinstance(result.config, DataNormalizationConfig)


@pytest.mark.unit
def test_create_data_normalization_service_uses_explicit_config() -> None:
    explicit_config = MagicMock()
    result = create_data_normalization_service(config=explicit_config)

    assert isinstance(result, DefaultDataNormalizer)
    assert result.config is explicit_config
