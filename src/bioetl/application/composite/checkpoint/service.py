"""Composite checkpoint workflow facade."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from bioetl.application.composite.checkpoint._anchor_context import (
    ExpectedCheckpointContext,
    create_expected_checkpoint_context,
)
from bioetl.application.composite.checkpoint.load_service import (
    CompositeCheckpointLoadService,
)
from bioetl.application.composite.checkpoint.persistence_service import (
    CompositeCheckpointPersistenceService,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.ports import (
    ClockPort,
    CompositeCheckpointPort,
    LoggerPort,
    MetricsPort,
    RunLedgerPort,
)


@dataclass(frozen=True, slots=True)
class CompositeCheckpointServiceContext:
    """Typed input bundle for ``CompositeCheckpointService`` construction."""

    composite_name: str
    run_id: str
    storage: CompositeCheckpointPort
    logger: LoggerPort
    resume: bool = False
    stale_checkpoint_threshold_hours: float | None = None
    expected_effective_config_hash: str | None = None
    expected_effective_config_artifact_id: str | None = None
    expected_execution_fingerprint: str | None = None
    expected_dq_contract_compatibility_hash: str | None = None
    expected_input_snapshot_fingerprint: str | None = None
    expected_contract_ref: str | None = None
    expected_contract_version: str | None = None
    expected_manifest_id: str | None = None
    run_ledger_port: RunLedgerPort | None = None
    metrics: MetricsPort | None = None
    clock: ClockPort | None = None
    load_service_factory: Callable[..., CompositeCheckpointLoadService] = (
        CompositeCheckpointLoadService
    )
    persistence_service_factory: Callable[
        ..., CompositeCheckpointPersistenceService
    ] = CompositeCheckpointPersistenceService


class CompositeCheckpointService:
    """Thin facade for composite checkpoint persistence workflows."""

    _DEFAULT_STALE_THRESHOLD_HOURS: float = 24.0
    _expected_checkpoint_context: ExpectedCheckpointContext
    _load_service: CompositeCheckpointLoadService
    _persistence_service: CompositeCheckpointPersistenceService

    def __init__(self, context: CompositeCheckpointServiceContext) -> None:
        params = context
        self._composite_name = params.composite_name
        self._run_id = params.run_id
        self._storage = params.storage
        self._logger = params.logger
        self._resume = params.resume
        self._stale_threshold_hours = (
            params.stale_checkpoint_threshold_hours
            if params.stale_checkpoint_threshold_hours is not None
            else self._DEFAULT_STALE_THRESHOLD_HOURS
        )
        self._expected_checkpoint_context = create_expected_checkpoint_context(
            effective_config_hash=params.expected_effective_config_hash,
            effective_config_artifact_id=params.expected_effective_config_artifact_id,
            execution_fingerprint=params.expected_execution_fingerprint,
            dq_contract_compatibility_hash=(
                params.expected_dq_contract_compatibility_hash
            ),
            input_snapshot_fingerprint=params.expected_input_snapshot_fingerprint,
            contract_ref=params.expected_contract_ref,
            contract_version=params.expected_contract_version,
            manifest_id=params.expected_manifest_id,
            composite_run_identity=params.run_id,
        )
        self._checkpoint_filename = self._make_filename(params.run_id)
        self._glob_pattern_value = self._glob_pattern()
        self._load_service = params.load_service_factory(
            composite_name=params.composite_name,
            run_id=params.run_id,
            storage=params.storage,
            logger=params.logger,
            resume=params.resume,
            stale_threshold_hours=self._stale_threshold_hours,
            expected_context=self._expected_checkpoint_context,
            checkpoint_filename=self._checkpoint_filename,
            glob_pattern=self._glob_pattern_value,
            run_ledger_port=params.run_ledger_port,
            metrics=params.metrics,
            clock=params.clock,
        )
        self._persistence_service = params.persistence_service_factory(
            composite_name=params.composite_name,
            checkpoint_filename=self._checkpoint_filename,
            glob_pattern=self._glob_pattern_value,
            storage=params.storage,
            logger=params.logger,
            metrics=params.metrics,
        )

    def _make_filename(self, run_id: str) -> str:
        return f"composite_{self._composite_name}_{run_id}.json"

    def _glob_pattern(self) -> str:
        return f"composite_{self._composite_name}_*.json"

    @property
    def expected_effective_config_hash(self) -> str:
        """Expose the configured effective-config anchor for dependent helpers."""
        return self._expected_checkpoint_context.effective_config_hash

    @property
    def expected_effective_config_artifact_id(self) -> str:
        """Expose the configured effective-config artifact anchor."""
        return self._expected_checkpoint_context.effective_config_artifact_id

    @property
    def expected_execution_fingerprint(self) -> str:
        """Expose the configured execution-fingerprint anchor."""
        return self._expected_checkpoint_context.execution_fingerprint

    @property
    def expected_dq_contract_compatibility_hash(self) -> str:
        """Expose the configured DQ compatibility anchor."""
        return self._expected_checkpoint_context.dq_contract_compatibility_hash

    @property
    def expected_input_snapshot_fingerprint(self) -> str:
        """Expose the configured input-snapshot fingerprint anchor."""
        return self._expected_checkpoint_context.input_snapshot_fingerprint

    @property
    def expected_contract_ref(self) -> str:
        """Expose the configured contract-ref anchor for dependent helpers."""
        return self._expected_checkpoint_context.contract_ref

    @property
    def expected_contract_version(self) -> str:
        """Expose the configured contract-version anchor for dependent helpers."""
        return self._expected_checkpoint_context.contract_version

    @property
    def expected_manifest_id(self) -> str:
        """Expose the configured manifest anchor for checkpoint correlation."""
        return self._expected_checkpoint_context.manifest_id

    async def load(self) -> CompositeCheckpointState:
        """Load checkpoint state or create a fresh one."""
        await asyncio.sleep(0)
        return self._load_service.load()

    async def save(self, state: CompositeCheckpointState) -> None:
        """Save checkpoint state to JSON atomically."""
        await asyncio.sleep(0)
        self._persistence_service.save(state)

    async def delete(self) -> None:
        """Delete checkpoint file after successful completion."""
        await asyncio.sleep(0)
        self._persistence_service.delete()

    async def delete_orphaned(self) -> int:
        """Delete orphaned checkpoint files from previous runs."""
        await asyncio.sleep(0)
        return self._persistence_service.delete_orphaned()

    async def list_all(self) -> list[str]:
        """List all checkpoints for this composite pipeline."""
        await asyncio.sleep(0)
        return self._persistence_service.list_all()
