"""CLI metrics bootstrap and target deployment binding."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, cast

import yaml

from bioetl.application.observability.control_plane_integrity_metrics import (
    ControlPlaneIntegrityMetricsService,
)
from bioetl.application.services.ops.metrics_service import MetricsService
from bioetl.composition.observability_resolution import resolve_tracing_port
from bioetl.infrastructure.observability.metrics_publisher_adapter import (
    MetricsPublisherAdapter,
)
from bioetl.infrastructure.observability.metrics_server_adapter import (
    MetricsServerAdapter,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.time import SystemClock
from bioetl.composition.runtime_builders import control_plane_root
from bioetl.composition.bootstrap.assembly.storage import (
    load_target_runtime_profile,
)
from bioetl.composition.factories.dq.composite_validation import (
    resolve_target_table_paths,
)
from bioetl.composition.runtime_builders.config_access import (
    get_settings,
    resolve_configs_root,
)
from bioetl.domain.exceptions import BioETLError
from bioetl.infrastructure.control_plane import (
    FileRunLedgerStore,
    FileRunManifestStore,
)
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_uncached,
)
from bioetl.infrastructure.config.target_classification_profile import (
    resolve_target_classification_profile,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.target_classification_config import (
    TargetClassificationYamlConfig,
)
from bioetl.infrastructure.storage.target_classification_migration import (
    TargetMigrationPaths,
)
from bioetl.infrastructure.storage.target_deployment_binding import (
    TargetDeploymentBinding,
    validate_rehearsal_paths,
)
from iuphar_target_class.stage0.io import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, TracingPort
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "bind_target_deployment",
    "bind_target_rehearsal",
    "bootstrap_metrics_service",
    "create_metrics_service",
]


def create_metrics_service(
    *,
    logger: LoggerPort | None = None,
    tracer: TracingPort | None = None,
) -> MetricsService:
    """Build a metrics service with a composition-owned server adapter."""
    resolved_logger = logger if logger is not None else NoOpLogger()
    return MetricsService(
        logger=resolved_logger,
        clock=SystemClock(),
        tracer=tracer,
        _server=MetricsServerAdapter(logger=resolved_logger),
        _publisher=MetricsPublisherAdapter(logger=resolved_logger),
    )


def refresh_control_plane_integrity_metrics(
    settings: Settings, *, logger: LoggerPort | None = None
) -> None:
    """Measure persisted manifest/ledger integrity before a terminal snapshot."""
    try:
        if not settings.observability.metrics_enabled:
            return
        ControlPlaneIntegrityMetricsService(
            manifest_port=FileRunManifestStore(
                base_path=control_plane_root(settings, "run_manifest")
            ),
            ledger_port=FileRunLedgerStore(
                base_path=control_plane_root(settings, "run_ledger")
            ),
            metrics=PrometheusMetrics(),
        ).refresh()
    except (
        BioETLError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        AttributeError,
    ) as exc:
        if logger is not None:
            logger.warning(
                "integrity_metrics_refresh_failed", error_type=type(exc).__name__
            )


def bootstrap_metrics_service(
    *,
    logger: LoggerPort | None = None,
) -> MetricsService:
    """Bootstrap metrics service for administrative operations.

    Creates a MetricsService with infrastructure dependencies injected.
    Used by CLI and other interfaces for metrics server management.

    Returns:
        MetricsService instance ready for use.

    """
    settings = get_settings()
    tracer = resolve_tracing_port(
        tracer=None,
        settings=settings,
        service_name="bioetl.metrics_admin",
    )
    return create_metrics_service(logger=logger, tracer=tracer)


EntityDocument = dict[str, object]

_CANONICAL_TARGET_ENTITY = "entities/chembl/target.yaml"


def _entity_document(path: Path) -> EntityDocument:
    value = yaml.safe_load(path.read_bytes())
    if not isinstance(value, dict) or not isinstance(value.get("pipeline"), dict):
        raise ValueError("migration configuration must be a complete entity YAML")
    return cast(EntityDocument, value)


def _without_classification(document: EntityDocument) -> EntityDocument:
    value = deepcopy(document)
    pipeline = cast(EntityDocument, value["pipeline"])
    pipeline.pop("target_classification", None)
    return value


def _require_enrich_v31(pipeline: EntityDocument) -> TargetClassificationYamlConfig:
    classification = TargetClassificationYamlConfig.model_validate(
        pipeline.get("target_classification")
    )
    if classification.mode != "enrich":
        raise ValueError("deployment configuration must select enrich")
    if classification.to_domain().contract_version != "3.1.0":
        raise ValueError(
            "target candidate migration writes physical contract 3.1.0 only; "
            "3.2.0 requires a later migration"
        )
    return classification


def bind_target_deployment(
    paths: TargetMigrationPaths,
    *,
    settings: Settings | None = None,
    configs_root: Path | None = None,
) -> TargetDeploymentBinding:
    """Permit a classification-only change at the canonical entity path."""
    checked = paths.checked()
    root = resolve_configs_root(configs_root).resolve()
    canonical = (root / _CANONICAL_TARGET_ENTITY).resolve()
    if checked["config"] != canonical or paths.workspace.resolve() != root.parent:
        raise ValueError("migration workspace/config must match the active config root")
    original = _entity_document(canonical)
    deployment = _entity_document(checked["candidate_config"])
    if _without_classification(original) != _without_classification(deployment):
        raise ValueError("deployment YAML may change only target_classification")
    pipeline = cast(EntityDocument, deployment["pipeline"])
    classification = _require_enrich_v31(pipeline)
    baseline = load_pipeline_config_uncached("chembl_target", configs_root=root)
    future = baseline.model_copy(update={"target_classification": classification})
    future = resolve_target_classification_profile(future).resolved_yaml_config
    profile = load_target_runtime_profile(future, dependency_root=paths.workspace)
    if profile is None:
        raise ValueError("deployment has no admitted profile")
    active_settings = settings or get_settings()
    silver, gold = resolve_target_table_paths(active_settings, future)
    if (silver.resolve(), gold.resolve()) != (checked["silver"], checked["gold"]):
        raise ValueError("deployment resolves different physical target destinations")
    assay = load_pipeline_config_uncached("chembl_assay", configs_root=root)
    assay_gold = resolve_target_table_paths(active_settings, assay)[1].resolve()
    if assay_gold != checked["assay"]:
        raise ValueError("deployment resolves a different physical assay destination")
    settings_digest = sha256_bytes(
        canonical_json_bytes(
            {
                "data_dir": str(active_settings.data_dir.resolve()),
                "configs_root": str(root),
                "silver": str(silver.resolve()),
                "gold": str(gold.resolve()),
                "assay": str(assay_gold),
            }
        )
    )
    return TargetDeploymentBinding(
        str(canonical),
        sha256_file(canonical),
        sha256_file(checked["candidate_config"]),
        str(silver.resolve()),
        str(gold.resolve()),
        profile.profile_sha256,
        settings_digest,
    )


def _rehearsal_locations(
    paths: TargetMigrationPaths,
    rehearsal_root: Path,
    configs_root: Path,
    settings: Settings,
    active_configs_root: Path | None,
) -> tuple[dict[str, Path], Path, Path]:
    checked = paths.checked()
    active = resolve_configs_root(active_configs_root).resolve()
    if paths.workspace.resolve() != active.parent:
        raise ValueError(
            "rehearsal workspace must match the active repository/config root"
        )
    root = validate_rehearsal_paths(
        checked, workspace=paths.workspace, rehearsal_root=rehearsal_root
    )
    copied = resolve_configs_root(configs_root).resolve()
    if not copied.is_relative_to(root) or checked["config"] != (
        copied / _CANONICAL_TARGET_ENTITY
    ):
        raise ValueError("rehearsal must load its copied configs tree")
    canonical = active / _CANONICAL_TARGET_ENTITY
    if sha256_file(canonical) != sha256_file(checked["config"]):
        raise ValueError(
            "rehearsal old configuration must equal the active canonical bytes"
        )
    if not settings.test_mode or not settings.data_dir.resolve().is_relative_to(root):
        raise ValueError(
            "rehearsal requires explicit isolated test_mode storage settings"
        )
    return checked, copied, active


def _rehearsal_future(
    checked: dict[str, Path], configs_root: Path
) -> PipelineYamlConfig:
    original = _entity_document(checked["config"])
    deployment = _entity_document(checked["candidate_config"])
    if _without_classification(original) != _without_classification(deployment):
        raise ValueError("deployment YAML may change only target_classification")
    pipeline = cast(EntityDocument, deployment["pipeline"])
    classification = _require_enrich_v31(pipeline)
    baseline = load_pipeline_config_uncached("chembl_target", configs_root=configs_root)
    future = baseline.model_copy(update={"target_classification": classification})
    return resolve_target_classification_profile(future).resolved_yaml_config


def _protect_active_resources(
    checked: dict[str, Path], active_configs_root: Path
) -> None:
    settings = get_settings()
    target = load_pipeline_config_uncached(
        "chembl_target", configs_root=active_configs_root
    )
    assay = load_pipeline_config_uncached(
        "chembl_assay", configs_root=active_configs_root
    )
    protected = tuple(
        path.resolve()
        for path in (
            active_configs_root / _CANONICAL_TARGET_ENTITY,
            *resolve_target_table_paths(settings, target),
            resolve_target_table_paths(settings, assay)[1],
        )
    )
    for path in checked.values():
        if any(
            path == item or path.is_relative_to(item) or item.is_relative_to(path)
            for item in protected
        ):
            raise ValueError(
                "rehearsal resources overlap active canonical data/configuration"
            )


def bind_target_rehearsal(
    paths: TargetMigrationPaths,
    *,
    rehearsal_root: Path,
    configs_root: Path,
    settings: Settings,
    active_configs_root: Path | None = None,
) -> TargetDeploymentBinding:
    """Bind an isolated rehearsal through the real loader and admission."""
    checked, copied, active = _rehearsal_locations(
        paths, rehearsal_root, configs_root, settings, active_configs_root
    )
    _protect_active_resources(checked, active)
    future = _rehearsal_future(checked, copied)
    profile = load_target_runtime_profile(future, dependency_root=paths.workspace)
    if profile is None:
        raise ValueError("rehearsal has no admitted profile")
    silver, gold = resolve_target_table_paths(settings, future)
    if (silver.resolve(), gold.resolve()) != (checked["silver"], checked["gold"]):
        raise ValueError("rehearsal resolves different physical target destinations")
    settings_digest = sha256_bytes(
        canonical_json_bytes(
            {
                "data_dir": str(settings.data_dir.resolve()),
                "configs_root": str(copied),
                "silver": str(silver.resolve()),
                "gold": str(gold.resolve()),
                "role": "rehearsal",
                "rehearsal_root": str(rehearsal_root.resolve()),
                "approved_workspace": str(paths.workspace.resolve()),
            }
        )
    )
    return TargetDeploymentBinding(
        str(checked["config"]),
        sha256_file(checked["config"]),
        sha256_file(checked["candidate_config"]),
        str(silver.resolve()),
        str(gold.resolve()),
        profile.profile_sha256,
        settings_digest,
        role="rehearsal",
        rehearsal_root=str(rehearsal_root.resolve()),
        approved_workspace=str(paths.workspace.resolve()),
    )
