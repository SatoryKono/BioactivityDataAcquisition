1. **Fix Harness Script (`scripts/engineering/performance/measure_merger_input.py`)**:
   - Use the live production `MergeService` instead of `DummyMergeService` and `MockDeltaReader`. Initialize it with proper mocks for its dependencies (like LoggerPort, MergedStoragePort, DeltaReaderPort) where the DeltaReaderPort mock actually returns the Arrow table using `deltalake.DeltaTable`. Oh wait, since the actual code requires `delta_reader`, we can create a mock implementation of the port `bioetl.domain.ports.DeltaReaderPort` and inject it into the real `MergeService`.
   - Add `resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))` to enforce the 4GB memory guard safely, rather than relying on OOM killer.
   - Include sample counts, source commit identity (`git log -1 --format=%H`), command executed, and exit codes in the report.
2. **Add Regression Test for Harness (`tests/performance/test_measure_merger_input.py`)**:
   - Write a pytest smoke test that verifies the harness script runs successfully on a small scale (e.g., 100 rows).
3. **Execute & Regenerate Report**:
   - Run the updated script.
   - Run `uv run pytest tests/performance/test_measure_merger_input.py`.
   - Commit the changes and prepare for submission.
