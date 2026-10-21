# Evidence: Crash/Restart Sweep - Silver (Issue #12106, S4)

## Qualification (Fresh Main)
- **Inline Merge Realism**: Local filesystem paths (`_should_execute_merge_inline` returning True) execute merges synchronously via native delta-rs. Cancellation/timeout is not enforceable mid-call.
- **Offload Merge Realism**: When process isolation or threading is used, merges can theoretically be timed out.
- **Commit-Conflict Reproducibility**: Yes. Concurrent writes to a Delta table via `deltalake` Python bindings correctly raise a `CommitFailedError` during `dt.merge(...).execute()` if the table version advances under it. This satisfies the requirement for a realistic `commit_conflict` retry scenario.
- **Gate Prove-ability**: Yes, the execution flow for retry telemetry allows a blocking gate. In `_handle_commit_retry` inside `merge_resilience_helpers.py`, `emit_retry` is called synchronously *before* `asyncio.sleep(delay)`. Because `emit_retry` ultimately invokes `logger.warning`, a custom logger can block the thread (using a `multiprocessing.Event.wait` for example) before the sleep or the next retry occurs. This allows test `7` (mid-retry gate) to achieve the `VERIFIED` verdict by proving the worker remains suspended without advancing state.

## Wave C: Silver Crash/Restart Verifications

| String | Scenario | Target Component | Status | Findings / Blockers |
| :--- | :--- | :--- | :--- | :--- |
| 5 | Crash during merge execution | `write_deltalake` (Merge) | `NOT_VERIFIABLE` | `_execute_merge_inline_with_timeout` calls `merge_callable()` directly. The function has no `yield`/`await` boundary, so a SIGKILL cannot be injected inside the native commit. |
| 5c | Crash during create | `write_deltalake` (Create) | `NOT_VERIFIABLE` | `_run_plain_delta_write_inline` calls `write_deltalake(**kwargs)` directly and has no Python phase boundary. |
| 5d | Crash during append | `write_deltalake` (Append) | `NOT_VERIFIABLE` | Append uses the same inline `write_deltalake` path. The binding is not a generator or coroutine. |
| 6 | Crash post-commit, pre-cleanup | `write_deltalake` (Post-write) | `NOT_VERIFIABLE` | Both inline write and inline merge return only after the native call. There is no yield gate between the atomic commit and the Python return. |
| 7 | Mid-retry `commit_conflict` gate | `_handle_commit_retry` | `VERIFIED` | Blocking gate proved via custom logger inside `multiprocessing` child. Verified organic `CommitFailedError` by injecting concurrent `V1` competitor write. Blocked target verified. Release resumes retry to complete `V2`. |
