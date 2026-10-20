______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-20'

______________________________________________________________________

# Decision note: CF-038 Phase-1 post-run compaction

**Date:** 2026-10-20
**Code:** CF-038 / #12042
**Status:** selected direction, pending GitHub-owner acceptance
**Option selected:** post-run compaction, keeping per-batch `SilverWriteMode.MERGE`

This note records a direction. It does not confirm a speedup and it does
not authorize production implementation.

## Decision

Phase-1 keeps one Delta `MERGE` per batch. The follow-up direction, when a
later change is explicitly authorized, is compaction of files that remain
on a live Silver table between runs.

`OPTIMIZE` and `VACUUM` are separate operations. A future implementation
does not enable automatic `VACUUM` by default. Retention is not shortened.
`retention_hours=0` is out of scope.

Phase-1 does not claim a lower `MERGE` cost inside the already measured
run. Post-run compaction does not rewrite that run's merge-time curve.

## Why the other two options wait

Adaptive batch upsizing waits because `run_2` does not split transform time
from `write_silver` time and does not compare batch sizes. No speedup is
attributed to a larger batch.

A single end-of-run merge waits because the measured commit tax is not
extreme: N=100 max `merge_time_raw_s` is 0.1689 s and the merge sum is
7.728513 s for 50000 processed rows. Moving `MERGE` to the end would
separate the periodic checkpoint (`records_processed` in
`src/bioetl/application/core/batch_checkpoint_recovery_service.py`) from a
Silver version that today is written inside `process_batch`
(`src/bioetl/application/core/record_processor.py`). That redesign is not
justified by these numbers.

## Measurement binding

Numbers below are from source revision
`1117a76a578cc7315cfe62823b8d5d7c6759b2af` (ancestor of current `main`),
capture `2026-10-20T12:48:01Z`, Python 3.13.15, Linux. They are not
measurements of `main` `07482702d3bc9d6b742188400c371304f4881eb9`.

The bytes live only in commit `0d7861219fb4b1ee1ef0e747ed281ac96fd5edb1`.
PR #12314 merge is `004e2913db6289fcca4c8f44de291899ff877bd7`. Commit
`d48192563e10f9a3350280c10380243cd7f19dc9` (#12316) removes `run_2`, its
provenance files, and the capture tool from `main`. Current `main`
`07482702d3bc9d6b742188400c371304f4881eb9` does not contain those paths.
Historical retention confirms the origin of the measurements. It does not
put a required evidence surface in the current tree. The files were not
copied onto current `main` and were not re-captured.

Harness workload, not a production `batch_size=1000` run: `batch_size=500`,
`overlap_ratio=0.2`, primary key `id`, each round calls
`write_silver(..., mode=MERGE)` on a new table.

| N | Wall | Merge sum (s) | Merge/wall | Peak RSS | Sampled RSS, last round | Log files | Parquet files | Final/processed rows | Exit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 0:07.43 | 0.574680 | 7.7% | 329056 KB | 315.85 MiB | 10 | 17 | 4100/5000 | 0 |
| 50 | 0:05.13 | 2.811909 | 54.8% | 359204 KB | 346.33 MiB | 50 | 87 | 20100/25000 | 0 |
| 100 | 0:10.44 | 7.728513 | 74.0% | 478412 KB | 464.78 MiB | 102 | 183 | 40100/50000 | 0 |

Peak RSS is GNU time `Maximum resident set size`. `rss_mb` in the JSON is
a psutil sample after the round. N=10 wall includes 1806 major page faults;
N=50 has 1 and N=100 has 10. Wall is not the pain scale. From N=50 to N=100
the merge sum grows 2.75x while commits double. N=100 first-10 mean
`merge_time_raw_s` is 0.0362 s; last-10 mean is 0.1314 s; median 0.0736 s;
p95 0.1311 s. Final N=100 bytes: 3271070 parquet, 340549 `_delta_log`.
The last round adds 3 log files instead of 1 (102 total). The JSON does not
name those two extra files.

## Artifacts and hash check

Permalink base, commit `0d7861219fb4b1ee1ef0e747ed281ac96fd5edb1` only.
These URLs are not links to current `main`.

- [manifest.json](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/0d7861219fb4b1ee1ef0e747ed281ac96fd5edb1/reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_2/manifest.json)
- [benchmark_provenance.md](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/0d7861219fb4b1ee1ef0e747ed281ac96fd5edb1/reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_2/benchmark_provenance.md)
- [N10/time.txt](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/0d7861219fb4b1ee1ef0e747ed281ac96fd5edb1/reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_2/N10/time.txt)
- [N50/time.txt](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/0d7861219fb4b1ee1ef0e747ed281ac96fd5edb1/reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_2/N50/time.txt)
- [N100/time.txt](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/0d7861219fb4b1ee1ef0e747ed281ac96fd5edb1/reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_2/N100/time.txt)
- [merge_scaling_N10.json](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/0d7861219fb4b1ee1ef0e747ed281ac96fd5edb1/reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_2/N10/N10-n1j0nze5/merge_scaling_N10.json)
- [merge_scaling_N50.json](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/0d7861219fb4b1ee1ef0e747ed281ac96fd5edb1/reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_2/N50/N50-9btidy6p/merge_scaling_N50.json)
- [merge_scaling_N100.json](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/0d7861219fb4b1ee1ef0e747ed281ac96fd5edb1/reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_2/N100/N100-yevzmbf8/merge_scaling_N100.json)

Run from the repository root with Python 3 and Git. The historical commit
must be available in the local clone. This command reads the manifest and
all 12 artifacts from that commit, hashes the raw bytes, and fails if the
entry count differs or any hash mismatches:

```bash
python - <<'PYTHON'
import hashlib
import json
import subprocess
import sys

revision = "0d7861219fb4b1ee1ef0e747ed281ac96fd5edb1"
base = "reports/performance/evidence/1117a76a578cc7315cfe62823b8d5d7c6759b2af/run_2"

def read_blob(path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"])

manifest = json.loads(read_blob(f"{base}/manifest.json"))
entries = [
    (path, expected)
    for run in manifest["runs"]
    for path, expected in run["artifacts_sha256"].items()
]
if len(entries) != 12:
    sys.exit(f"Expected 12 entries, found {len(entries)}")
mismatches = 0
for path, expected in entries:
    actual = hashlib.sha256(read_blob(f"{base}/{path}")).hexdigest()
    if actual != expected:
        print(f"Mismatch: {path}: expected {expected}, got {actual}")
        mismatches += 1
exit_code = int(mismatches != 0)
print(f"Checked: {len(entries)}")
print(f"Mismatches: {mismatches}")
print(f"Exit {exit_code}")
sys.exit(exit_code)
PYTHON
```

Actual output on 2026-10-20 (Python 3.14.4, Git 2.53.0; process exit code 0):

```text
Checked: 12
Mismatches: 0
Exit 0
```

| Path | SHA-256 |
| --- | --- |
| `N10/N10-n1j0nze5/merge_scaling_N10.json` | `da12950b0b068ed293d82d3d88031e5a11ec92a8abad2e1e0e97a4d94c24c35a` |
| `N10/N10-n1j0nze5/observations.jsonl` | `16c27e17e0c9a2bbe47d0159459ecc587a9ff9b5f34593255789e6766fb4fbc8` |
| `N10/pytest.log` | `338743c28809a8ea1a6b553211dd350d95af4e29c4f6afcb90584a4fabe5ef98` |
| `N10/time.txt` | `83cc611c839087960d8bbef89f750a9fee6b5d9df9312265d199afa4498c1772` |
| `N50/N50-9btidy6p/merge_scaling_N50.json` | `d998252f9d8238138a9b44310f6b7ac1cefd5b2c8f8f65c88284c2618666e23a` |
| `N50/N50-9btidy6p/observations.jsonl` | `e6d0a5f7cdb3219de4f4ea2760b7ff67495e20742bb5a5fb7ef60794d5b974c3` |
| `N50/pytest.log` | `6460136a355b3ee5168b4b9137f25e7d817397068bd8afdba7fd1d47a807130e` |
| `N50/time.txt` | `7c5f52ebd205b736281f41306dd6c7e8133203b6d18dea7d89aa310175962831` |
| `N100/N100-yevzmbf8/merge_scaling_N100.json` | `18bcedb8d09b3519474f3e0da94fde490676a26fcda4948e5433c4181b138642` |
| `N100/N100-yevzmbf8/observations.jsonl` | `e4033f9b54e6a62d03ddccc223fd8a707b4fc4e340011fb1bd9b82b1cf48274e` |
| `N100/pytest.log` | `bfa68dd8e72f932f520c505123c95a2c72c3d2d8561ba47eb21b3eb8ec02fcfb` |
| `N100/time.txt` | `07bbdbc42d09b2b233fff99719cf0284ff6ea75c297106aac84f45e58994f8e0` |

## Boundaries

In scope for this direction: file accumulation between runs on a table that
outlives one process. Out of scope: changing `batch_size`, changing
`SilverWriteMode.MERGE`, checkpoint/restart redesign, and calling `VACUUM`
on every successful run.

`SilverWriter.optimize` and `SilverWriter.vacuum` already exist
(`src/bioetl/infrastructure/storage/silver/maintenance_mixin.py`). Calling
them is a later change. Default retention still applies. An immediate
`VACUUM` after `OPTIMIZE` does not remove files created in the same run
when retention is left unchanged.

## Later latency proof

No new benchmark is required to select this direction. A later claim that
latency improved needs a controlled A/B on the same source SHA, the same
initial table state, and the same workload. Account for `OPTIMIZE` cost
separately from the following run. One new run compared with historical
`run_2` is not that comparison.

## Residual risks

- The within-run curve from 0.0362 s to 0.1314 s remains after this direction.
- `OPTIMIZE` duration and RSS are unmeasured.
- Automatic `VACUUM` can delete files readers still need if retention is tightened. This direction does not tighten it.
- The harness uses batch 500, overlap 0.2, and an empty table. Production batch 1000 is not in `run_2`.
- Peak RSS is the whole pytest process, not Delta alone.
- Current `main` has no `run_2` evidence surface. The `0d7861219f` permalinks above preserve provenance only.

## Acceptance

GitHub-owner acceptance is still required. This note does not close #12042
and does not start production work.
