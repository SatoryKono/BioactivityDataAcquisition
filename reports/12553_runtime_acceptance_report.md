# 12553 Runtime Acceptance Report

Acceptance remains partial pending independent verification. Issue #12553 remains open.
Static inventory runtime_result stays NOT_RUN_12553; K2 code and K3 validator/tests are unchanged.

## Packaging and review remediation

The full local machine bundle is in evidence.zip under the bundle directory,
with evidence.zip.sha256 beside it. All filenames cited below are archive
entries unless they are baseline loose files. Exact-head CI still uploads the
separate raw files. This preserves the canonical documentation inventory from
main without excluding this task from any documentation gate.

The registry now rejects unbound observer versions and confirms lock boundaries
only after successful, non-skipped execution of all five control tests. The
build function is split into focused helpers; quality thresholds are unchanged.

## K1: command evidence

Bundle: reports/audit-runs/12553-runtime-acceptance/.
Each new run has separate *-stdout.txt, *-stderr.txt, *-exit-code.txt and
*-command.json files with argv, timestamps, timeout, pre-run status, full
checked HEAD and tree. Empty stderr means an empty captured stream.
The *-rerun-* attempts preserve the initial Windows pytest-cache access failure
(exit 1). Successful subsequent runs disable only pytest's cache provider.
The actual review-controls output supersedes the previous one-line placeholder.
Historical missing stderr cannot be reconstructed retroactively.

## K2: accepted negative control

The control uses monkeypatch, not pytester. An isolated real RLock omits release
on context exit; the existing assertion detects missing-release. The fixture
releases the lock during cleanup. Normal/error lock tests substitute the inner
collector and establish the lock boundary, not execution of every inner resource.

## K3: accepted static contract

scripts/engineering/qa/external_resource_inventory.py and its tests are unchanged.
Execution is reported separately, never by replacing NOT_RUN_12553 in the inventory.

## K4: complete accounting, partial execution

coverage-register.json and coverage-register.md account for all 207 resources:
85 EXECUTED_PARTIAL and 122 NOT_VERIFIABLE, with individual reasons and source
sites. All five original scenario expectations are retained. Traces observe real
file/task/executor/iterator lifetimes. Full scenario-barrier acceptance remains
NOT_VERIFIABLE; a green test or a test name is not promoted to runtime PASS.

## K5: actual refresh evidence

The original artifact-refresh-check-before/update/check-after sequence exited
1/0/1; its final failure reported test-governance input drift while the observer
was still being finalized. Those genuine failure logs are retained.
The stable artifact-refresh-final-check-before/update/check-after sequence
exited 1/0/0, with CHECK: governance artifacts current in the final stdout.
All six commands have separate raw stdout/stderr and exit-code/command files.
Generated outputs are restored to origin/main after validation, as explicitly
required by the task. The successful refresh describes the measured temporary
generated state; it does not assert freshness after restoration.
Local clean-status evidence is captured at a committed checkpoint; exact final
head status and SHA/tree are recorded by the branch-scoped CI artifact.

## Validation and boundaries

Latest local owning groups: files/config 862 passed, 7 skipped; tasks/executors
85 passed; storage/export 159 passed, 4 skipped; HTTP/telemetry 232 passed;
health/composition 1016 passed, 4 skipped; unchanged review controls 5 passed.
Windows skips include fcntl and symlink privileges and remain explicit.
Evidence contracts plus unchanged K3 tests: 132 passed. Final gzip-register
contracts: 3 passed. Ruff, full docs links, docs drift and full-tree gate passed.
Earlier docs-links failures caused by the new workflow catalog entry are retained;
docs-links-verified is the successful full rerun. Runtime mirrors are untouched;
no mirror synchronization is needed. Debt budgets are unchanged after restoration.
Memory pre-task was read-only; no memory post-task/session note was written.

## Exact published-head evidence

.github/workflows/runtime-acceptance-12553.yml checks out github.sha explicitly
and reruns the owning suites with outputs outside the checkout. Its uploaded
artifact runtime-12553-<full SHA> contains the same bundle path, checked-head-sha.txt,
checked-tree-sha.txt, source/fixture/harness hashes, coverage register, streams,
exit codes and final-worktree-status-stdout.txt. The PR passport supplies the
actual run/artifact URL and result once observed. Merely adding this workflow
is not proof it ran or passed. It has no production endpoint dependency and
its job is restricted to the task branch. Retire it after issue acceptance.
Structured observations are stored losslessly as JSON.gz to keep raw trace
content while reducing checkout size.

## Revision semantics

A tracked receipt cannot contain its own containing commit's SHA or full tree
hash: writing either changes that identity. Receipts name actual execution
revisions. The final PR passport separately identifies the published head and
any differences from execution revisions; evidence additions are not silently
presented as an exact-head rerun.
