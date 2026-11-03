"""Narrow control-plane service-access seam for first-party interface callers."""

from __future__ import annotations

from bioetl.composition._resource_management import (
    get_checkpoint_runtime_service as get_checkpoint_runtime_service,
)
from bioetl.composition._services import get_adr_service as get_adr_service
from bioetl.composition._services import (
    get_bronze_cleanup_service as get_bronze_cleanup_service,
)
from bioetl.composition._services import get_config_service as get_config_service
from bioetl.composition._services import get_export_service as get_export_service
from bioetl.composition._services import (
    get_forensic_run_diff_service as get_forensic_run_diff_service,
)
from bioetl.composition._services import (
    get_historical_replay_closure_service as get_historical_replay_closure_service,
)
from bioetl.composition._services import (
    get_historical_replay_corpus_service as get_historical_replay_corpus_service,
)
from bioetl.composition._services import (
    get_historical_replay_universe_service as get_historical_replay_universe_service,
)
from bioetl.composition._services import get_lineage_service as get_lineage_service
from bioetl.composition._services import get_lock_service as get_lock_service
from bioetl.composition._services import (
    get_run_manifest_service as get_run_manifest_service,
)
from bioetl.composition.factories.services.workflow_services import (
    get_workflow_execution_service as get_workflow_execution_service,
)
from bioetl.composition.factories.services.workflow_services import (
    get_workflow_inspection_service as get_workflow_inspection_service,
)
from bioetl.composition.factories.services.workflow_services import (
    get_workflow_runner_service as get_workflow_runner_service,
)
from bioetl.composition.factories.services.workflow_services import (
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
from bioetl.composition.composite_catalog import (
    list_configured_pipeline_names as list_configured_pipeline_names,
)

__all__ = [
    "EvidenceLocationBindingContext",
    "bootstrap_control_plane_lifecycle_store",
    "build_evidence_location_binding_context",
    "get_adr_service",
    "get_bronze_cleanup_service",
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
    "relative_data_root_under_alias",
    "resolve_dashboard_data_alias_base",
    "resolve_registration_runtime_source_id",
]


from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.run_reports.source_identity import (
    RUNTIME_SOURCE_ID_ENV,
    resolve_runtime_source_identity,
)
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    load_repository_source_environment,
)
from bioetl.composition.runtime_builders.run_manifest_data_roots import (
    resolve_data_root,
)
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    canonicalize_relative_data_root,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings


@dataclass(frozen=True, slots=True)
class EvidenceLocationBindingContext:
    """Trusted write root + alias binding for one publisher call."""

    write_data_root: Path
    alias_base: Path
    root_alias: str
    relative_data_root: str
    runtime_source_id: str | None
    report_root: Path | None
    # Set when write root is outside an explicitly configured dashboard alias.
    skip_reason: str | None = None

    @property
    def registration_allowed(self) -> bool:
        """False when the binding must not publish a ``dashboard_data`` locator."""
        return self.skip_reason is None and self.runtime_source_id is not None


def resolve_dashboard_data_alias_base(*, settings: Settings) -> Path | None:
    """Resolve the trusted ``dashboard_data`` alias base from typed Settings.

    Returns ``BIOETL_DASHBOARD_DATA_ROOT`` when configured on Settings, else
    ``None`` so callers may treat the write root as the alias base.
    """
    configured = getattr(settings, "dashboard_data_root", None)
    if configured is None:
        return None
    text = str(configured).strip()
    if not text:
        return None
    return Path(text).expanduser().resolve(strict=False)


def relative_data_root_under_alias(
    *,
    write_data_root: Path,
    alias_base: Path,
) -> str | None:
    """Return posix relative path of write root under alias, or ``.``.

    Uses ``Path.relative_to`` against the DI/composition alias base — not
    parent-folder name heuristics. Returns ``None`` when write root is outside
    the alias base (caller must skip registration, never remap ``dashboard_data``).
    """
    write = Path(write_data_root).resolve(strict=False)
    base = Path(alias_base).resolve(strict=False)
    try:
        relative = write.relative_to(base)
    except ValueError:
        return None
    text = relative.as_posix()
    if text in {"", "."}:
        return "."
    return canonicalize_relative_data_root(text)


def _repository_root() -> Path:
    # composition → bioetl → src → repo root
    return Path(__file__).resolve().parents[3]


def resolve_registration_runtime_source_id(settings: Settings) -> str | None:
    """Resolve bind/runtime source digest for locators (composition edge).

    Precedence matches :func:`resolve_runtime_source_identity`: typed settings,
    then repository ``.env`` / ``.env.local``.
    """
    configured = getattr(settings, "runtime_source_id", None)
    process_environment: dict[str, str] = {}
    if configured is not None and str(configured).strip():
        process_environment[RUNTIME_SOURCE_ID_ENV] = str(configured).strip()
    repository_environment = load_repository_source_environment(
        _repository_root(),
        names=(RUNTIME_SOURCE_ID_ENV,),
        process_environment=process_environment,
    )
    resolution = resolve_runtime_source_identity(
        process_environment=process_environment,
        repository_environment=repository_environment,
    )
    if resolution.is_resolved and resolution.value is not None:
        return resolution.value
    return None


def build_evidence_location_binding_context(
    settings: Settings,
) -> EvidenceLocationBindingContext:
    """Build alias/write binding from settings + composition-edge env.

    Never remaps ``dashboard_data`` onto a foreign write root. When
    ``BIOETL_DASHBOARD_DATA_ROOT`` is set and the write root lies outside it,
    registration is skipped with diagnostics.
    """
    write_root = resolve_data_root(settings).resolve(strict=False)
    configured_alias = resolve_dashboard_data_alias_base(settings=settings)
    report_root = getattr(settings, "report_root", None)
    runtime_source_id = resolve_registration_runtime_source_id(settings)

    if configured_alias is None:
        # No explicit dashboard alias: write root IS the trusted base.
        return EvidenceLocationBindingContext(
            write_data_root=write_root,
            alias_base=write_root,
            root_alias=DEFAULT_EVIDENCE_ROOT_ALIAS,
            relative_data_root=".",
            runtime_source_id=runtime_source_id,
            report_root=Path(report_root) if report_root is not None else None,
        )

    relative = relative_data_root_under_alias(
        write_data_root=write_root,
        alias_base=configured_alias,
    )
    if relative is None:
        return EvidenceLocationBindingContext(
            write_data_root=write_root,
            alias_base=configured_alias,
            root_alias=DEFAULT_EVIDENCE_ROOT_ALIAS,
            relative_data_root=".",
            runtime_source_id=runtime_source_id,
            report_root=Path(report_root) if report_root is not None else None,
            skip_reason=(
                "write_data_root_outside_dashboard_data_alias; "
                "refusing to publish dashboard_data locator for foreign root"
            ),
        )
    return EvidenceLocationBindingContext(
        write_data_root=write_root,
        alias_base=configured_alias,
        root_alias=DEFAULT_EVIDENCE_ROOT_ALIAS,
        relative_data_root=relative,
        runtime_source_id=runtime_source_id,
        report_root=Path(report_root) if report_root is not None else None,
    )
