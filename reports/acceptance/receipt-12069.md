# Acceptance Receipt for Issue #12069 (CF-065)

This receipt documents the findings regarding `MemoryError` and watchdog timings in the pytest diagnostic pipeline, fulfilling the acceptance criteria for this portion of issue #12069 (CF-065).

## 1. Pytest Collection MemoryError Trace

A `MemoryError` raised during module load (pytest collection phase) is correctly captured by pytest itself and results in an exit code of `2` (collection failed) along with a proper traceback in the console output.

This directly satisfies the requirement to prove that an ordinary `MemoryError` during collection leaves a diagnostic trail and does not silently abort. The `pytest_abort_diagnostic_adapter` supervisor, which is now on `main` via #12240, saves child stdout and stderr logs referenced by the `DiagnosticManifest`. It records a non-zero child exit without incorrectly inferring an Out-Of-Memory (OOM) silent abort (`oom_inferred = False`). With diagnostics persisted, the wrapper preserves the positive child exit code: `2` for the collection failure above. The adapter test `test_memory_error_keeps_traceback_without_claiming_oom` separately covers a direct Python `MemoryError`, for which `wrapper_exit_code = 1`.

**Evidence (Added Test):**
A new unit test `tests/unit/scripts/engineering/ci/test_memory_error_collection.py` explicitly reproduces this exact `MemoryError` during collection scenario.
Result: Exit code is 2, and the traceback (`MemoryError: synthetic-collection-memory-error`) is captured correctly in the standard output/error, proving that the collection abort leaves a clean diagnostic trail.

## 2. Watchdog Timers Reconciliation

The system employs two timeout mechanisms that could conceptually overlap:

1.  **pytest-timeout (60s):** Configured in `pyproject.toml` (`timeout = 60`, `timeout_method = "thread"`). This bounds individual tests; the thread timeout can terminate the test runner, so suite continuation or a complete JUnit report is not guaranteed.
2.  **diagnostic watchdog (`-X faulthandler` + timeout bounds):** A Python process-level supervisor wrapping the execution. The diagnostic adapter `child_watchdog_seconds` from `pytest_abort_diagnostic_adapter.py` derives the timeout from the caller's total budget minus a diagnostic and cleanup margin. `-X faulthandler` enables fault tracebacks; it does not itself configure a 120-second timer.

**Reconciliation:**
There was a concern regarding `faulthandler dump 120 с vs pytest-timeout 60 с`.
These represent distinct layers: the per-test timeout bounds an individual test, while the diagnostic supervisor bounds the entire child run. For the serial-coverage pass budget, `child_watchdog_seconds` stays above the 60-second per-test timeout; the outer timeout is budget-dependent rather than a fixed 120 seconds.

The outer watchdog records `WATCHDOG_TIMEOUT` when the child run exceeds its budget. It provides a last-resort safety net when the test runner is unresponsive and the per-test timeout cannot terminate it. On POSIX it attempts a diagnostic `SIGABRT` before process-tree cleanup.

The timeouts therefore serve different scopes rather than conflicting. The outer budget covers the whole run, not time elapsed within a particular test. The adapter correctly avoids claiming a faulthandler dump natively on Windows (`test_windows_timeout_does_not_claim_sigabrt_dump`), respecting OS constraints, while preserving timeout diagnostics.

## 3. Diagnostic Consumption

Diagnostic consumption optimization is out of scope for this receipt and is tracked separately in #12070.

## Conclusion

The collection test demonstrates that an ordinary Python `MemoryError` during collection leaves a diagnostic trail. The diagnostic adapter (#12240) separately records signal aborts, watchdog timeouts, and missing evidence without inferring host OOM from a silent abort, a signal, or a missing report.
