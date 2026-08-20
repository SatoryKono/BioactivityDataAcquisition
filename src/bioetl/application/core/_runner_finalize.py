"""Terminal contract-evidence and debug-export finalizers for PipelineRunner."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.services.export_lineage.debug_export_service import (
    DebugExportResult,
)
from bioetl.domain.exceptions.base import BioETLError

if TYPE_CHECKING:
    from bioetl.application.core.batch_executor import BatchExecutor
    from bioetl.application.core.lifecycle.lock_runtime_service import (
        LockRuntimeService,
    )
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.domain.config import PipelineConfig
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import ContractEvidenceRecorderPort, LoggerPort

_RUN_FAILURE_EXCEPTIONS = (
    BioETLError,
    AssertionError,
    AttributeError,
    KeyError,
    LookupError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


class _RunnerFinalizeHost(Protocol):
    """Narrow runner surface consumed by terminal finalizers."""

    @property
    def manifest_id(self) -> str | None: ...

    @property
    def run_id(self) -> str: ...

    @property
    def _contract_evidence_recorder(self) -> ContractEvidenceRecorderPort | None: ...

    @property
    def _lock_runtime_service(self) -> LockRuntimeService: ...

    @property
    def _context(self) -> PipelineContext: ...

    @property
    def _executor(self) -> BatchExecutor: ...

    @property
    def _logger(self) -> LoggerPort: ...

    @property
    def _run_ledger_service(self) -> RunLedgerService | None: ...

    @property
    def _config(self) -> PipelineConfig: ...


def finalize_contract_evidence(runner: _RunnerFinalizeHost) -> None:
    """Write the immutable sidecar after lock acquire and before extract."""
    recorder = runner._contract_evidence_recorder
    manifest_id = runner.manifest_id
    if recorder is None or not manifest_id:
        return
    from bioetl.application.services.control_plane.manifest.contract_evidence import (
        build_runtime_contract_evidence,
    )

    get_context = runner._lock_runtime_service.get_context
    lock = get_context()
    lock_owner_id = None if lock is None else str(lock.owner_id)
    record = recorder.record
    record(
        manifest_id,
        build_runtime_contract_evidence(
            manifest_id=manifest_id,
            contract_ref=getattr(runner._context, "contract_ref", None),
            contract_schema_hash=getattr(runner._context, "contract_schema_hash", None),
            resume_requested=bool(getattr(runner._context, "resume", False)),
            lock_owner_id=lock_owner_id,
        ),
    )


async def finalize_debug_export(runner: _RunnerFinalizeHost, status: str) -> None:
    finalize = getattr(runner._executor, "finalize_debug_export", None)
    if not callable(finalize):
        return
    try:
        finalize_fn = cast(Callable[..., Awaitable[object]], finalize)
        result = await finalize_fn(status=status, manifest_id=runner.manifest_id)
    except _RUN_FAILURE_EXCEPTIONS as error:
        warning = runner._logger.warning
        warning(
            "debug_export_finalize_failed",
            error=str(error),
            error_type=type(error).__name__,
            run_id=str(runner._context.run_id),
        )
        return
    if not isinstance(result, DebugExportResult):
        return
    ledger = runner._run_ledger_service
    if ledger is not None:
        publish = ledger.record_artifact_published
        publish(
            layer="debug_export",
            artifact_path=result.root_path,
            artifact_content_hash=result.debug_export_hash,
            dataset_ref=f"debug_export:{runner._config.pipeline_name}@{runner.run_id}",
            details={
                "manifest_path": result.manifest_path,
                "debug_export_hash": result.debug_export_hash,
            },
        )
