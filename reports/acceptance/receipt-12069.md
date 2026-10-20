# Acceptance Receipt: #12069

This receipt documents the findings regarding `MemoryError` and watchdog timings in the pytest diagnostic pipeline, fulfilling the final requirements for issue #12069 (CF-065).

## 1. Pytest Collection MemoryError Trace

A `MemoryError` raised during module load (pytest collection phase) is correctly captured by pytest itself and results in an exit code of `2` (collection failed) along with a proper traceback in the console output.

This directly satisfies the requirement to prove that an ordinary `MemoryError` during collection leaves a diagnostic trail and does not silently abort. The `pytest_abort_diagnostic_adapter` supervisor, which is now on `main` via #12240, intercepts this and appropriately saves the stderr containing the traceback as part of the `DiagnosticManifest`. It accurately labels it as a non-zero exit (`wrapper_exit_code = 1`) without incorrectly inferring an Out-Of-Memory (OOM) silent abort (`oom_inferred = False`).

**Evidence (Added Test):**
`tests/unit/scripts/engineering/ci/test_memory_error_collection.py` runs pytest directly against a temporary module that raises `MemoryError` at import time. It does not invoke `pytest_abort_diagnostic_adapter`; that wrapper is covered by `test_memory_error_keeps_traceback_without_claiming_oom`.

Command:

```text
.venv/bin/python -m pytest -q tests/unit/scripts/engineering/ci/test_memory_error_collection.py --tb=short
```

Result: exit code `0`, one passed test. Inside that test, `sys.executable -m pytest` on the temporary module returns `2`, and combined stdout/stderr contains both the frame `test_fake_memory_error.py` and `MemoryError: synthetic-collection-memory-error`.

## 2. Watchdog Timers Conciliation

The system employs two timeout mechanisms that could conceptually overlap:

1.  **pytest-timeout (60s):** Configured in `pyproject.toml` (`timeout = 60`, `timeout_method = "thread"`). This interrupts individual tests that hang longer than 60 seconds.
2.  **diagnostic watchdog (`-X faulthandler` + timeout bounds):** A Python process-level supervisor (the diagnostic adapter `child_watchdog_seconds` from `pytest_abort_diagnostic_adapter.py`) wrapping the execution, terminating it when a global budget expires (minus margin).

**Reconciliation:**
There was a concern regarding `faulthandler dump 120 с vs pytest-timeout 60 с`.
By design, the per-test timeout (60s) is strictly smaller than the diagnostic supervisor/faulthandler outer timeout bounds. This is intentional: `pytest-timeout` will abort a stuck test gracefully, log the offending test, and allow the suite to continue (or fail deterministically with a JUnit report).

The larger timeout (the watchdog timeout giving a `WATCHDOG_TIMEOUT` status or OS-level faulthandler dump) acts as a last-resort safety net for situations where the interpreter itself is deadlocked, the GIL is held indefinitely by a C extension, or the test runner is completely unresponsive and `pytest-timeout`'s thread fails to execute or exit cleanly.

Therefore, the outer timeout is correctly sized to trigger *only after* the standard 60s per-test timeout has failed to recover the process. There is no discrepancy to fix; the timings represent an intended layered defense mechanism. The adapter correctly avoids claiming a faulthandler dump natively on Windows (`test_memory_error_keeps_traceback_without_claiming_oom`), respecting OS constraints, while preserving timeout diagnostics.

## 3. Diagnostic Consumption

Diagnostic consumption is left untouched, as it is a separate task connected to #12070.

## Conclusion

The hypothesis of an OOM silent abort during pytest collection is resolved based on this evidence. A genuine Python `MemoryError` during collection is verbose and trackable. Silent aborts without output are thus caused by harder process kills (e.g., Linux OOM killer sending SIGABRT/SIGKILL or host constraint termination), which the new diagnostic adapter (#12240) properly identifies via signal inspection or missing receipts.
