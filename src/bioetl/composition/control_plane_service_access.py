"""Narrow control-plane service-access seam for first-party interface callers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.composition._resource_management import (
    get_checkpoint_runtime_service as get_checkpoint_runtime_service,
)
from bioetl.composition._workflow_services import (
    get_workflow_execution_service as get_workflow_execution_service,
)
from bioetl.composition._workflow_services import (
    get_workflow_inspection_service as get_workflow_inspection_service,
)
from bioetl.composition._workflow_services import (
    get_workflow_runner_service as get_workflow_runner_service,
)
from bioetl.composition._workflow_services import (
    load_workflow_config as load_workflow_config,
)
from bioetl.composition.bootstrap.cli import (
    bootstrap_control_plane_lifecycle_store as bootstrap_control_plane_lifecycle_store,
)
from bioetl.composition.bootstrap.cli.run_manifest import (
    persist_historical_replay_closure_report as persist_historical_replay_closure_report,
)
from bioetl.composition.bootstrap.cli.run_manifest import (
    persist_historical_replay_universe_report as persist_historical_replay_universe_report,
)
from bioetl.composition.config_catalog import (
    list_configured_pipeline_names as list_configured_pipeline_names,
)

if TYPE_CHECKING:
    from bioetl.application.services.export_service import ExportService
    from bioetl.application.services.forensic_run_diff_service import (
        ForensicRunDiffService,
    )
    from bioetl.application.services.historical_replay_closure_service import (
        HistoricalReplayClosureService,
    )
    from bioetl.application.services.historical_replay_corpus_service import (
        HistoricalReplayCorpusService,
    )
    from bioetl.application.services.historical_replay_universe_service import (
        HistoricalReplayUniverseService,
    )
    from bioetl.application.services.lineage_service import LineageService
    from bioetl.application.services.lock_service import LockService
    from bioetl.application.services.run_manifest_service import RunManifestService


def _services_owner() -> Any:
    """Resolve `_services` lazily so tests can patch its bootstrap seams."""
    from bioetl.composition import _services

    return _services


def get_export_service() -> ExportService:
    """Get Delta export service."""
    services = _services_owner()
    services._ensure_provider_registrations()
    return cast("ExportService", services._invoke_bootstrap("bootstrap_export_service"))


def get_lock_service() -> LockService:
    """Get administrative lock service."""
    services = _services_owner()
    services._ensure_provider_registrations()
    return cast("LockService", services._invoke_bootstrap("bootstrap_lock_service"))


def get_historical_replay_corpus_service() -> HistoricalReplayCorpusService:
    """Get historical replay corpus service."""
    services = _services_owner()
    services._ensure_provider_registrations()
    return cast(
        "HistoricalReplayCorpusService",
        services._invoke_bootstrap("bootstrap_historical_replay_corpus_service"),
    )


def get_historical_replay_universe_service() -> HistoricalReplayUniverseService:
    """Get historical replay universe service."""
    services = _services_owner()
    services._ensure_provider_registrations()
    return cast(
        "HistoricalReplayUniverseService",
        services._invoke_bootstrap("bootstrap_historical_replay_universe_service"),
    )


def get_historical_replay_closure_service() -> HistoricalReplayClosureService:
    """Get historical replay closure service."""
    services = _services_owner()
    services._ensure_provider_registrations()
    return cast(
        "HistoricalReplayClosureService",
        services._invoke_bootstrap("bootstrap_historical_replay_closure_service"),
    )


def get_forensic_run_diff_service() -> ForensicRunDiffService:
    """Get forensic run diff service."""
    services = _services_owner()
    services._ensure_provider_registrations()
    return cast(
        "ForensicRunDiffService",
        services._invoke_bootstrap("bootstrap_forensic_run_diff_service"),
    )


def get_run_manifest_service() -> RunManifestService:
    """Get run-manifest service without full pipeline registration."""
    services = _services_owner()
    services._ensure_provider_registrations()
    return cast(
        "RunManifestService",
        services._invoke_bootstrap("bootstrap_run_manifest_service"),
    )


def get_lineage_service() -> LineageService:
    """Get lineage service."""
    services = _services_owner()
    services._ensure_provider_registrations()
    return cast("LineageService", services._invoke_bootstrap("bootstrap_lineage_service"))


def get_config_service() -> object:
    """Get application configuration service."""
    services = _services_owner()
    services._ensure_provider_registrations()
    return services._invoke_bootstrap("bootstrap_config_service")


def get_adr_service() -> object:
    """Get ADR management port."""
    services = _services_owner()
    services._ensure_provider_registrations()
    return services._invoke_bootstrap("bootstrap_adr_service")

__all__ = [
    "bootstrap_control_plane_lifecycle_store",
    "get_adr_service",
    "get_checkpoint_runtime_service",
    "get_config_service",
    "get_export_service",
    "get_forensic_run_diff_service",
    "get_historical_replay_closure_service",
    "get_historical_replay_corpus_service",
    "get_historical_replay_universe_service",
    "get_lineage_service",
    "get_lock_service",
    "get_run_manifest_service",
    "get_workflow_execution_service",
    "get_workflow_inspection_service",
    "get_workflow_runner_service",
    "list_configured_pipeline_names",
    "load_workflow_config",
    "persist_historical_replay_closure_report",
    "persist_historical_replay_universe_report",
]
