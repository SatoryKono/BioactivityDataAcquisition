"""Runtime-management builders for composite runtime composition."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.composite.runtime_wiring_api import FSMStateHelperService
from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_composite_checkpoint_port,
    bootstrap_quarantine_port,
)
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
    CompositeControlPlaneBundle,
    RuntimeManagementServicesBundle,
)
from bioetl.composition.services.versioning import compute_config_hash
from bioetl.domain.normalization import (
    normalize_contract_ref,
    normalize_contract_version,
    normalize_control_plane_sha256,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.composite.runtime_wiring_api import (
        CompositeCheckpointService,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import CompositeCheckpointPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.config import Settings


def build_runtime_management_services(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    settings: Settings,
    logger: LoggerPort,
    run_id: str,
    checkpoint_manager_cls: type[CompositeCheckpointService],
    create_dq_report_service: Callable[
        [LoggerPort, Settings, MetricsPort],
        DQReportService,
    ],
    control_plane_bundle: CompositeControlPlaneBundle | None = None,
) -> RuntimeManagementServicesBundle:
    """Build checkpoint, FSM, DQ, and quarantine runtime services."""

    expected_effective_config_hash = _resolve_expected_effective_config_hash(config)
    checkpoint_storage: CompositeCheckpointPort = bootstrap_composite_checkpoint_port()
    quarantine_port = (
        bootstrap_quarantine_port() if config.cross_validation.enabled else None
    )
    return RuntimeManagementServicesBundle(
        checkpoint_manager=checkpoint_manager_cls(
            composite_name=config.name,
            run_id=run_id,
            storage=checkpoint_storage,
            logger=logger,
            resume=runtime.resume,
            expected_effective_config_hash=expected_effective_config_hash,
            expected_contract_ref=normalize_contract_ref(config.name),
            expected_contract_version=normalize_contract_version(
                getattr(config, "version", "")
            ),
            expected_manifest_id=(
                None
                if control_plane_bundle is None
                else control_plane_bundle.manifest_id
            ),
            expected_execution_fingerprint=(
                None
                if control_plane_bundle is None
                else control_plane_bundle.execution_fingerprint
            ),
            expected_dq_contract_compatibility_hash=(
                None
                if control_plane_bundle is None
                else control_plane_bundle.dq_contract_compatibility_hash
            ),
            expected_effective_config_artifact_id=(
                None
                if control_plane_bundle is None
                else control_plane_bundle.effective_config_artifact_id
            ),
            run_ledger_port=(
                None
                if control_plane_bundle is None
                or control_plane_bundle.run_ledger_service is None
                else control_plane_bundle.run_ledger_service.ledger_port
            ),
        ),
        dq_report_service=create_dq_report_service(
            logger,
            settings,
            infra_context.metrics,
        ),
        fsm_state_helper=FSMStateHelperService(
            config=config,
            logger=logger,
            run_id=run_id,
        ),
        quarantine_port=quarantine_port,
    )


def _resolve_expected_effective_config_hash(config: CompositeConfig) -> str:
    """Best-effort hash for checkpoint compatibility anchors."""
    to_dict = getattr(config, "to_dict", None)
    if not callable(to_dict):
        return ""
    try:
        payload = to_dict()
    except (AttributeError, TypeError, ValueError):
        return ""
    if not isinstance(payload, dict):
        return ""
    try:
        return (
            normalize_control_plane_sha256(
                compute_config_hash(cast(dict[str, object], payload))
            )
            or ""
        )
    except (TypeError, ValueError):
        return ""


__all__ = ["build_runtime_management_services"]
