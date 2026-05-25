"""Shared builders for RecordProcessor tests."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.composition.factories.services.factory import ServicesBuilder
from bioetl.domain.config import TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.ports.noop import NoOpTracing


def _write_temp_pipeline_config(
    base_path: Path, pipeline_name: str, soft_threshold: float, hard_threshold: float
) -> Path:
    provider, entity = pipeline_name.split("_", 1)
    config_dir = base_path / "configs" / "entities" / provider
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / f"{entity}.yaml"
    config_path.write_text(
        "\n".join(
            [
                "version: '1.0.0'",
                f"provider: {provider}",
                f"entity: {entity}",
                "pipeline:",
                f"  pipeline_name: {pipeline_name}",
                f"  provider: {provider}",
                f"  entity_type: {entity}",
                "  business_primary_keys: ['id']",
                "  silver_table: 'tmp_silver'",
                "  batch_size: 10",
                "  checkpoint_interval: 100",
                "  sink: {}",
                "  dq_overrides:",
                f"    soft_fail_threshold: {soft_threshold}",
                f"    hard_fail_threshold: {hard_threshold}",
                "schema:",
                "  column_groups:",
                "    - name: system",
                "      fields: [entity_id]",
                "    - name: business",
                "      fields: [value]",
                "  silver:",
                "    include_groups: [system, business]",
                "  gold:",
                "    include_groups: [system, business]",
            ]
        ),
        encoding="utf-8",
    )
    base_dir = base_path / "configs" / "base"
    base_dir.mkdir(parents=True, exist_ok=True)
    dq_defaults_path = base_dir / "quality.yaml"
    dq_defaults_path.write_text(
        "\n".join(
            [
                "version: '1.0.0'",
                "thresholds:",
                "  soft_fail: 0.05",
                "  hard_fail: 0.20",
                "strict_validation: false",
                "invalid_record_policy: quarantine",
                "report:",
                "  enabled: true",
                "  format: json",
                "  include_sample_failures: true",
                "  sample_size: 10",
                "  output_path: null",
                "common_field_validations: []",
                "common_cross_field_validations: []",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def _create_record_processor(
    *,
    services: PipelineService,
    error_classifier: ErrorClassifier,
    context: PipelineContext,
    config: RecordProcessorConfig,
    transform_callback,
    gold_filter_callback,
    gold_transform_callback,
    gold_validator,
    tracer=None,
    lock_validator=None,
) -> RecordProcessor:
    effective_tracer = tracer if tracer is not None else NoOpTracing()
    components = ServicesBuilder.create_batch_processing_components(
        services=services,
        context=context,
        config=config,
        error_classifier=error_classifier,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
        gold_validator=gold_validator,
        tracer=effective_tracer,
        lock_validator=lock_validator,
    )
    return RecordProcessor(
        context=context,
        batch_metrics=components.batch_metrics,
        transformer=components.transformer,
        writer=components.writer,
        config=config,
        tracer=effective_tracer,
    )


def _create_record_processor_config(
    *,
    pipeline_name: str = "test_provider_test_entity",
    provider: str = "test_provider",
    entity_type: str = "test_entity",
    table_config: TableConfig | None = None,
    dq_config: object | None = None,
) -> RecordProcessorConfig:
    config_kwargs = {
        "pipeline_name": pipeline_name,
        "provider": provider,
        "entity_type": entity_type,
        "silver_schema": None,
        "gold_schema": None,
    }
    if table_config is not None:
        config_kwargs["table_config"] = table_config
    if dq_config is not None:
        config_kwargs["dq_config"] = dq_config
    return RecordProcessorConfig(**config_kwargs)
