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

## Integrated W47 and CI configuration repair

W47 completed all 17 shards on e4181fd47bdbfee8e537a5c5edc78631bbc197a6:
32,866 passed, 187 skipped, zero failures/errors, line 99.70%, branch 94.34%,
config_root 40/40 lines and 18/18 branches. All 17 raw database hashes match
the manifest. Source digest remains 4db123e5e95045405ceb710e2425c1cd0e733fb6a225dccc7fc4146c63eaacb5;
test digest is 8eda05d84247514c788836919a2df950d4bc92ac06948537a8040b6c9942f9f6.

CircleCI pipeline 119 failed before execution because accepted main contained
two environment mappings in test-integration. Removing the redundant two-line
mapping preserves all three thread limits. Unique-key YAML parsing and all
39 CircleCI architecture contracts passed. The full integrated architecture
diagnostic completed 5,004 cases with one failure and 76 skips: its sole
failure was the reviewed skip census for the two already-merged RF-022
opt-in entrypoints. The census now records the actual two guards and their
mutually exclusive selection. All 57 owning tests passed without skips.

Only squash merging is enabled in the repository. W47's branch commit must
not be relabelled as an ancestral main measurement. W48 is running directly
on main c61913580698f70b181ae3e9ac852c631f02a878 for post-squash telemetry.
Final independent CI acceptance and issue closure remain pending.


## Main-bound W48 telemetry and post-merge remediation

PR #11944 was squash-merged into 5aca24359c040cb236d691996438daeb16801160.
W48 ran directly on its unchanged-source/test ancestor
c61913580698f70b181ae3e9ac852c631f02a878 and completed all 17 shards:
32,866 passed, 187 skipped, zero failures/errors; line 99.70%, branch 94.34%,
config_root 40/40 lines and 18/18 branches. All database, JUnit telemetry and
XML hashes were independently checked. Canonical telemetry was generated in
the original measurement checkout and copied byte-exactly with the original
manifest identities. This keeps local_single_host trust; it is not CI ADMIT.

The architecture retry timed out in detect-secrets; its unchanged focused
repeat passed in 19.861 seconds. A subsequent suite was interrupted at 54%
without terminating exit/JUnit. Both diagnostics are preserved and do not
establish full architecture acceptance. The post-merge branch fixes the
CircleCI duplicate environment mapping and the reviewed census of the two
already-merged RF-022 opt-in guards. No test skips or debt budgets were added.
Final independent workflow acceptance and issue closure remain pending.


W48 raw measured candidate covers the complete 2,552-module roster. Its direct
historical comparison exits 1 for 80 other module rows; see
[comparison ledger](full-coverage-wave-48/comparison-ledger.json). config_root
measures 100%; retained module percentages have not been lowered. No global
coverage-nonregression claim is made. Post-merge owning contracts: 96 passed,
zero skips; full docs verification exited 0. A complete final architecture
run and independent CI lifecycle acceptance still remain pending.
