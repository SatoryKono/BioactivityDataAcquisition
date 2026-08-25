"""Support helpers for resolving DQ service context inputs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from bioetl.composition.bootstrap_contexts import DQConfigsContext, DQOutputPathsContext
from bioetl.domain.value_objects.dq_report import SilverDQCheckType

if TYPE_CHECKING:
    from pydantic import BaseModel

    from bioetl.domain.ports import (
        BronzeDQConfigPort,
        GoldDQConfigPort,
        LoggerPort,
        MetricsPort,
        SilverDQConfigPort,
    )
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


from bioetl.composition.contracts.structural import ModelDumpable

from bioetl.application.ports.dq import DQReportServiceFactoryProtocol

from bioetl.infrastructure.schemas.dq_report_config import (
    BronzeSinkConfig,
    GoldSinkConfig,
    SilverSinkConfig,
)


@dataclass(frozen=True, slots=True)
class DQServiceBundle:
    """Typed DQ service collaborators created by composition factories."""

    bronze_analyzer: object | None = None
    silver_analyzer: object | None = None
    gold_analyzer: object | None = None
    report_writer: object | None = None
    report_service: object | None = None

    def __bool__(self) -> bool:
        return self.report_service is not None


def extract_single_dq_config_impl(
    sink: Mapping[str, object],
    layer_name: str,
    config_class: type[BaseModel],
) -> BronzeDQConfigPort | SilverDQConfigPort | GoldDQConfigPort | None:
    sink_config = sink.get(layer_name)
    if not sink_config or not hasattr(sink_config, "model_dump"):
        return None
    validated = config_class.model_validate(
        cast(ModelDumpable, sink_config).model_dump()
    )
    dq_report = getattr(validated, "dq_report", None)
    if dq_report is not None and getattr(dq_report, "enabled", False):
        return cast(
            "BronzeDQConfigPort | SilverDQConfigPort | GoldDQConfigPort",
            dq_report,
        )
    return None


def extract_dq_configs_impl(
    yaml_config: PipelineYamlConfig | None,
    *,
    extract_single_dq_config_fn: Callable[..., object],
    relaxed_dq: bool = False,
) -> DQConfigsContext:

    if yaml_config is None:
        return DQConfigsContext(bronze=None, silver=None, gold=None)

    sink = getattr(yaml_config, "sink", None)
    if sink is None or not isinstance(sink, Mapping):
        return DQConfigsContext(bronze=None, silver=None, gold=None)

    sink_mapping = cast(Mapping[str, object], sink)
    silver_config = cast(
        "SilverDQConfigPort | None",
        extract_single_dq_config_fn(sink_mapping, "silver", SilverSinkConfig),
    )
    if silver_config is not None and relaxed_dq:
        silver_config = _trim_relaxed_silver_checks(silver_config)

    return DQConfigsContext(
        bronze=cast(
            "BronzeDQConfigPort | None",
            extract_single_dq_config_fn(sink_mapping, "bronze", BronzeSinkConfig),
        ),
        silver=silver_config,
        gold=cast(
            "GoldDQConfigPort | None",
            extract_single_dq_config_fn(sink_mapping, "gold", GoldSinkConfig),
        ),
    )


def _trim_relaxed_silver_checks(
    silver_config: SilverDQConfigPort,
) -> SilverDQConfigPort:
    """Remove expensive Silver profiling checks for relaxed-DQ flows."""
    checks = getattr(silver_config, "checks", None)
    if not isinstance(checks, list):
        return silver_config

    expensive_check = SilverDQCheckType.VALUE_DISTRIBUTION.value
    if expensive_check not in checks:
        return silver_config

    model_copy = getattr(silver_config, "model_copy", None)
    if not callable(model_copy):
        raise TypeError("Silver DQ config must support immutable model_copy updates")
    return cast(
        "SilverDQConfigPort",
        model_copy(
            update={"checks": [check for check in checks if check != expensive_check]}
        ),
    )


def get_layer_path_impl(config: object) -> str | None:
    return getattr(config, "path", None) if config else None


def has_flat_structure_impl(config: object) -> bool:
    return bool(config and getattr(config, "flat_structure", False))


def extract_dq_output_paths_impl(
    yaml_config: PipelineYamlConfig | None,
    *,
    get_layer_path_fn: Callable[[object], str | None],
    has_flat_structure_fn: Callable[[object], bool],
) -> DQOutputPathsContext:
    if yaml_config is None:
        return DQOutputPathsContext(
            bronze_path=None,
            silver_path=None,
            gold_path=None,
            flat_structure=False,
        )

    sink = getattr(yaml_config, "sink", None)
    if sink is None or not isinstance(sink, Mapping):
        return DQOutputPathsContext(
            bronze_path=None,
            silver_path=None,
            gold_path=None,
            flat_structure=False,
        )

    sink_mapping = cast(Mapping[str, object], sink)
    bronze_config = sink_mapping.get("bronze")
    silver_config = sink_mapping.get("silver")
    gold_config = sink_mapping.get("gold")
    return DQOutputPathsContext(
        bronze_path=get_layer_path_fn(bronze_config),
        silver_path=get_layer_path_fn(silver_config),
        gold_path=get_layer_path_fn(gold_config),
        flat_structure=has_flat_structure_fn(silver_config)
        or has_flat_structure_fn(gold_config),
    )


def is_dq_report_enabled_impl(config: PipelineYamlConfig) -> bool:
    sink = config.sink
    for layer_name in ("bronze", "silver", "gold"):
        layer_config = sink.get(layer_name)
        if layer_config and layer_config.dq_report.enabled:
            return True
    return False


def get_flat_structure_impl(config: PipelineYamlConfig) -> bool:
    sink = config.sink
    for layer_name in ("silver", "gold"):
        layer_config = sink.get(layer_name)
        if layer_config and getattr(layer_config, "flat_structure", False):
            return True
    return False


def get_output_root_impl(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
) -> Path:
    """Resolve the canonical managed output root from settings.

    Output layout is always ``{data_dir}/output`` (ADR-025). Pipeline sink
    bronze paths are not used as a climb source — that produced divergent
    roots when bronze was configured outside the managed tree.
    """
    del pipeline_config  # root is settings-scoped, not sink-path-derived
    return Path(settings.data_dir) / "output"


def create_dq_services_impl(
    settings: Settings,
    pipeline_config: PipelineYamlConfig,
    logger: LoggerPort,
    *,
    metrics: MetricsPort | None,
    create_bronze_analyzer_fn: Callable[[], object],
    create_silver_analyzer_fn: Callable[[], object],
    create_gold_analyzer_fn: Callable[[], object],
    create_report_writer_fn: Callable[..., object],
    dq_report_service_cls: DQReportServiceFactoryProtocol,
    is_dq_report_enabled_fn: Callable[[PipelineYamlConfig], bool],
    get_output_root_fn: Callable[[Settings, PipelineYamlConfig], Path],
    get_flat_structure_fn: Callable[[PipelineYamlConfig], bool],
) -> DQServiceBundle:
    if not is_dq_report_enabled_fn(pipeline_config):
        return DQServiceBundle()

    bronze_analyzer = create_bronze_analyzer_fn()
    silver_analyzer = create_silver_analyzer_fn()
    gold_analyzer = create_gold_analyzer_fn()
    report_writer = create_report_writer_fn(
        base_path=get_output_root_fn(settings, pipeline_config) / "reports" / "dq",
        logger=logger,
        flat_structure=get_flat_structure_fn(pipeline_config),
    )
    report_service = dq_report_service_cls(
        logger=logger,
        bronze_analyzer=bronze_analyzer,
        silver_analyzer=silver_analyzer,
        gold_analyzer=gold_analyzer,
        report_writer=report_writer,
        metrics=metrics,
    )
    return DQServiceBundle(
        bronze_analyzer=bronze_analyzer,
        silver_analyzer=silver_analyzer,
        gold_analyzer=gold_analyzer,
        report_writer=report_writer,
        report_service=report_service,
    )
