"""Composition-edge wiring for RF-004 evidence-location registration.

Reads process env only at the composition boundary. Application services
receive absolute paths, alias bases, and runtime_source_id as parameters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.evidence_location.registration import (
    EvidenceLocationRegisterRequest,
    EvidenceLocationRegistrationOutcome,
    EvidenceLocationRegistrationService,
    EvidenceLocationVerifyOutcome,
)
from bioetl.application.services.run_reports.evidence_location_paths import (
    default_evidence_root_alias_registry,
)
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
    EvidenceLocationKind,
    canonicalize_relative_data_root,
)
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)

if TYPE_CHECKING:
    from bioetl.domain.control_plane.run_manifest import RunManifest
    from bioetl.domain.control_plane.workflow_manifest import WorkflowManifest
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "EvidenceLocationBindingContext",
    "build_evidence_location_binding_context",
    "build_evidence_location_registration_service",
    "register_pipeline_manifest_location",
    "register_workflow_manifest_location",
    "relative_data_root_under_alias",
    "resolve_dashboard_data_alias_base",
    "resolve_registration_runtime_source_id",
]

_DASHBOARD_DATA_ROOT_ENV = "BIOETL_DASHBOARD_DATA_ROOT"


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


def resolve_dashboard_data_alias_base(*, write_data_root: Path) -> Path | None:
    """Resolve the trusted ``dashboard_data`` alias base at composition edge.

    Returns the configured ``BIOETL_DASHBOARD_DATA_ROOT`` when set, otherwise
    ``None`` so callers may treat the write root as the alias base.
    """
    raw = os.environ.get(_DASHBOARD_DATA_ROOT_ENV, "").strip()
    if raw:
        return Path(raw).expanduser().resolve(strict=False)
    _ = write_data_root
    return None


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
    # runtime_builders → composition → bioetl → src → repo root
    return Path(__file__).resolve().parents[4]


def resolve_registration_runtime_source_id(settings: Settings) -> str | None:
    """Resolve bind/runtime source digest for locators (composition edge).

    Precedence matches :func:`resolve_runtime_source_identity`: typed settings /
    process env, then repository ``.env`` / ``.env.local``.
    """
    configured = getattr(settings, "runtime_source_id", None)
    process_environment: dict[str, str] = {}
    if configured is not None and str(configured).strip():
        process_environment[RUNTIME_SOURCE_ID_ENV] = str(configured).strip()
    else:
        env_value = os.environ.get(RUNTIME_SOURCE_ID_ENV, "").strip()
        if env_value:
            process_environment[RUNTIME_SOURCE_ID_ENV] = env_value
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
    configured_alias = resolve_dashboard_data_alias_base(write_data_root=write_root)
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


def build_evidence_location_registration_service(
    settings: Settings,
) -> tuple[EvidenceLocationRegistrationService, EvidenceLocationBindingContext]:
    """Construct file-backed registration service + binding context."""
    binding = build_evidence_location_binding_context(settings)
    # Alias registry always uses the trusted dashboard base (never remapped).
    default_evidence_root_alias_registry(dashboard_data_root=binding.alias_base)
    store = FileEvidenceLocationStore(
        report_root=binding.report_root
        if binding.report_root is not None
        else Path("reports") / "run-reports"
    )
    return EvidenceLocationRegistrationService(locations=store), binding


def _soft_skip(*, code: str, detail: str) -> EvidenceLocationRegistrationOutcome:
    return EvidenceLocationRegistrationOutcome(code=code, detail=detail)


def _guard_registration_binding(
    binding: EvidenceLocationBindingContext,
) -> EvidenceLocationRegistrationOutcome | None:
    if binding.skip_reason is not None:
        return _soft_skip(
            code="skipped_write_root_outside_alias",
            detail=binding.skip_reason,
        )
    if binding.runtime_source_id is None:
        return _soft_skip(
            code="skipped_missing_runtime_source_id",
            detail="runtime_source_id unresolved; locator not published",
        )
    return None


def register_pipeline_manifest_location(
    *,
    manifest: RunManifest,
    settings: Settings,
) -> EvidenceLocationRegistrationOutcome:
    """Best-effort register after a pipeline manifest was persisted."""
    service, binding = build_evidence_location_registration_service(settings)
    skipped = _guard_registration_binding(binding)
    if skipped is not None:
        return skipped
    assert binding.runtime_source_id is not None
    workflow_run_id = getattr(manifest, "workflow_run_id", None)
    return service.register_pipeline_run(
        pipeline_name=str(manifest.pipeline_name),
        run_id=str(manifest.run_id),
        runtime_source_id=binding.runtime_source_id,
        relative_data_root=binding.relative_data_root,
        root_alias=binding.root_alias,
        workflow_run_id=str(workflow_run_id) if workflow_run_id else None,
    )


def register_workflow_manifest_location(
    *,
    manifest: WorkflowManifest,
    settings: Settings,
) -> EvidenceLocationRegistrationOutcome:
    """Best-effort register after a workflow parent manifest was persisted."""
    service, binding = build_evidence_location_registration_service(settings)
    skipped = _guard_registration_binding(binding)
    if skipped is not None:
        return skipped
    assert binding.runtime_source_id is not None
    return service.register_workflow_run(
        workflow_name=str(manifest.workflow_name),
        workflow_run_id=str(manifest.workflow_run_id),
        runtime_source_id=binding.runtime_source_id,
        relative_data_root=binding.relative_data_root,
        root_alias=binding.root_alias,
    )


def build_evidence_location_binding_service(
    settings: Settings,
) -> tuple[EvidenceLocationRegistrationService, EvidenceLocationBindingContext]:
    """Alias for :func:`build_evidence_location_registration_service`."""
    return build_evidence_location_registration_service(settings)


def _verify_bound_location(
    *,
    settings: Settings,
    kind: EvidenceLocationKind,
    owner: str,
    run_id: str,
    workflow_run_id: str | None,
) -> EvidenceLocationVerifyOutcome | None:
    """Finalize-time verify shared by pipeline and workflow callers."""
    service, binding = build_evidence_location_registration_service(settings)
    if binding.skip_reason is not None or binding.runtime_source_id is None:
        return None
    return service.record_verify_observation(
        EvidenceLocationRegisterRequest(
            kind=kind,
            owner=owner,
            run_id=run_id,
            runtime_source_id=binding.runtime_source_id,
            relative_data_root=binding.relative_data_root,
            root_alias=binding.root_alias,
            workflow_run_id=workflow_run_id,
        )
    )


def verify_pipeline_run_location(
    *,
    pipeline_name: str,
    run_id: str,
    workflow_run_id: str | None,
    settings: Settings,
) -> EvidenceLocationVerifyOutcome | None:
    """Finalize-time verify; returns None when binding cannot be published."""
    return _verify_bound_location(
        settings=settings,
        kind=EvidenceLocationKind.PIPELINE,
        owner=pipeline_name,
        run_id=run_id,
        workflow_run_id=workflow_run_id,
    )


def verify_workflow_run_location(
    *,
    workflow_name: str,
    workflow_run_id: str,
    settings: Settings,
) -> EvidenceLocationVerifyOutcome | None:
    """Finalize-time verify for a workflow parent locator."""
    return _verify_bound_location(
        settings=settings,
        kind=EvidenceLocationKind.WORKFLOW,
        owner=workflow_name,
        run_id=workflow_run_id,
        workflow_run_id=None,
    )
