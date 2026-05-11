"""Runtime-management builders for composite runtime composition."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.application.composite.runtime_wiring_api import (
    CompositeCheckpointServiceContext,
    FSMStateHelperService,
)
from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_composite_checkpoint_writer,
    bootstrap_quarantine_adapter,
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
    from bioetl.domain.ports import (
        ClockPort,
        CompositeCheckpointPort,
        LoggerPort,
        MetricsPort,
    )
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
    checkpoint_storage = bootstrap_composite_checkpoint_writer()
    checkpoint_manager = _create_checkpoint_manager(
        config=config,
        runtime=runtime,
        control_plane_bundle=control_plane_bundle,
        logger=logger,
        run_id=run_id,
        checkpoint_storage=checkpoint_storage,
        checkpoint_manager_cls=checkpoint_manager_cls,
        checkpoint_clock=infra_context.clock,
    )
    quarantine_port = (
        bootstrap_quarantine_adapter() if config.cross_validation.enabled else None
    )

    return RuntimeManagementServicesBundle(
        checkpoint_manager=checkpoint_manager,
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


def _create_checkpoint_manager(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    control_plane_bundle: CompositeControlPlaneBundle | None,
    logger: LoggerPort,
    run_id: str,
    checkpoint_storage: CompositeCheckpointPort,
    checkpoint_manager_cls: type[CompositeCheckpointService],
    checkpoint_clock: ClockPort | None,
) -> CompositeCheckpointService:
    expected_manifest_id = (
        None if control_plane_bundle is None else control_plane_bundle.manifest_id
    )
    expected_execution_fingerprint = (
        None
        if control_plane_bundle is None
        else control_plane_bundle.execution_fingerprint
    )
    expected_dq_contract_compatibility_hash = (
        None
        if control_plane_bundle is None
        else control_plane_bundle.dq_contract_compatibility_hash
    )
    expected_input_snapshot_fingerprint = (
        None
        if control_plane_bundle is None
        else getattr(control_plane_bundle, "input_snapshot_fingerprint", None)
    )
    expected_effective_config_artifact_id = (
        None
        if control_plane_bundle is None
        else control_plane_bundle.effective_config_artifact_id
    )
    run_ledger_port = (
        None
        if control_plane_bundle is None
        or control_plane_bundle.run_ledger_service is None
        else control_plane_bundle.run_ledger_service.ledger_port
    )
    expected_effective_config_hash = _resolve_expected_effective_config_hash(
        config=config,
        control_plane_bundle=control_plane_bundle,
    )
    expected_contract_ref = normalize_contract_ref(config.name)
    expected_contract_version = normalize_contract_version(
        getattr(config, "version", "")
    )
    checkpoint_context = CompositeCheckpointServiceContext(
        composite_name=config.name,
        run_id=run_id,
        storage=checkpoint_storage,
        logger=logger,
        resume=runtime.resume,
        expected_effective_config_hash=expected_effective_config_hash,
        expected_contract_ref=expected_contract_ref,
        expected_contract_version=expected_contract_version,
        expected_manifest_id=expected_manifest_id,
        expected_execution_fingerprint=expected_execution_fingerprint,
        expected_dq_contract_compatibility_hash=(
            expected_dq_contract_compatibility_hash
        ),
        expected_effective_config_artifact_id=expected_effective_config_artifact_id,
        expected_input_snapshot_fingerprint=expected_input_snapshot_fingerprint,
        run_ledger_port=run_ledger_port,
        clock=checkpoint_clock,
    )
    return checkpoint_manager_cls(checkpoint_context)


def _resolve_expected_effective_config_hash(
    *,
    config: CompositeConfig,
    control_plane_bundle: CompositeControlPlaneBundle | None,
) -> str:
    """Resolve the effective-config hash used as a composite checkpoint anchor."""
    bundle_effective_hash = (
        None
        if control_plane_bundle is None
        else getattr(control_plane_bundle, "effective_config_hash", None)
    )
    if bundle_effective_hash:
        return str(bundle_effective_hash)
    to_dict = getattr(config, "to_dict", None)
    if not callable(to_dict):
        raise ValueError(
            "Composite runtime requires config.to_dict() to derive "
            "expected_effective_config_hash for checkpoint compatibility"
        )
    try:
        payload = to_dict()
    except (AttributeError, TypeError, ValueError):
        raise ValueError(
            "Composite runtime failed to serialize config for "
            "expected_effective_config_hash checkpoint anchor"
        ) from None
    if not isinstance(payload, dict):
        raise ValueError(
            "Composite runtime config serialization must return a mapping to "
            "derive expected_effective_config_hash"
        )
    try:
        config_hash = normalize_control_plane_sha256(
            compute_config_hash(cast(dict[str, object], payload))
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Composite runtime failed to compute expected_effective_config_hash "
            "from serialized config"
        ) from exc
    if not config_hash:
        raise ValueError(
            "Composite runtime produced an empty expected_effective_config_hash "
            "checkpoint anchor"
        )
    return config_hash


__all__ = ["build_runtime_management_services"]
