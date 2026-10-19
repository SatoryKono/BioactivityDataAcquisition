# Eager merger input measurement — Issue 12045 Phase 0

Status: NOT_ESTABLISHED. The old Bottleneck Confirmed claim is withdrawn.
The historical report is preserved byte-for-byte under
`reports/performance/history/merger_input_919147a/`, with separate limitations.

The repaired harness invokes production composition, MergeService and DeltaReader.
Only `_read_silver_table` is timed. Output storage is unused and no join is run.
The fixture is a narrow deterministic synthetic Activity/Target-like input, not
the largest production composite. It is prepared in a separate bounded process.
Every repeat uses a fresh bounded process. Peak RSS includes native imports and
service construction, excludes fixture creation, and is a process lifetime peak;
it is not operation-only allocation or a difference of cumulative maxima.

Both fixture and measurement workers enforce Linux RLIMIT_AS and RLIMIT_CPU
before native imports. Address-space limits are not RSS limits. Timeout and
nonzero exits are BLOCKED observations, not evidence of OOM or a bottleneck.
The CLI defaults to 100/1000 rows, three repeats, 4096 MiB and 30 seconds per
process; it rejects scales above 100000 and never overwrites raw evidence.

Minimal tests include a real failed allocation under a 128 MiB guard, timeout,
invalid input, history preservation and two production reads of a 10-row fixture.
The 2 GiB development smoke exited -11; the 4 GiB smoke completed. The signal
alone does not establish its cause. Container memory.max was 17179869184 bytes.

## Repeated observations

Measured source: `9d40ebb2455b8f85598c770736db6c057c5c1a21` (clean worktree).
Source bytes SHA256: `da6b59803e8f9dfffb1ff9e6262e6153c2ab1fe5f5ee048894842376a7254f31`.

Raw observations: `reports/performance/merger_input_observations.json`.
Raw bytes SHA256: `1719f98ea18b5450df740209e4a62baf9bad3ea11bc843fba2f1d29fd832a357`.

Command (a new output filename is required on each invocation):

```bash
.venv/bin/python scripts/engineering/performance/measure_merger_input.py --scales 1000 10000 100000 --repeats 3 --memory-mib 4096 --timeout-s 30 --out /tmp/pr12274-observations-9d40ebb245.json
```

All preparation and measurement exits were 0; orchestrator exit was 0.
Three fresh measurement processes per scale; no other validation commands ran
concurrently during this capture. Host CPU scheduling and page cache were not
controlled. Fresh interpreters do not imply cold filesystem caches.

| Rows | Repeats | Read time median (s) | Read time min–max (s) | Process peak RSS min–max (MiB) |
| --- | --- | --- | --- | --- |
| 1,000 | 3 | 0.018056 | 0.013656–0.018462 | 251.06–254.36 |
| 10,000 | 3 | 0.019688 | 0.017572–0.023681 | 262.05–264.96 |
| 100,000 | 3 | 0.049182 | 0.033801–0.076566 | 305.23–305.40 |

## Conclusion and validation limits

NOT_ESTABLISHED: no production bottleneck or acceptable production scale can be
inferred from a single narrow synthetic input and no joins. The largest composite,
wide production schemas, simultaneous input retention and fan-out remain unmeasured.
No production refactor or redesign is justified by this probe.

Owning tests: 93 passed; test-governance architecture tests: 46 passed. Targeted
Ruff, docs links and docs drift passed. Selected ARTIFACT_REFRESH families
(test-gov, flaky fingerprint, remote-main) and debt-governance passed after update.
The exact commands for those historical results were not retained in the source
commit and are not reconstructed here. The full family check is BLOCKED by stale
telemetry hash and unreachable historical source commit; no telemetry was
fabricated or rebound. No budgets were increased.

The PR description matches this report's NOT_ESTABLISHED result. The four reported
Sonar issues still require exact current details; no claim of fixing them is made.
