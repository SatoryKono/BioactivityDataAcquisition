"""Composite checkpoint workflow facade."""

from __future__ import annotations

import asyncio
import warnings
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class CompositeCheckpointServiceInit:
    """Typed input bundle for ``CompositeCheckpointService`` construction."""

    composite_name: str
    run_id: str
    storage: CompositeCheckpointPort
    logger: LoggerPort
    resume: bool = False
    stale_checkpoint_threshold_hours: float | None = None
    expected_effective_config_hash: str | None = None
    expected_contract_ref: str | None = None
    expected_contract_version: str | None = None
    expected_manifest_id: str | None = None
    run_ledger_port: RunLedgerPort | None = None
    metrics: MetricsPort | None = None
    load_service_factory: Callable[
        ..., CompositeCheckpointLoadService
    ] = CompositeCheckpointLoadService
    persistence_service_factory: Callable[
        ..., CompositeCheckpointPersistenceService
    ] = CompositeCheckpointPersistenceService


_CHECKPOINT_INIT_REQUIRED_FIELDS = ("composite_name", "run_id", "storage", "logger")
_CHECKPOINT_INIT_OPTIONAL_DEFAULTS: dict[str, object] = {
    "resume": False,
    "stale_checkpoint_threshold_hours": None,
    "expected_effective_config_hash": None,
    "expected_contract_ref": None,
    "expected_contract_version": None,
    "expected_manifest_id": None,
    "run_ledger_port": None,
    "metrics": None,
    "load_service_factory": CompositeCheckpointLoadService,
    "persistence_service_factory": CompositeCheckpointPersistenceService,
}


def _resolve_checkpoint_init_value(
    *,
    field_name: str,
    init: CompositeCheckpointServiceInit | None,
    overrides: dict[str, object],
) -> object:
    if field_name in overrides:
        return overrides[field_name]
    if field_name in _CHECKPOINT_INIT_OPTIONAL_DEFAULTS and init is None:
        return _CHECKPOINT_INIT_OPTIONAL_DEFAULTS[field_name]
    if init is None:
        raise TypeError(
            "CompositeCheckpointService() missing required argument: "
            f"'{field_name}'"
        )
    return getattr(init, field_name)


def _coerce_checkpoint_service_init(
    init: CompositeCheckpointServiceInit | None,
    overrides: dict[str, object],
) -> CompositeCheckpointServiceInit:
    for field_name in _CHECKPOINT_INIT_REQUIRED_FIELDS:
        _resolve_checkpoint_init_value(
            field_name=field_name,
            init=init,
            overrides=overrides,
        )
    return CompositeCheckpointServiceInit(
        composite_name=_resolve_checkpoint_init_value(
            field_name="composite_name",
            init=init,
            overrides=overrides,
        ),
        run_id=_resolve_checkpoint_init_value(
            field_name="run_id",
            init=init,
            overrides=overrides,
        ),
        storage=_resolve_checkpoint_init_value(
            field_name="storage",
            init=init,
            overrides=overrides,
        ),
        logger=_resolve_checkpoint_init_value(
            field_name="logger",
            init=init,
            overrides=overrides,
        ),
        resume=_resolve_checkpoint_init_value(
            field_name="resume",
            init=init,
            overrides=overrides,
        ),
        stale_checkpoint_threshold_hours=_resolve_checkpoint_init_value(
            field_name="stale_checkpoint_threshold_hours",
            init=init,
            overrides=overrides,
        ),
        expected_effective_config_hash=_resolve_checkpoint_init_value(
            field_name="expected_effective_config_hash",
            init=init,
            overrides=overrides,
        ),
        expected_contract_ref=_resolve_checkpoint_init_value(
            field_name="expected_contract_ref",
            init=init,
            overrides=overrides,
        ),
        expected_contract_version=_resolve_checkpoint_init_value(
            field_name="expected_contract_version",
            init=init,
            overrides=overrides,
        ),
        expected_manifest_id=_resolve_checkpoint_init_value(
            field_name="expected_manifest_id",
            init=init,
            overrides=overrides,
        ),
        run_ledger_port=_resolve_checkpoint_init_value(
            field_name="run_ledger_port",
            init=init,
            overrides=overrides,
        ),
        metrics=_resolve_checkpoint_init_value(
            field_name="metrics",
            init=init,
            overrides=overrides,
        ),
        load_service_factory=_resolve_checkpoint_init_value(
            field_name="load_service_factory",
            init=init,
            overrides=overrides,
        ),
        persistence_service_factory=_resolve_checkpoint_init_value(
            field_name="persistence_service_factory",
            init=init,
            overrides=overrides,
        ),
    )


class CompositeCheckpointService:
    """Thin facade for composite checkpoint persistence workflows."""

    _DEFAULT_STALE_THRESHOLD_HOURS: float = 24.0
    _expected_checkpoint_context: ExpectedCheckpointContext

    def __init__(
        self,
        init: CompositeCheckpointServiceInit | None = None,
        **overrides: object,
    ) -> None:
        params = _coerce_checkpoint_service_init(init, overrides)
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
        )
        self._persistence_service = params.persistence_service_factory(
            composite_name=params.composite_name,
            checkpoint_filename=self._checkpoint_filename,
            glob_pattern=self._glob_pattern_value,
            storage=params.storage,
            logger=params.logger,
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


class CompositeCheckpointManager(CompositeCheckpointService):
    def __init__(self, *args, **kwargs):
        message = (
            "CompositeCheckpointManager is deprecated and will be removed in v2.0. "
            "Use CompositeCheckpointService instead."
        )
        warnings.warn(message, DeprecationWarning, stacklevel=3)
        super().__init__(*args, **kwargs)
