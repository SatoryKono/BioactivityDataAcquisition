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
from typing import Any, cast
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
    _build_merge_condition,
    _build_merge_execute_callable,
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

_MERGE_KEYS = ["id"]


class GateLogger(NoOpLogger):
    """Custom logger that blocks execution upon emitting a specific retry event."""

    def __init__(
        self,
        reach_event: multiprocessing.synchronize.Event,
        release_event: multiprocessing.synchronize.Event,
    ) -> None:
        """Hold the reach and release events shared with the parent process."""
        super().__init__()
        self._reach_event = reach_event
        self._release_event = release_event

    def warning(self, _event: str, **kwargs: Any) -> Any:
        """Block retry until the parent releases the commit-conflict gate."""
        if (
            _event == "silver_merge_retry"
            and kwargs.get("retry_type") == "commit_conflict"
        ):
            self._reach_event.set()
            self._release_event.wait()
        return super().warning(_event, **kwargs)


def _child_worker_mid_retry(
    base_path: Path,
    reach_event: multiprocessing.synchronize.Event,
    release_event: multiprocessing.synchronize.Event,
) -> None:
    """Child process that triggers an organic commit_conflict and blocks in the logger."""

    async def _run() -> None:
        """Merge id=1, conflict once on that key, then finish the retry."""
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

        from bioetl.infrastructure.storage.silver import delta_merge_helpers

        orig_build = delta_merge_helpers._build_merge_execute_callable
        call_count = 0

        def mocked_build(*args: Any, **kwargs: Any) -> Any:
            """Wrap the real merge callable and inject one competing commit."""
            merge_callable = orig_build(*args, **kwargs)

            def mock_callable() -> Any:
                """Append a competing id=1 row before the first native merge."""
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    competitor = pa.table(
                        {"id": [1], "val": ["V1"], "content_hash": ["hash_v1"]}
                    )
                    write_deltalake(str(table_path), competitor, mode="append")
                return merge_callable()

            return mock_callable

        with patch(
            "bioetl.infrastructure.storage.silver.delta_merge_helpers._build_merge_execute_callable",
            new=mocked_build,
        ):
            request = _DeltaWriteRequest(
                validated_mode=SilverWriteMode.MERGE,
                table_path=str(table_path),
                arrow_data=pa.table(
                    {"id": [1], "val": ["A"], "content_hash": ["hash1"]}
                ),
                primary_keys=list(_MERGE_KEYS),
                partition_cols=None,
                merge_schema=False,
            )
            await writer._dispatch_write_with_domain_errors(
                table_name="test_silver_7", request=request
            )

    asyncio.run(_run())


def _sorted_delta_rows(table: DeltaTable) -> tuple[tuple[int, str, str], ...]:
    """Return ``(id, val, content_hash)`` rows in stable order."""
    arrow = table.to_pyarrow_table().select(["id", "val", "content_hash"])
    rows = [
        (int(row["id"]), str(row["val"]), str(row["content_hash"]))
        for row in arrow.to_pylist()
    ]
    return tuple(sorted(rows))


def test_silver_mid_retry_gate_string_7(tmp_path: Path) -> None:
    """Prove the commit_conflict gate holds V1, then the retry writes V2.

    The competitor row uses the same ``id`` as the merge source so it matches
    ``_build_merge_condition``.
    """
    assert _build_merge_condition(list(_MERGE_KEYS)) == "target.id = source.id"
    base_path = tmp_path / "g1_silver"
    base_path.mkdir()
    table_path = base_path / "test_silver_7"

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
        assert reach_event.wait(timeout=10), "Child never reached mid-retry gate"

        time.sleep(1)
        dt = DeltaTable(str(table_path))
        assert dt.version() == 1, (
            f"Table advanced beyond V1 unexpectedly: {dt.version()}"
        )
        assert _sorted_delta_rows(dt) == (
            (1, "V0", "hash_v0"),
            (1, "V1", "hash_v1"),
        )
        assert process.is_alive(), "Child died prematurely while blocked in gate"

        release_event.set()

        process.join(timeout=10)
        assert not process.is_alive(), "Child hung after gate release"
        assert process.exitcode == 0, f"Child exited with {process.exitcode}"

        dt.update_incremental()
        assert dt.version() == 2, "Table did not advance to V2 after retry completion"
        assert _sorted_delta_rows(dt) == (
            (1, "A", "hash1"),
            (1, "A", "hash1"),
        )
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


def _assert_native_merge_has_no_phase_boundary() -> None:
    """Inspect the builder and the closure that calls ``dt.merge().execute()``."""
    _assert_no_python_phase_boundary(_build_merge_execute_callable)
    _assert_no_python_phase_boundary(_execute_merge_inline_with_timeout)
    records = pa.table({"id": [1], "val": ["A"], "content_hash": ["hash1"]})
    merge_callable = _build_merge_execute_callable(
        dt=cast(DeltaTable, object()),
        table_path="missing-silver-table",
        records=records,
        merge_condition=_build_merge_condition(list(_MERGE_KEYS)),
        merge_schema=False,
    )
    _assert_no_python_phase_boundary(merge_callable)
    closure_source = inspect.getsource(merge_callable)
    assert "dt.merge(" in closure_source
    assert ".execute()" in closure_source
    assert "predicate=merge_condition" in closure_source


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
    """String 5: native ``dt.merge(...).execute()`` has no yield/await boundary."""
    _assert_native_merge_has_no_phase_boundary()


def test_silver_crash_post_commit_string_6() -> None:
    """String 6: create and merge return only after the atomic native commit."""
    _assert_no_python_phase_boundary(_run_plain_delta_write_inline)
    _assert_native_merge_has_no_phase_boundary()
