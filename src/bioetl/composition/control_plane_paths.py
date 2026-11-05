"""Writable control-plane path helpers and evidence-location binding."""

from __future__ import annotations

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
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    canonicalize_relative_data_root,
)
from bioetl.infrastructure.control_plane.evidence_location_path_safety import (
    assert_path_within_trusted_base,
)
from bioetl.infrastructure.control_plane.file_evidence_read_context import (
    FileEvidenceReadContext,
    validate_control_tree,
)
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.control_plane.file_run_ledger_store import FileRunLedgerStore
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
    LiveRootRecordResult,
    record_manifest_in_live_catalog,
)
from bioetl.infrastructure.control_plane.file_workflow_manifest_store import (
    FileWorkflowManifestStore,
)
from bioetl.infrastructure.control_plane.replay_object_verifier import (
    ReplayObjectVerifier,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "EvidenceLocationBindingContext",
    "FileEvidenceReadContextFactory",
    "LiveRootRecordResult",
    "build_evidence_location_binding_context",
    "control_plane_root",
    "publish_new_run_manifest_to_live_root",
    "relative_data_root_under_alias",
    "resolve_dashboard_data_alias_base",
    "resolve_data_root",
    "resolve_registration_runtime_source_id",
]


def publish_new_run_manifest_to_live_root(
    *,
    manifest: RunManifest,
    settings: Settings,
    source_base: Path,
) -> LiveRootRecordResult:
    """Record one new manifest in the dashboard live root.

    When ``dashboard_data_root`` differs from the run data root, the manifest,
    its run-id index, and its own contract-evidence sidecar are recorded under
    ``{dashboard_data_root}/output/control/run_manifest``. Historical trees are
    not walked. An unset alias, or the same directory, keeps the run data root
    as the only catalog.
    """
    alias = resolve_dashboard_data_alias_base(settings=settings)
    data_root = alias if alias is not None else resolve_data_root(settings)
    live_base = Path(data_root) / "output" / "control" / "run_manifest"
    return record_manifest_in_live_catalog(
        manifest=manifest,
        live_base=live_base,
        source_base=source_base,
    )


def control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return resolve_data_root(settings) / "output" / "control" / leaf


@dataclass(frozen=True, slots=True)
class FileEvidenceReadContextFactory:
    """Open file-backed read ports under a trusted alias base (RF-003)."""

    metrics: MetricsPort | None = None

    def open(
        self,
        data_root: Path,
        *,
        trusted_alias_base: Path,
    ) -> FileEvidenceReadContext:
        """Validate containment, then bind standard control-plane file stores."""
        alias_base = Path(trusted_alias_base).resolve(strict=False)
        safe_root = assert_path_within_trusted_base(
            Path(data_root),
            trusted_base=alias_base,
            field_name="data_root",
        )
        validate_control_tree(safe_root, trusted_alias_base=alias_base)
        output_root = safe_root / "output" / "control"
        verifier = ReplayObjectVerifier(
            config_root=output_root / "effective_config",
            lock_root=output_root / "dependency_locks",
            bronze_root=safe_root / "output" / "bronze",
            trusted_base=alias_base,
        )
        return FileEvidenceReadContext(
            data_root=safe_root,
            trusted_alias_base=alias_base,
            manifest_port=FileRunManifestStore(
                base_path=output_root / "run_manifest",
                metrics=self.metrics,
                replay_object_verifier=verifier,
            ),
            ledger_port=FileRunLedgerStore(
                base_path=output_root / "run_ledger",
                metrics=self.metrics,
            ),
            workflow_manifest_port=FileWorkflowManifestStore(
                base_path=output_root / "workflow_manifest",
                metrics=self.metrics,
            ),
            lineage_port=FileLineageStore(
                base_path=output_root / "lineage",
                metrics=self.metrics,
            ),
            replay_object_verifier=verifier,
        )


@dataclass(frozen=True, slots=True)
class EvidenceLocationBindingContext:
    """Trusted write root + alias binding for one publisher call."""

    write_data_root: Path
    alias_base: Path
    root_alias: str
    relative_data_root: str
    runtime_source_id: str | None
    report_root: Path | None
    skip_reason: str | None = None

    @property
    def registration_allowed(self) -> bool:
        """False when the binding must not publish a ``dashboard_data`` locator."""
        return self.skip_reason is None and self.runtime_source_id is not None


def resolve_dashboard_data_alias_base(*, settings: Settings) -> Path | None:
    """Resolve the trusted ``dashboard_data`` alias base from typed Settings."""
    configured = getattr(settings, "dashboard_data_root", None)
    if configured is None:
        return None
    text = str(configured).strip()
    if not text:
        return None
    return Path(text).expanduser().resolve(strict=False)


def relative_data_root_under_alias(
    *, write_data_root: Path, alias_base: Path
) -> str | None:
    """Return the canonical relative write root, or None when it is outside alias."""
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


def resolve_registration_runtime_source_id(
    settings: Settings, *, repository_root: Path | None = None
) -> str | None:
    """Resolve the bind/runtime source digest at the composition edge."""
    configured = getattr(settings, "runtime_source_id", None)
    process_environment: dict[str, str] = {}
    if configured is not None and str(configured).strip():
        process_environment[RUNTIME_SOURCE_ID_ENV] = str(configured).strip()
    repository_environment = load_repository_source_environment(
        repository_root or _repository_root(),
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
    """Build alias/write binding; never remap a trusted alias to a foreign root."""
    write_root = resolve_data_root(settings).resolve(strict=False)
    configured_alias = resolve_dashboard_data_alias_base(settings=settings)
    report_root = getattr(settings, "report_root", None)
    runtime_source_id = resolve_registration_runtime_source_id(settings)

    if configured_alias is None:
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
