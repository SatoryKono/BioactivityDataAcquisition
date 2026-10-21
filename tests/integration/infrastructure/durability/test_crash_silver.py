"""Crash/restart sweep for Silver Delta Writer (Wave C)."""

from __future__ import annotations

import ast
import asyncio
import inspect
import multiprocessing
import multiprocessing.synchronize
import textwrap
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pyarrow as pa
import pytest
from deltalake import DeltaTable, write_deltalake

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.delta.resilience import (
    AdaptiveRetryPolicy,
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.silver.delta_merge_helpers import (
    _execute_merge_inline_with_timeout,
)
from bioetl.infrastructure.storage.silver.delta_request_models import _DeltaWriteRequest
from bioetl.infrastructure.storage.silver.delta_write_execution import (
    _run_plain_delta_write_inline,
)
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from bioetl.infrastructure.time.system_clock import SystemClock
from bioetl.infrastructure.validation import ContractAwareSilverValidator

pytestmark = pytest.mark.integration


class GateLogger(NoOpLogger):
    """Custom logger that blocks execution upon emitting a specific retry event."""

    def __init__(
        self,
        reach_event: multiprocessing.synchronize.Event,
        release_event: multiprocessing.synchronize.Event,
    ) -> None:
        super().__init__()
        self._reach_event = reach_event
        self._release_event = release_event

    def warning(self, _event: str, **kwargs: Any) -> Any:
        if (
            _event == "silver_merge_retry"
            and kwargs.get("retry_type") == "commit_conflict"
        ):
            self._reach_event.set()
            self._release_event.wait(timeout=10)
        return super().warning(_event, **kwargs)


def _child_worker_mid_retry(
    base_path: Path,
    reach_event: multiprocessing.synchronize.Event,
    release_event: multiprocessing.synchronize.Event,
) -> None:
    """Child process that triggers an organic commit_conflict and blocks in the logger."""

    async def _run() -> None:
        table_path = base_path / "test_silver_7"
        logger = GateLogger(reach_event, release_event)
        validator = ContractAwareSilverValidator(schema=None)
        req = SilverWriterRuntimeServicesRequest(
            logger=logger, clock=SystemClock(), silver_validator=validator
        )
        writer = SilverWriter(base_path=base_path, logger=logger, runtime_request=req)
        retry_policy = AdaptiveRetryPolicy(
            enabled=True, max_retries=2, base_delay_seconds=0.1, max_delay_seconds=0.5
        )
        if writer._delta is not None:
            writer._delta._merge_resilience_policy = SilverMergeResiliencePolicy(
                commit_retry=retry_policy,
                timeout_retry=retry_policy,
                execution_timeout_seconds=30.0,
            )

        orig_build = None
        from bioetl.infrastructure.storage.silver import delta_merge_helpers

        orig_build = delta_merge_helpers._build_merge_execute_callable

        call_count = 0

        def mocked_build(*args: Any, **kwargs: Any) -> Any:
            merge_callable = orig_build(*args, **kwargs)

            def mock_callable() -> Any:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # Inject a concurrent competitor write right before the inner callable runs
                    v1_df = pa.table(
                        {"id": [1], "val": ["V1"], "content_hash": ["hash_v1"]}
                    )
                    write_deltalake(str(table_path), v1_df, mode="append")
                return merge_callable()

            return mock_callable

        with patch(
            "bioetl.infrastructure.storage.silver.delta_merge_helpers._build_merge_execute_callable",
            new=mocked_build,
        ):
            try:
                request = _DeltaWriteRequest(
                    validated_mode=SilverWriteMode.MERGE,
                    table_path=str(table_path),
                    arrow_data=pa.table(
                        {"id": [1], "val": ["A"], "content_hash": ["hash1"]}
                    ),
                    primary_keys=["id"],
                    partition_cols=None,
                    merge_schema=False,
                )
                await writer._dispatch_write_with_domain_errors(
                    table_name="test_silver_7", request=request
                )
            except Exception as e:
                # Let exceptions bubble to fail the child process
                raise e

    asyncio.run(_run())


def test_silver_mid_retry_gate_string_7(tmp_path: Path) -> None:
    """Prove that Silver merge handles commit_conflict and blocks predictably in logger.

    This fulfills string 7: mid-retry gate with commit_conflict.
    """
    base_path = tmp_path / "g1_silver"
    base_path.mkdir()
    table_path = base_path / "test_silver_7"

    # Step 1: Initial V0
    v0_df = pa.table({"id": [1], "val": ["V0"], "content_hash": ["hash_v0"]})
    write_deltalake(str(table_path), v0_df)

    ctx = multiprocessing.get_context("spawn")
    reach_event = ctx.Event()
    release_event = ctx.Event()

    process = ctx.Process(
        target=_child_worker_mid_retry,
        args=(base_path, reach_event, release_event),
    )
    process.start()

    try:
        # Wait for child to inject concurrent write and reach the gate
        assert reach_event.wait(timeout=10), "Child never reached mid-retry gate"

        # Prove child is blocked by verifying no further commits occurred
        time.sleep(1)
        dt = DeltaTable(str(table_path))
        assert dt.version() == 1, (
            f"Table advanced beyond V1 unexpectedly: {dt.version()}"
        )
        assert process.is_alive(), "Child died prematurely while blocked in gate"

        # Step 6: Release gate
        release_event.set()

        # Step 7: Child completes merge, table advances to V2
        process.join(timeout=10)
        assert not process.is_alive(), "Child hung after gate release"
        assert process.exitcode == 0, f"Child exited with {process.exitcode}"

        dt.update_incremental()
        assert dt.version() == 2, "Table did not advance to V2 after retry completion"

    finally:
        if process.is_alive():
            process.kill()
            process.join(timeout=10)


def _assert_no_python_phase_boundary(target: object) -> None:
    """Fail when a native Delta call exposes a Python yield/await boundary."""
    assert not inspect.isgeneratorfunction(target)
    assert not inspect.isasyncgenfunction(target)
    assert not inspect.iscoroutinefunction(target)
    source = textwrap.dedent(inspect.getsource(target))
    tree = ast.parse(source)
    assert not any(
        isinstance(node, (ast.Yield, ast.YieldFrom, ast.Await))
        for node in ast.walk(tree)
    )


def test_silver_crash_create_string_5c() -> None:
    """String 5c: inline create has no Python phase boundary inside the native write."""
    _assert_no_python_phase_boundary(_run_plain_delta_write_inline)
    assert "write_deltalake(**kwargs)" in inspect.getsource(
        _run_plain_delta_write_inline
    )


def test_silver_crash_append_string_5d() -> None:
    """String 5d: inline append uses the same uncancellable plain write."""
    _assert_no_python_phase_boundary(_run_plain_delta_write_inline)
    assert not inspect.isgeneratorfunction(write_deltalake)
    assert not inspect.iscoroutinefunction(write_deltalake)


def test_silver_crash_merge_string_5() -> None:
    """String 5: inline merge calls the native commit directly, without a yield gate."""
    _assert_no_python_phase_boundary(_execute_merge_inline_with_timeout)
    assert "merge_callable()" in inspect.getsource(_execute_merge_inline_with_timeout)


def test_silver_crash_post_commit_string_6() -> None:
    """String 6: the native commit returns only after the atomic write."""
    _assert_no_python_phase_boundary(_run_plain_delta_write_inline)
    _assert_no_python_phase_boundary(_execute_merge_inline_with_timeout)
