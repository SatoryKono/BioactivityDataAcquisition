"""Targeted branch-coverage tests for canonical composition pipeline helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.dq.context_resolver import (
    extract_dq_configs,
    extract_dq_output_paths,
    extract_single_dq_config,
)
from bioetl.composition.factories.pipeline import GenericPipelineFactory
from bioetl.composition.factories.services.bundle import (
    _create_cached_bronze_data_source,
    build_pipeline_services,
)
from bioetl.composition.factories.services.factory import BaseServicesFactory
from bioetl.domain.value_objects.dq_report import SilverDQCheckType
from bioetl.infrastructure.schemas.dq_report_config import (
    SilverDQReportConfig,
    SilverSinkConfig,
)

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-pipeline-factory-"))
CUSTOM_BRONZE_PATH = str(TEST_ROOT / "custom-bronze")
CACHED_BRONZE_PATH = str(TEST_ROOT / "bronze")


@pytest.mark.unit
def test_generic_pipeline_factory_requires_gold_schema() -> None:
    with pytest.raises(ValueError, match="gold_schema is required"):
        GenericPipelineFactory(
            pipeline_name="chembl_publication",
            pipeline_class=MagicMock(),
            provider="chembl",
            gold_schema=None,
        )


@pytest.mark.unit
def test_generic_pipeline_factory_create_transformer_returns_none_without_class() -> (
    None
):
    factory = GenericPipelineFactory(
        pipeline_name="chembl_publication",
        pipeline_class=MagicMock(),
        provider="chembl",
        gold_schema=MagicMock(),
        transformer_class=None,
    )

    assert factory.create_transformer() is None


@pytest.mark.unit
def test_generic_pipeline_factory_create_transformer_builds_instance() -> None:
    transformer_instance = MagicMock()
    transformer_class = MagicMock(return_value=transformer_instance)
    factory = GenericPipelineFactory(
        pipeline_name="chembl_publication",
        pipeline_class=MagicMock(),
        provider="chembl",
        gold_schema=MagicMock(),
        transformer_class=transformer_class,
    )

    result = factory.create_transformer(tracer=MagicMock(), metrics=MagicMock())

    assert result is transformer_instance
    transformer_class.assert_called_once()


@pytest.mark.unit
@patch("bioetl.infrastructure.adapters.CachedBronzeDataSource")
@patch("bioetl.infrastructure.storage.bronze_writer.BronzeWriter")
def test_create_cached_bronze_data_source_uses_explicit_path(
    mock_bronze_writer: MagicMock,
    mock_cached_source: MagicMock,
) -> None:
    expected_source = MagicMock()
    mock_cached_source.return_value = expected_source
    logger = MagicMock()

    result = _create_cached_bronze_data_source(
        settings=SimpleNamespace(bronze_path=Path("/data/output/bronze")),
        pipeline_config=SimpleNamespace(provider="chembl", entity_type="publication"),
        logger=logger,
        cached_bronze=SimpleNamespace(
            bronze_path=CUSTOM_BRONZE_PATH,
            bronze_date="2026-03-03",
        ),
    )

    assert result is expected_source
    assert mock_bronze_writer.call_args.kwargs["base_path"] == Path(CUSTOM_BRONZE_PATH)
    mock_cached_source.assert_called_once()


@pytest.mark.unit
@patch("bioetl.infrastructure.adapters.CachedBronzeDataSource")
@patch("bioetl.infrastructure.storage.bronze_writer.BronzeWriter")
def test_create_cached_bronze_data_source_falls_back_to_convention_path(
    mock_bronze_writer: MagicMock,
    mock_cached_source: MagicMock,
) -> None:
    expected_source = MagicMock()
    mock_cached_source.return_value = expected_source
    logger = MagicMock()

    result = _create_cached_bronze_data_source(
        settings=SimpleNamespace(bronze_path=Path("/data/output/bronze")),
        pipeline_config=SimpleNamespace(provider="chembl", entity_type="publication"),
        logger=logger,
        cached_bronze=SimpleNamespace(
            bronze_path=None,
            bronze_date=None,
        ),
    )

    assert result is expected_source
    assert mock_bronze_writer.call_args.kwargs["base_path"] == Path(
        "/data/output/bronze/chembl/publication"
    )
    mock_cached_source.assert_called_once()


@pytest.mark.unit
@patch.object(BaseServicesFactory, "create_common_services")
@patch.object(BaseServicesFactory, "_create_metrics")
@patch("bioetl.composition.factories.services.bundle._create_data_source")
@patch("bioetl.composition.factories.services.bundle._create_cached_bronze_data_source")
def test_build_pipeline_services_uses_cached_bronze_when_enabled(
    mock_cached_source: MagicMock,
    mock_data_source: MagicMock,
    mock_create_metrics: MagicMock,
    mock_create_common_services: MagicMock,
) -> None:
    logger = MagicMock()
    settings = SimpleNamespace()
    pipeline_config = SimpleNamespace(provider="chembl", entity_type="publication")
    cached_bronze = SimpleNamespace(
        enabled=True,
        bronze_path=CACHED_BRONZE_PATH,
        bronze_date="2026-03-02",
    )

    mock_create_metrics.return_value = "metrics"
    mock_cached_source.return_value = "cached-source"
    mock_create_common_services.return_value = "services"

    result = build_pipeline_services(
        pipeline_name="chembl_publication",
        create_data_source_fn=MagicMock(),
        settings=settings,
        logger=logger,
        audit=MagicMock(),
        config=pipeline_config,
        cached_bronze=cached_bronze,
    )

    assert result == "services"
    mock_cached_source.assert_called_once()
    mock_data_source.assert_not_called()
    logger.info.assert_called_once()
    mock_create_common_services.assert_called_once()


@pytest.mark.unit
@patch.object(BaseServicesFactory, "create_common_services")
@patch.object(BaseServicesFactory, "_create_metrics")
@patch("bioetl.composition.factories.services.bundle._create_data_source")
@patch("bioetl.composition.factories.services.bundle._create_cached_bronze_data_source")
def test_build_pipeline_services_uses_regular_data_source_when_cached_disabled(
    mock_cached_source: MagicMock,
    mock_data_source: MagicMock,
    mock_create_metrics: MagicMock,
    mock_create_common_services: MagicMock,
) -> None:
    logger = MagicMock()
    settings = SimpleNamespace()
    pipeline_config = SimpleNamespace(provider="chembl", entity_type="publication")
    cached_bronze = SimpleNamespace(enabled=False)

    mock_create_metrics.return_value = "metrics"
    mock_data_source.return_value = "regular-source"
    mock_create_common_services.return_value = "services"

    result = build_pipeline_services(
        pipeline_name="chembl_publication",
        create_data_source_fn=MagicMock(),
        settings=settings,
        logger=logger,
        audit=MagicMock(),
        config=pipeline_config,
        cached_bronze=cached_bronze,
    )

    assert result == "services"
    mock_data_source.assert_called_once()
    mock_cached_source.assert_not_called()


@pytest.mark.unit
def test_extract_single_dq_config_returns_none_when_layer_absent() -> None:
    result = extract_single_dq_config(
        sink={"bronze": None},
        layer_name="bronze",
        config_class=MagicMock(),
    )

    assert result is None


@pytest.mark.unit
def test_extract_single_dq_config_returns_none_when_not_pydantic_model() -> None:
    result = extract_single_dq_config(
        sink={"bronze": object()},
        layer_name="bronze",
        config_class=MagicMock(),
    )

    assert result is None


class _EnabledConfigClass:
    @staticmethod
    def model_validate(_: dict[str, object]) -> SimpleNamespace:
        return SimpleNamespace(
            dq_report=SimpleNamespace(enabled=True, name="dq-report")
        )


class _DisabledConfigClass:
    @staticmethod
    def model_validate(_: dict[str, object]) -> SimpleNamespace:
        return SimpleNamespace(dq_report=SimpleNamespace(enabled=False))


@pytest.mark.unit
def test_extract_single_dq_config_returns_enabled_dq_report() -> None:
    sink_cfg = SimpleNamespace(model_dump=lambda: {"path": "data/output/bronze"})

    result = extract_single_dq_config(
        sink={"bronze": sink_cfg},
        layer_name="bronze",
        config_class=_EnabledConfigClass,
    )

    assert result is not None
    assert result.name == "dq-report"


@pytest.mark.unit
def test_extract_single_dq_config_returns_none_when_dq_disabled() -> None:
    sink_cfg = SimpleNamespace(model_dump=lambda: {"path": "data/output/bronze"})

    result = extract_single_dq_config(
        sink={"bronze": sink_cfg},
        layer_name="bronze",
        config_class=_DisabledConfigClass,
    )

    assert result is None


@pytest.mark.unit
def test_extract_dq_configs_returns_empty_context_for_none_yaml() -> None:
    dq_configs = extract_dq_configs(None)

    assert dq_configs.bronze is None
    assert dq_configs.silver is None
    assert dq_configs.gold is None


@pytest.mark.unit
def test_extract_dq_configs_returns_empty_context_for_missing_sink() -> None:
    yaml_config = SimpleNamespace(sink=None)

    dq_configs = extract_dq_configs(yaml_config)

    assert dq_configs.bronze is None
    assert dq_configs.silver is None
    assert dq_configs.gold is None


@pytest.mark.unit
def test_extract_dq_configs_trims_value_distribution_for_relaxed_dq() -> None:
    silver_sink = SilverSinkConfig(
        path="data/output/silver",
        dq_report=SilverDQReportConfig(enabled=True),
    )
    yaml_config = SimpleNamespace(sink={"silver": silver_sink})

    dq_configs = extract_dq_configs(yaml_config, relaxed_dq=True)

    assert dq_configs.silver is not None
    assert (
        SilverDQCheckType.VALUE_DISTRIBUTION not in dq_configs.silver.get_checks_enums()
    )
    assert SilverDQCheckType.VALUE_DISTRIBUTION.value in silver_sink.dq_report.checks


@pytest.mark.unit
def test_extract_dq_output_paths_returns_defaults_for_none_yaml() -> None:
    paths = extract_dq_output_paths(None)

    assert paths.bronze_path is None
    assert paths.silver_path is None
    assert paths.gold_path is None
    assert paths.flat_structure is False


@pytest.mark.unit
def test_extract_dq_output_paths_returns_defaults_for_missing_sink() -> None:
    yaml_config = SimpleNamespace(sink=None)

    paths = extract_dq_output_paths(yaml_config)

    assert paths.bronze_path is None
    assert paths.silver_path is None
    assert paths.gold_path is None
    assert paths.flat_structure is False
