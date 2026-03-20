"""Runtime-management builders for composite runtime composition."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_composite_checkpoint_port,
    bootstrap_quarantine_port,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_bundles import (
    RuntimeManagementServicesBundle,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.composite.checkpoint import CompositeCheckpointService
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import CompositeCheckpointPort, LoggerPort
    from bioetl.infrastructure.config import Settings


def build_runtime_management_services(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    settings: Settings,
    logger: LoggerPort,
    run_id: str,
    checkpoint_manager_cls: type[CompositeCheckpointService],
    create_dq_report_service: Callable[[LoggerPort, Settings], DQReportService],
) -> RuntimeManagementServicesBundle:
    """Build checkpoint, FSM, DQ, and quarantine runtime services."""
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
        ),
        dq_report_service=create_dq_report_service(logger, settings),
        fsm_state_helper=FSMStateHelperService(
            config=config,
            logger=logger,
            run_id=run_id,
        ),
        quarantine_port=quarantine_port,
    )


__all__ = ["build_runtime_management_services"]
