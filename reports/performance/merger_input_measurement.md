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

Repeated raw observations will be captured against this committed source, with
source byte hashes, exact commands, environment, limits, exits and fixture hashes.
No production refactor or redesign is justified by this limited-scale probe.
The current PR body describes different historical results and must be reconciled
at publication review; it has not been edited by this local task.
