# Evidence: Crash/Restart Sweep - Silver (Issue #12106, S4)

## Qualification (Fresh Main)
- **Inline Merge Realism**: Local filesystem paths (`_should_execute_merge_inline` returning True) execute merges synchronously via native delta-rs. Cancellation/timeout is not enforceable mid-call.
- **Offload Merge Realism**: When process isolation or threading is used, merges can theoretically be timed out.
- **Commit-Conflict Reproducibility**: Yes. Concurrent writes to a Delta table via `deltalake` Python bindings correctly raise a `CommitFailedError` during `dt.merge(...).execute()` if the table version advances under it. This satisfies the requirement for a realistic `commit_conflict` retry scenario.
- **Gate Prove-ability**: Yes, the execution flow for retry telemetry allows a blocking gate. In `_handle_commit_retry` inside `merge_resilience_helpers.py`, `emit_retry` is called synchronously *before* `asyncio.sleep(delay)`. Because `emit_retry` ultimately invokes `logger.warning`, a custom logger can block the thread (using a `multiprocessing.Event.wait` for example) before the sleep or the next retry occurs. This allows test `7` (mid-retry gate) to achieve the `VERIFIED` verdict by proving the worker remains suspended without advancing state.

## Wave C: Silver Crash/Restart Verifications

| String | Scenario | Target Component | Status | Findings / Blockers |
| :--- | :--- | :--- | :--- | :--- |
| 5 | Crash during merge execution | `dt.merge(...).execute()` | `NOT_VERIFIABLE` | `_build_merge_execute_callable` runs `dt.merge(...).execute()` for an existing table. That closure and the inline wrapper have no Python `yield`/`await` boundary, so a SIGKILL cannot be injected mid-commit. |
| 5c | Crash during create | `write_deltalake` (Create) | `NOT_VERIFIABLE` | Inline create calls `write_deltalake(**kwargs)` with no Python phase boundary. |
| 5d | Crash during append | `write_deltalake` (Append) | `NOT_VERIFIABLE` | Inline append uses the same uncancellable plain write. |
| 6 | Crash post-commit, pre-cleanup | `dt.merge(...).execute()` / `write_deltalake` | `NOT_VERIFIABLE` | The native commit returns only after the atomic write. There is no post-commit Python hook between the rename and the return. |
| 7 | Mid-retry `commit_conflict` gate | `_handle_commit_retry` | `VERIFIED` | Blocking gate proved via custom logger inside `multiprocessing` child. Competing `id=1` row matches `target.id = source.id`. While blocked the table stays at V1 with `V0` and `V1`. Release completes retry at V2 with both matched rows updated to the merge source. |
