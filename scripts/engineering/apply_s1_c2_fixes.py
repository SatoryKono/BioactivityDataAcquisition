"""Apply S1 C2 application-core residual fixes (one-shot patcher)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"{label}: target block missing in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"fixed {label}")


def main() -> None:
    replace_once(
        ROOT / "src/bioetl/application/core/postrun/_metadata_writes.py",
        (
            "    silver_table = config.table.silver_table\n"
            "    if not silver_table:\n"
            "        return None\n"
            '    silver_path = storage.get_table_path(silver_table, layer="silver")\n'
        ),
        (
            "    silver_table = config.table.silver_table\n"
            "    if not silver_table:\n"
            "        return None\n"
            '    if not storage.is_table_initialized(silver_table, layer="silver"):\n'
            "        return None\n"
            '    silver_path = storage.get_table_path(silver_table, layer="silver")\n'
        ),
        "metadata_writes",
    )

    replace_once(
        ROOT / "src/bioetl/application/core/lifecycle/cleanup_service.py",
        (
            "        await asyncio.sleep(0)\n"
            "        # Use sync preview_cleanup from StorageMaintenancePort.\n"
            "        preview_dict = self._storage.preview_cleanup(\n"
            "            silver_table=silver_table,\n"
            "            gold_table=gold_table,\n"
            "        )\n"
        ),
        (
            "        # Offload the synchronous filesystem scan so the event loop stays responsive.\n"
            "        preview_dict = await asyncio.to_thread(\n"
            "            self._storage.preview_cleanup,\n"
            "            silver_table,\n"
            "            gold_table,\n"
            "        )\n"
        ),
        "cleanup_service",
    )

    replace_once(
        ROOT / "src/bioetl/application/core/lifecycle/heartbeat.py",
        (
            "    async def stop(self) -> None:\n"
            '        """Stop the background heartbeat task.\n'
            "        Cancels the task and waits for completion.\n"
            '        """\n'
            "        if self._task:\n"
            "            self._task.cancel()\n"
            "            with contextlib.suppress(asyncio.CancelledError):\n"
            "                await self._task\n"
            "            self._task = None\n"
            "\n"
            "    @property\n"
            "    def is_running(self) -> bool:\n"
            '        """Check if heartbeat task is running."""\n'
            "        return self._task is not None and not self._task.done()\n"
            "\n"
            "    async def _heartbeat_loop(self) -> None:\n"
            '        """Background loop that sends periodic heartbeats.\n'
            "        Raises:\n"
            "            PipelineShutdownError: If lock is lost during heartbeat.\n"
            '        """\n'
            "        while not self._shutdown_signal.is_requested:\n"
            "            await asyncio.sleep(self._interval)\n"
            "            success = await self._lock_port.heartbeat(\n"
            "                self._lock_key, self._owner_id, exclusive=self._exclusive\n"
            "            )\n"
            "            if not success:\n"
            '                self._logger.error("Lost lock during execution!")\n'
            "                self._shutdown_signal.request()\n"
            '                raise PipelineShutdownError("Lock lost")\n'
        ),
        (
            "    async def stop(self) -> None:\n"
            '        """Stop the background heartbeat task.\n'
            "        Cancels the task and waits for completion.\n"
            '        """\n'
            "        if self._task:\n"
            "            self._task.cancel()\n"
            "            # CancelledError is expected after cancel(); PipelineShutdownError must not\n"
            "            # surface from a completed lock-loss path when stop() races the loop.\n"
            "            with contextlib.suppress(asyncio.CancelledError, PipelineShutdownError):\n"
            "                await self._task\n"
            "            self._task = None\n"
            "\n"
            "    @property\n"
            "    def is_running(self) -> bool:\n"
            '        """Check if heartbeat task is running."""\n'
            "        return self._task is not None and not self._task.done()\n"
            "\n"
            "    async def _heartbeat_loop(self) -> None:\n"
            '        """Background loop that sends periodic heartbeats.\n'
            "\n"
            "        On lock loss, request shutdown and return immediately so the background\n"
            "        task completes cleanly without failing with PipelineShutdownError.\n"
            '        """\n'
            "        while not self._shutdown_signal.is_requested:\n"
            "            await asyncio.sleep(self._interval)\n"
            "            success = await self._lock_port.heartbeat(\n"
            "                self._lock_key, self._owner_id, exclusive=self._exclusive\n"
            "            )\n"
            "            if not success:\n"
            '                self._logger.error("Lost lock during execution!")\n'
            "                self._shutdown_signal.request()\n"
            "                return\n"
        ),
        "heartbeat",
    )

    replace_once(
        ROOT
        / "src/bioetl/application/core/preflight/medallion_validator_idempotency.py",
        (
            "        return [\n"
            "            ConfigValidationError(\n"
            "                field=field,\n"
            "                expected=(\n"
            '                    "one of: append_log, occurrence_only, "\n'
            '                    "partition_append_with_stable_partition_key"\n'
            "                ),\n"
            "                actual=contract,\n"
            '                rule="RULES §2.1: append-mode semantic outputs require append-safe idempotency_contract",\n'
            "            )\n"
            "        ]\n"
        ),
        (
            '        append_safe = ", ".join(sorted(APPEND_SAFE_IDEMPOTENCY_CONTRACTS))\n'
            "        return [\n"
            "            ConfigValidationError(\n"
            "                field=field,\n"
            '                expected=f"one of: {append_safe}",\n'
            "                actual=contract,\n"
            '                rule="RULES §2.1: append-mode semantic outputs require append-safe idempotency_contract",\n'
            "            )\n"
            "        ]\n"
        ),
        "idempotency",
    )

    replace_once(
        ROOT / "src/bioetl/application/core/preflight/service.py",
        (
            "from __future__ import annotations\n"
            "\n"
            "import time\n"
            "from typing import TYPE_CHECKING, Protocol\n"
        ),
        (
            "from __future__ import annotations\n"
            "\n"
            "import inspect\n"
            "import time\n"
            "from typing import TYPE_CHECKING, Protocol\n"
        ),
        "preflight_import",
    )
    replace_once(
        ROOT / "src/bioetl/application/core/preflight/service.py",
        (
            "async def validate_infrastructure(host: _PreflightExecutionHostProtocol) -> None:\n"
            '    """Validate infrastructure health before pipeline execution."""\n'
            "    start_time = time.perf_counter()\n"
            "    try:\n"
            "        report = await host._preflight_service.validate_infrastructure(\n"
            "            host._services,\n"
            "            raise_on_unhealthy=False,\n"
            "        )\n"
            "    except TypeError as exc:\n"
            '        if "raise_on_unhealthy" not in str(exc):\n'
            "            raise\n"
            "        report = await host._preflight_service.validate_infrastructure(host._services)\n"
            "    if report is None:\n"
            "        return\n"
        ),
        (
            "def _supports_raise_on_unhealthy(validate_fn: object) -> bool:\n"
            '    """Return True when ``validate_infrastructure`` accepts raise_on_unhealthy."""\n'
            "    try:\n"
            "        signature = inspect.signature(validate_fn)  # type: ignore[arg-type]\n"
            "    except (TypeError, ValueError):\n"
            "        return False\n"
            '    return "raise_on_unhealthy" in signature.parameters\n'
            "\n"
            "\n"
            "async def validate_infrastructure(host: _PreflightExecutionHostProtocol) -> None:\n"
            '    """Validate infrastructure health before pipeline execution."""\n'
            "    start_time = time.perf_counter()\n"
            "    validate_fn = host._preflight_service.validate_infrastructure\n"
            "    if _supports_raise_on_unhealthy(validate_fn):\n"
            "        report = await validate_fn(\n"
            "            host._services,\n"
            "            raise_on_unhealthy=False,\n"
            "        )\n"
            "    else:\n"
            "        report = await validate_fn(host._services)\n"
            "    if report is None:\n"
            "        return\n"
        ),
        "preflight_validate",
    )

    replace_once(
        ROOT / "src/bioetl/application/core/runner.py",
        (
            "    async def run(self) -> None:\n"
            '        """Execute the pipeline and always finalize shutdown/telemetry cleanup."""\n'
            "        record_run_started(self)\n"
            '        debug_export_status = "success"\n'
            "        try:\n"
            "            shutdown_recorded = await self._run_pipeline_lifecycle()\n"
            "        except PipelineShutdownError:\n"
            '            debug_export_status = "shutdown"\n'
            "            self._record_terminal_shutdown()\n"
            "            raise\n"
            "        except _RUN_FAILURE_EXCEPTIONS as exc:\n"
            '            debug_export_status = "failed"\n'
            "            record_run_failed(self, exc)\n"
            "            raise\n"
            "        else:\n"
            "            if not shutdown_recorded:\n"
            "                self._record_successful_completion()\n"
            "            else:\n"
            '                debug_export_status = "shutdown"\n'
            "        finally:\n"
            "            await self._finalize_debug_export(debug_export_status)\n"
            "            await self._cleanup_after_run()\n"
            "\n"
            "    async def _run_pipeline_lifecycle(self) -> bool:\n"
            "        shutdown_recorded = False\n"
            "        with self._pipeline_span(), self._observer:\n"
            "            try:\n"
            "                async with self._services, self._lock_runtime_service:\n"
            "                    await self._run_managed_pipeline()\n"
            "            except PipelineShutdownError:\n"
            "                self._record_terminal_shutdown()\n"
            "                shutdown_recorded = True\n"
            "                raise\n"
            "            finally:\n"
            "                self._observer.capture_execution_metrics(self.execution_metrics)\n"
            "        return shutdown_recorded\n"
        ),
        (
            "    async def run(self) -> None:\n"
            '        """Execute the pipeline and always finalize shutdown/telemetry cleanup."""\n'
            "        record_run_started(self)\n"
            '        debug_export_status = "success"\n'
            "        try:\n"
            "            await self._run_pipeline_lifecycle()\n"
            "        except PipelineShutdownError:\n"
            '            debug_export_status = "shutdown"\n'
            "            # Terminal shutdown is recorded only in this outer handler.\n"
            "            self._record_terminal_shutdown()\n"
            "            raise\n"
            "        except _RUN_FAILURE_EXCEPTIONS as exc:\n"
            '            debug_export_status = "failed"\n'
            "            record_run_failed(self, exc)\n"
            "            raise\n"
            "        else:\n"
            "            self._record_successful_completion()\n"
            "        finally:\n"
            "            # Guard each finalizer independently so cleanup still runs when\n"
            "            # debug-export finalization fails (and vice versa).\n"
            "            try:\n"
            "                await self._finalize_debug_export(debug_export_status)\n"
            "            except _RUN_FAILURE_EXCEPTIONS as error:\n"
            "                self._logger.warning(\n"
            '                    "debug_export_finalize_outer_failed",\n'
            "                    error=str(error),\n"
            "                    error_type=type(error).__name__,\n"
            "                    run_id=str(self._context.run_id),\n"
            "                )\n"
            "            try:\n"
            "                await self._cleanup_after_run()\n"
            "            except _RUN_FAILURE_EXCEPTIONS as error:\n"
            "                self._logger.warning(\n"
            '                    "cleanup_after_run_failed",\n'
            "                    error=str(error),\n"
            "                    error_type=type(error).__name__,\n"
            "                    run_id=str(self._context.run_id),\n"
            "                )\n"
            "\n"
            "    async def _run_pipeline_lifecycle(self) -> None:\n"
            "        with self._pipeline_span(), self._observer:\n"
            "            try:\n"
            "                async with self._services, self._lock_runtime_service:\n"
            "                    await self._run_managed_pipeline()\n"
            "            finally:\n"
            "                self._observer.capture_execution_metrics(self.execution_metrics)\n"
        ),
        "runner",
    )

    test_path = ROOT / "tests/unit/application/core/test_postrun_metadata_writes.py"
    test_text = test_path.read_text(encoding="utf-8")
    old_test = "    storage.is_table_initialized = MagicMock(return_value=False)\n"
    new_test = (
        "    # Silver finalization requires an initialized table (parity with gold gate).\n"
        "    storage.is_table_initialized = MagicMock(return_value=True)\n"
    )
    if old_test in test_text:
        test_path.write_text(test_text.replace(old_test, new_test, 1), encoding="utf-8")
        print("fixed metadata writes test")
    else:
        print("metadata writes test already updated or different")

    print("C2 partial done (remaining: pre_silver + service_support write files)")


if __name__ == "__main__":
    main()
