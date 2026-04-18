"""Shared test harness for CompositePipelineRunner unit suites."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import polars as pl

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.domain.composite.result import EnrichmentResult, MergeResult
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.locking import FencingToken

MOCK_FENCING_TOKEN = FencingToken(
    sequence=1,
    key="lock:mock",
    owner_id=UUID("00000000-0000-0000-0000-000000000000"),
    issued_at=0.0,
)


class InMemoryCheckpointManager:
    """Minimal checkpoint manager fake for CompositePipelineRunner unit tests."""

    expected_effective_config_hash = ""
    expected_contract_ref = ""
    expected_contract_version = ""
    expected_manifest_id = ""

    def __init__(
        self,
        *,
        composite_name: str,
        run_id: str,
        logger: MagicMock,
        resume: bool = False,
    ) -> None:
        self._composite_name = composite_name
        self._run_id = run_id
        self._logger = logger
        self._resume = resume
        self._state = CompositeCheckpointState(
            composite_name=composite_name,
            run_id=run_id,
            created_at=datetime.now(tz=UTC),
        )

    async def load(self) -> CompositeCheckpointState:
        await asyncio.sleep(0)
        return self._state

    async def save(self, state: CompositeCheckpointState) -> None:
        await asyncio.sleep(0)
        self._state = state

    async def delete(self) -> None:
        await asyncio.sleep(0)

    async def delete_orphaned(self) -> int:
        await asyncio.sleep(0)
        return 0

    async def list_all(self) -> list[str]:
        await asyncio.sleep(0)
        return []


@dataclass
class MockEnricherConfig:
    """Mock enricher configuration for runner tests."""

    pipeline: str
    required: bool = False


@dataclass
class MockCompositeConfig:
    """Mock composite configuration for runner tests."""

    name: str = "test_composite"
    lock_key: str = "lock:test_composite"

    @dataclass
    class SeedConfig:
        pipeline: str = "chembl_activity"
        silver_table: str = "chembl_activity"
        output_keys: tuple[str, ...] = ("chembl_id",)

    @dataclass
    class MergeConfig:
        output_silver_path: str = "silver/composite"
        output_gold_path: str = "gold/composite"

    @dataclass
    class DQConfig:
        soft_fail_threshold: float = 0.05
        hard_fail_threshold: float = 0.20

    seed: SeedConfig | None = None
    merge: MergeConfig | None = None
    dq: DQConfig | None = None
    enrichers: tuple[object, ...] = ()
    required_enrichers: frozenset[str] = frozenset()
    dependencies: tuple[object, ...] = ()

    @property
    def required_dependencies(self) -> tuple[str, ...]:
        return tuple(
            dependency.pipeline
            for dependency in self.dependencies
            if getattr(dependency, "required", False)
        )

    def __post_init__(self) -> None:
        if self.seed is None:
            self.seed = self.SeedConfig()
        if self.merge is None:
            self.merge = self.MergeConfig()
        if self.dq is None:
            self.dq = self.DQConfig()


class MockPipelineRunner:
    """Mock PipelineRunner for runner tests."""

    def __init__(
        self,
        should_fail: bool = False,
        error_message: str = "Pipeline failed",
    ) -> None:
        self._should_fail = should_fail
        self._error_message = error_message
        self.run_called = False
        self._executor = MagicMock()
        self._executor.records_fetched = 100
        self._executor.records_silver = 95

    @property
    def execution_metrics(self) -> dict[str, int]:
        return {
            "records_fetched": self._executor.records_fetched,
            "records_silver": self._executor.records_silver,
        }

    async def run(self) -> None:
        await asyncio.sleep(0)
        self.run_called = True
        if self._should_fail:
            raise RuntimeError(self._error_message)


def create_in_memory_checkpoint_manager(
    *,
    composite_name: str,
    run_id: str,
    logger: MagicMock,
    resume: bool = False,
) -> InMemoryCheckpointManager:
    """Create a lightweight checkpoint manager without filesystem I/O."""
    return InMemoryCheckpointManager(
        composite_name=composite_name,
        run_id=run_id,
        logger=logger,
        resume=resume,
    )


def create_mock_logger() -> MagicMock:
    """Create a mock logger with all standard methods."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger


def create_mock_lock(*, release_value: bool = True) -> AsyncMock:
    """Create a mock lock preloaded with the shared fencing token."""
    lock = AsyncMock()
    lock.acquire = AsyncMock(return_value=MOCK_FENCING_TOKEN)
    lock.release = AsyncMock(return_value=release_value)
    return lock


def create_mock_checkpoint_manager(
    initial_state: CompositeCheckpointState | None = None,
) -> AsyncMock:
    """Create an async checkpoint manager stub."""
    manager = AsyncMock()
    if initial_state is None:
        initial_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            created_at=datetime.now(tz=UTC),
        )
    manager.load = AsyncMock(return_value=initial_state)
    manager.save = AsyncMock()
    manager.delete = AsyncMock()
    return manager


def create_tracking_checkpoint_manager(
    *,
    composite_name: str = "test_composite",
    run_id: str = "00000000-0000-0000-0000-000000000123",
    state: CompositePipelineState = CompositePipelineState.NOT_STARTED,
) -> AsyncMock:
    """Create a checkpoint manager that records every saved state."""
    manager = AsyncMock()
    manager._saved_states = []

    async def load_impl() -> CompositeCheckpointState:
        await asyncio.sleep(0)
        return CompositeCheckpointState(
            composite_name=composite_name,
            run_id=run_id,
            state=state,
            created_at=datetime.now(tz=UTC),
        )

    async def save_impl(checkpoint_state: CompositeCheckpointState) -> None:
        await asyncio.sleep(0)
        manager._saved_states.append(checkpoint_state)

    manager.load = AsyncMock(side_effect=load_impl)
    manager.save = AsyncMock(side_effect=save_impl)
    manager.delete = AsyncMock()
    return manager


def create_mock_key_extractor(
    dataframe: pl.DataFrame | None = None,
) -> AsyncMock:
    """Create a mock key extractor returning the provided dataframe."""
    extractor = AsyncMock()
    extractor.extract = AsyncMock(
        return_value=(
            dataframe
            if dataframe is not None
            else pl.DataFrame({"chembl_id": ["CHEMBL123"]})
        )
    )
    return extractor


def create_mock_coordinator(
    results: dict[str, EnrichmentResult] | None = None,
) -> AsyncMock:
    """Create a mock enrichment coordinator."""
    coordinator = AsyncMock()
    coordinator.run_enrichers = AsyncMock(
        return_value=(
            results
            if results is not None
            else {
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=95,
                    records_not_found=5,
                    duration_seconds=10.0,
                ),
            }
        )
    )
    return coordinator


def create_mock_merger(
    result: MergeResult | None = None,
) -> AsyncMock:
    """Create a mock merger service."""
    merger = AsyncMock()
    merge_result = (
        result
        if result is not None
        else MergeResult(
            records_from_seed=100,
            records_merged=95,
            records_enriched=80,
            records_fully_enriched=70,
            sources_used=("crossref", "pubmed"),
            output_silver_path="silver/composite/test",
            output_gold_path="gold/test_enriched",
            duration_seconds=5.0,
        )
    )
    merge_call = AsyncMock(return_value=merge_result)
    merger.merge = merge_call
    merger.execute_request = merge_call
    return merger


def create_async_seed_runner(
    *,
    records_fetched: int = 100,
    records_silver: int = 95,
) -> AsyncMock:
    """Create an AsyncMock seed runner with execution metrics."""
    runner = AsyncMock()
    runner.run.return_value = None
    runner._executor = MagicMock(
        records_fetched=records_fetched,
        records_silver=records_silver,
    )
    runner.execution_metrics = {
        "records_fetched": records_fetched,
        "records_silver": records_silver,
    }
    return runner


def seed_runner_factory(seed_runner: object):
    """Return a zero-argument factory for the configured seed runner."""

    def _factory() -> object:
        return seed_runner

    return _factory


def new_seed_runner_factory():
    """Return a factory that creates a fresh mock seed runner."""

    def _factory() -> MockPipelineRunner:
        return MockPipelineRunner()

    return _factory


def new_enricher_runner_factory():
    """Return a factory that creates a fresh mock enricher runner."""

    def _factory(name: str, dataframe: object) -> MockPipelineRunner:
        return MockPipelineRunner()

    return _factory


def create_mock_fsm_state_helper(
    *,
    logger: MagicMock,
    config: MockCompositeConfig | object | None = None,
    run_id: str | None = None,
) -> FSMStateHelperService:
    """Create a real FSM helper service for runner tests."""
    return FSMStateHelperService(
        config=config or MockCompositeConfig(),
        logger=logger,
        run_id=run_id or str(uuid4()),
    )


def create_magic_composite_config(
    *,
    output_keys: tuple[str, ...] = ("doi",),
    enrichers: list[MagicMock] | None = None,
    required_enrichers: list[str] | None = None,
    output_silver_path: str = "silver/composite/test",
    output_gold_path: str = "gold/test_enriched",
) -> MagicMock:
    """Create a MagicMock composite config for runner FSM suites."""
    config = MagicMock()
    config.name = "test_composite"
    config.lock_key = "composite:test_composite"
    config.seed.pipeline = "chembl_activity"
    config.seed.silver_table = "silver/chembl/activity"
    config.seed.output_keys = output_keys
    config.enrichers = enrichers or []
    config.required_enrichers = required_enrichers or []
    config.merge.output_silver_path = output_silver_path
    config.merge.output_gold_path = output_gold_path
    config.dq.soft_fail_threshold = 0.05
    config.dq.hard_fail_threshold = 0.20
    return config


def create_magic_seed_runner_factory(
    *,
    records_fetched: int = 100,
    records_silver: int = 95,
) -> object:
    """Create a factory returning a MagicMock seed runner."""

    def factory() -> MagicMock:
        runner = MagicMock()
        runner.run = AsyncMock()
        executor = MagicMock()
        executor.records_fetched = records_fetched
        executor.records_silver = records_silver
        runner._executor = executor
        runner.execution_metrics = {
            "records_fetched": records_fetched,
            "records_silver": records_silver,
        }
        return runner

    return factory


def create_magic_enricher_runner_factory() -> object:
    """Create a factory returning a MagicMock enricher runner."""

    def factory(name: str, keys: pl.DataFrame) -> MagicMock:
        runner = MagicMock()
        runner.run = AsyncMock()
        executor = MagicMock()
        executor.records_silver = len(keys)
        executor.records_quarantined = 0
        runner._executor = executor
        runner.execution_metrics = {
            "records_silver": len(keys),
            "records_quarantined": 0,
        }
        return runner

    return factory
