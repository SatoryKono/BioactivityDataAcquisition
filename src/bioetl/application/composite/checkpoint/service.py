"""Composite checkpoint workflow facade."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.ports import (
        CompositeCheckpointPort,
        LoggerPort,
        MetricsPort,
        RunLedgerPort,
    )


class CompositeCheckpointService:
    """Thin facade for composite checkpoint persistence workflows."""

    _DEFAULT_STALE_THRESHOLD_HOURS: float = 24.0
    _expected_checkpoint_context: ExpectedCheckpointContext

    def __init__(
        self,
        composite_name: str,
        run_id: str,
        storage: CompositeCheckpointPort,
        logger: LoggerPort,
        resume: bool = False,
        stale_checkpoint_threshold_hours: float | None = None,
        expected_effective_config_hash: str | None = None,
        expected_contract_ref: str | None = None,
        expected_contract_version: str | None = None,
        expected_manifest_id: str | None = None,
        run_ledger_port: RunLedgerPort | None = None,
        metrics: MetricsPort | None = None,
        load_service_factory: Callable[
            ..., CompositeCheckpointLoadService
        ] = CompositeCheckpointLoadService,
        persistence_service_factory: Callable[
            ..., CompositeCheckpointPersistenceService
        ] = CompositeCheckpointPersistenceService,
    ) -> None:
        self._composite_name = composite_name
        self._run_id = run_id
        self._storage = storage
        self._logger = logger
        self._resume = resume
        self._stale_threshold_hours = (
            stale_checkpoint_threshold_hours
            if stale_checkpoint_threshold_hours is not None
            else self._DEFAULT_STALE_THRESHOLD_HOURS
        )
        self._expected_checkpoint_context = create_expected_checkpoint_context(
            effective_config_hash=expected_effective_config_hash,
            contract_ref=expected_contract_ref,
            contract_version=expected_contract_version,
            manifest_id=expected_manifest_id,
            composite_run_identity=run_id,
        )
        self._checkpoint_filename = self._make_filename(run_id)
        self._glob_pattern_value = self._glob_pattern()
        self._load_service = load_service_factory(
            composite_name=composite_name,
            run_id=run_id,
            storage=storage,
            logger=logger,
            resume=resume,
            stale_threshold_hours=self._stale_threshold_hours,
            expected_context=self._expected_checkpoint_context,
            checkpoint_filename=self._checkpoint_filename,
            glob_pattern=self._glob_pattern_value,
            run_ledger_port=run_ledger_port,
            metrics=metrics,
        )
        self._persistence_service = persistence_service_factory(
            composite_name=composite_name,
            checkpoint_filename=self._checkpoint_filename,
            glob_pattern=self._glob_pattern_value,
            storage=storage,
            logger=logger,
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


import warnings


class CompositeCheckpointManager(CompositeCheckpointService):
    def __init__(self, *args, **kwargs):
        message = (
            "CompositeCheckpointManager is deprecated and will be removed in v2.0. "
            "Use CompositeCheckpointService instead."
        )
        warnings.warn(message, DeprecationWarning, stacklevel=3)
        super().__init__(*args, **kwargs)
