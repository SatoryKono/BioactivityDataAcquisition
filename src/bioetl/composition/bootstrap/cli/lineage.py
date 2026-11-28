"""Bootstrap functions for lineage CLI operations."""

from __future__ import annotations
from pathlib import Path
from bioetl.application.services.lineage.lineage_inspection_service import (
    LineageInspectionService,
)
from bioetl.composition.bootstrap.assembly.target_classification_runtime import (
    isolated_v30_target_fk_repair,
)
from bioetl.composition.factories.services.port_factories import create_metrics
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.infrastructure.control_plane import (
    FileLineageStore,
    FileRunManifestStore,
)
import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from collections.abc import AsyncIterator
from typing import cast
from uuid import UUID
from bioetl.application.core.base import BasePipeline
from bioetl.application.core.wiring.registry import TargetTransformer
from bioetl.composition.factories.pipeline.assembler import (
    GenericPipelineFactory,
    create_pipeline_factory,
)
from bioetl.composition.factories.pipeline.registry import chembl_target_factory
from bioetl.composition.factories.dq.composite_validation import (
    resolve_target_table_paths,
)
from bioetl.composition.runtime_builders.observability_builder import (
    build_observability_bundle,
)
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.ports import PipelineCreateRunnerRequest
from bioetl.domain.types import (
    BronzeRecord,
    GoldSchemaType,
    HealthStatus,
    RunID,
    RunType,
)
from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_from_root,
)
from bioetl.infrastructure.config.settings_api import ObservabilitySettings, Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.pipeline_contract_policy import (
    PipelineContractPolicy,
)
from bioetl.infrastructure.storage.target_fk_repair import (
    RecoveredTargetSource,
    TargetRepairBaseline,
    freeze_target_baseline,
    publish_repair_candidate,
    read_recovered_target_source,
)

__all__ = ["bootstrap_lineage_service"]


def bootstrap_lineage_service() -> LineageInspectionService:
    """Bootstrap lineage inspection service for CLI commands."""
    settings = get_settings()
    metrics = create_metrics(settings)
    output_root = Path(settings.data_dir) / "output" / "control"
    return LineageInspectionService(
        lineage_store=FileLineageStore(
            base_path=output_root / "lineage",
            metrics=metrics,
        ),
        manifest_port=FileRunManifestStore(
            base_path=output_root / "run_manifest",
            metrics=metrics,
        ),
    )


@dataclass(frozen=True)
class TargetFKRepairRequest:
    """Explicit immutable inputs; output is restricted to a new local report root."""

    repo_root: Path
    source_directory: Path
    output_directory: Path
    run_id: UUID
    started_at: datetime


class _FrozenAPISource:
    """DataSourcePort seam yielding hash-verified API records without network I/O."""

    provider_name = "chembl"

    def __init__(self, source: RecoveredTargetSource) -> None:
        self._source = source

    async def __aenter__(self) -> _FrozenAPISource:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """No network session or external resource is opened."""

    async def health_check(self) -> HealthStatus:
        """The local immutable response has already passed acquisition checks."""
        await asyncio.sleep(0)
        return HealthStatus.HEALTHY

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Replay the complete verified missing-target cohort once."""
        # Pagination is part of the port. This source always replays the full cohort.
        _ = (limit, query, filter_ids, filter_field, offset)
        if entity_type != "target":
            raise ValueError("Recovery source supports target only")
        for record in self._source.records:
            # Separate copies prevent any pipeline normalizer changing frozen inputs.
            yield json.loads(json.dumps(record))


def _prepare_inputs(
    request: TargetFKRepairRequest,
) -> tuple[TargetRepairBaseline, RecoveredTargetSource, Path]:
    root = request.repo_root.resolve(strict=True)
    reports = (root / "reports" / "local").resolve()
    if not reports.is_relative_to(root):
        raise ValueError("reports/local must remain physically inside the repository")
    destination = request.output_directory.resolve()
    if not destination.is_relative_to(reports) or destination == reports:
        raise ValueError("Recovery output must be a new directory under reports/local")
    if destination.exists():
        raise ValueError("Recovery output directory must be new")
    if request.started_at.tzinfo is None:
        raise ValueError("Recovery started_at must include a timezone")
    data = root / "data" / "output"
    baseline = freeze_target_baseline(
        data / "silver" / "chembl" / "target",
        data / "gold" / "chembl" / "target",
        data / "gold" / "chembl" / "assay",
    )
    source = read_recovered_target_source(
        request.source_directory, expected_ids=baseline.missing_ids
    )
    return baseline, source, destination


def isolate_recovery_config(
    config: PipelineYamlConfig, data_root: Path
) -> PipelineYamlConfig:
    """Rebind every ingress path that could feed a writer or metadata exporter."""
    sink = {}
    for layer, item in config.sink.items():
        path = data_root / "output" / layer / "chembl" / "target"
        sink[layer] = item.model_copy(
            update={
                "path": str(path),
                "csv_export": item.csv_export.model_copy(update={"path": str(path)}),
                "dq_report": item.dq_report.model_copy(
                    update={"output_path": str(path / "dq")}
                ),
            }
        )
    report = config.dq_overrides.report.model_copy(
        update={"output_path": str(data_root / "output" / "dq")}
    )
    return config.model_copy(
        update={
            "sink": sink,
            "dq_overrides": config.dq_overrides.model_copy(update={"report": report}),
            "input_filter": config.input_filter.model_copy(
                update={"source_path": str(data_root / "input" / "target.csv")}
            ),
        }
    )


def _verify_isolated_paths(config: PipelineYamlConfig, settings: Settings) -> None:
    root = settings.data_dir.resolve()
    planned = list(resolve_target_table_paths(settings, config))
    for item in config.sink.values():
        planned.extend(
            Path(str(value))
            for value in (item.path, item.csv_export.path, item.dq_report.output_path)
        )
    planned.append(Path(str(config.dq_overrides.report.output_path)))
    if any(not path.resolve().is_relative_to(root) for path in planned):
        raise ValueError("Recovery writer or metadata path escapes isolated data root")


async def prepare_target_fk_repair(request: TargetFKRepairRequest) -> Path:
    """Run actual V30 transforms in isolation, then publish additive candidates.

    ``test_mode`` selects isolated storage roots instead of YAML canonical sink
    paths. It does not replace the transformer, normalizer, filters, schemas,
    identity/hash generator, or Silver/Gold writers with test doubles.
    """
    if request.repo_root.resolve(strict=True) != Path.cwd().resolve():
        raise ValueError("recovery repo_root must match the active contract root")
    baseline, source, destination = _prepare_inputs(request)
    config = load_pipeline_config_from_root(
        "chembl_target", configs_root=request.repo_root / "configs"
    )
    if config.target_classification.mode != "off":
        raise ValueError("V30 recovery requires classification mode off")
    # The loader's public cache is keyed only by provider/entity. Recovery must
    # read this root even if another root was loaded earlier in this process.
    load_pipeline_contract_policy.cache_clear()
    contract = load_pipeline_contract_policy("chembl", "target")
    if contract.active_version != "3.0.0" or contract.write_versions != ["3.0.0"]:
        raise ValueError("V30 recovery requires the single 3.0.0 write contract")
    config = isolate_recovery_config(config, destination / "execution" / "data")
    configuration_bytes = json.dumps(
        {
            "pipeline": config.model_dump(mode="json"),
            "contract_policy": contract.model_dump(mode="json"),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    configuration_path = destination / "execution" / "configuration.json"
    settings = Settings(
        test_mode=True,
        env="dev",
        data_dir=destination / "execution" / "data",
        report_root=destination / "execution" / "reports",
        metrics_enabled=False,
        observability=ObservabilitySettings(
            metrics_enabled=False,
            metrics_server_enabled=False,
            tracing_enabled=False,
            dq_monitor_enabled=False,
        ),
        _env_file=None,  # type: ignore[call-arg]  # BaseSettings runtime-only kwarg.
    )
    _verify_isolated_paths(config, settings)
    configuration_path.parent.mkdir(parents=True)
    configuration_path.write_bytes(configuration_bytes + b"\n")
    return await _execute_isolated_recovery(
        request=request,
        config=config,
        settings=settings,
        contract=contract,
        configuration_path=configuration_path,
        source=source,
        baseline=baseline,
        destination=destination,
    )


async def _execute_isolated_recovery(
    *,
    request: TargetFKRepairRequest,
    config: PipelineYamlConfig,
    settings: Settings,
    contract: PipelineContractPolicy,
    configuration_path: Path,
    source: RecoveredTargetSource,
    baseline: TargetRepairBaseline,
    destination: Path,
) -> Path:
    observability = build_observability_bundle(
        pipeline="chembl_target",
        run_id=RunID(request.run_id),
        settings=settings,
        yaml_config=config,
    )
    source_adapter = _FrozenAPISource(source)
    registered = cast(GenericPipelineFactory[BasePipeline], chembl_target_factory)
    factory = create_pipeline_factory(
        "chembl_target",
        registered.pipeline_class,
        "chembl",
        silver_schema=registered.silver_schema,
        gold_schema=cast(GoldSchemaType, registered.gold_schema),
        pandera_silver_schema=registered.pandera_silver_schema,
        transformer_class=TargetTransformer,
        data_source_creator=lambda *args, **kwargs: source_adapter,
    )
    runtime = RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        limit=len(source.records),
        strict_validation=True,
        strict_gold_validation=True,
    )
    with isolated_v30_target_fk_repair(config):
        runner = factory.create_runner(
            PipelineCreateRunnerRequest(
                run_id=RunID(request.run_id),
                started_at=request.started_at,
                runtime=runtime,
                settings=settings,
                config=config,
                observability=observability,
            )
        )
        await runner.run()
    metrics = runner.execution_metrics
    for key in ("records_silver", "records_gold"):
        if metrics.get(key) != len(source.records):
            raise ValueError(
                f"Actual pipeline did not retain full recovery cohort: {key}"
            )
    reread = read_recovered_target_source(
        request.source_directory, expected_ids=baseline.missing_ids
    )
    if reread.reference != source.reference:
        raise ValueError("Recovery acquisition changed during execution")
    execution = {
        "pipeline": "chembl_target",
        "run_id": str(request.run_id),
        "started_at": request.started_at.isoformat(),
        "status": "completed",
        "metrics": dict(metrics),
        "resolved_configuration": {
            "path": str(configuration_path),
            "sha256": hashlib.sha256(configuration_path.read_bytes()).hexdigest(),
        },
        "contract_policy": contract.model_dump(mode="json"),
        "settings": {
            "isolated_storage_paths": True,
            "test_mode": True,
            "network_source": False,
        },
    }
    return publish_repair_candidate(
        baseline,
        isolated_data_root=settings.data_dir,
        destination=destination / "tables",
        source=source,
        execution=execution,
    )
