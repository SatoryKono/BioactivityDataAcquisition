# Config-root post-merge acceptance (#11899)

Main source: `090d7a74c56e9de8db2f96d9a183a9058a55ccc8` (PR #11933 squash).
Measured CircleCI source: `cd50cf3ca72783c49ecdd8a3825b2199101f7c2b`.
Both commits have Git tree `a58149d611dcf1af98e732b25c945dbf088b58cb`.
The CI commit is not an ancestor after squash; the CI identity is preserved.

## Cause and behavior

The earlier R11 selection did not execute the installed-layout fallback at
`config_root.py:32`, the configs-only ancestor rejection, or the missing cwd
configs branch. Rooted-path coverage alone did not exercise these branches.
The merged tests use an isolated synthetic source layout, assert the exact
`source_path.parents[4]` fallback, reject unmarked configs directories, and
assert the repository configs path when preferred cwd configs are absent.
Production resolver behavior and coverage thresholds remain unchanged.

## Independent complete coverage measurement

CircleCI job [1401](https://circleci.com/gh/SatoryKono/BioactivityDataAcquisition/1401)
completed all 17 canonical coverage shards: 32,842 passed, 174 skipped,
zero failures/errors. The combined XML measures config_root at 40/40 lines
and 18/18 branches. Overall line coverage is 99.70%; branch coverage is 94.35%.
The complete job proof remains **STOP** because its separate architecture
receipt failed telemetry freshness and its debt receipt found remote-main drift.
A passing coverage phase does not mean a passing overall CI job.

Original artifacts and identity are preserved in [ci-1401](ci-1401).
The independently checked identity/counts are in
[verified-coverage.json](ci-1401/verified-coverage.json).

## Measured versus retained coverage

The raw candidate has a complete roster of 2,552 source modules. Its direct
per-module historical regression guard exits 1: 81 other module rows measure
below their retained historical percentages. The failures and all differing
rows remain explicit in [adoption-validation-ledger.json](ci-1401/adoption-validation-ledger.json).
These are residual historical comparison findings, not repaired by #11899.

Canonical nonregressing adoption exits 0, preserves historical per-module
floors, and adds no below-85% rows. The adopted inventory records 2,513 fully
covered, 38 partially covered and one no-executable-code module. Retained
percentages are not newly measured percentages. Both canonical command records
and the raw candidate are retained alongside the original inventory.

## Main verification and remaining acceptance

Post-merge owning guards passed (22 tests, zero skips). Full docs verification
passed. The independent CI job exposes the two remaining governance failures;
the telemetry baseline was refreshed through the canonical local-manifest
validator from [W46](full-coverage-wave-46/manifest.json) on reachable main SHA
090d7a74. W46 completed all 17 shards: 32,830 passed, 186 skipped, zero
failures/errors; config_root 40/40 lines and 18/18 branches, overall line
99.70%, branch 94.34%. Platform-specific skips are retained in the JUnit files.
The CI-family generator rebound remote-main/debt artifacts without changing
budgets. W46 remains local evidence, distinct from independent CI job 1401.

Final workflow acceptance and issue closure are pending. Local results retain
`local_single_host` trust and do not claim CI PASS or lifecycle ADMIT.

## Concurrent main movement

During verification main advanced to c6191358 through CI preparation commits
and PR #11935. No `src/bioetl` files changed, but the test roster changed.
W46 still measures SHA 090d7a74 and its original test hash; it is not relabelled
as a measurement of c6191358. The full architecture diagnostic run on 090d7a74
found nine remote-main/debt coherence failures while origin/main moved. Those
failed diagnostics are preserved. The branch must integrate current main and
complete its applicable fresh checks before closure.
