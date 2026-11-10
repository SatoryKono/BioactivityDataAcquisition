# 12553 Runtime Acceptance Report

Acceptance remains partial pending independent verification. Issue #12553 remains open.
Static inventory runtime_result stays NOT_RUN_12553; K2 code and K3 validator/tests are unchanged.

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

## K4 and K5: work in progress

The 207-resource register and actual ARTIFACT_REFRESH check/update/check logs
will follow in subsequent commits. No complete lifecycle or clean-tree claim
is made at this intermediate stage.

## Revision semantics

A tracked receipt cannot contain its own containing commit's SHA or full tree
hash: writing either changes that identity. Receipts name actual execution
revisions. The final PR passport separately identifies the published head and
any differences from execution revisions; evidence additions are not silently
presented as an exact-head rerun.
