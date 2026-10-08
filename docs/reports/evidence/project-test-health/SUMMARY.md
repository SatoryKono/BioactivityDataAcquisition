---
status: active-non-canonical
last_verified: "2026-10-08"
freshness_window_days: 7
owner: quality
canonical_sources:
  - configs/quality/test_matrix.yaml
  - configs/quality/test_health_reporting.yaml
  - configs/quality/fixture_governance_ledger.yaml
allowed_interpretation: backlog_signal_only
verification_scope: tracked_test_module_inventory
---

# Project Test Health

## Current status

The tracked test-module inventory remains the verification scope for this
summary. Its canonical inputs and machine-readable inventory record remain in
the companion metadata. This page is a non-canonical evidence layer and does
not replace those sources.

The P02 R6 local coverage capture ran on commit
`aff1f4955c7cb5cc3a9a972ab300b9c4bffcae44`, source tree
`20ff5954914c50c111d533b89d4a719dbc9c973c51b486d17385fe1dc6e05f26`, and test
tree `0800468b7a5f706cecd3fd8dbfbe88cfa2d85ca56d6b51d537e39f98bd2c6c07`.
All 17 canonical shards completed with exit code 0: 33,583 JUnit testcase rows,
0 failures, 0 errors, and 205 skips. The combined report measured 99.68% line coverage and
94.28% branch coverage; both configured aggregate gates passed. The run used
one local worker. Its portable, path-free evidence manifest is
[`p02-r6-coverage-manifest.json`](p02-r6-coverage-manifest.json).

This local capture does not establish hosted CI acceptance or make the
architecture suite green. Exact-SHA hosted architecture gates and the full
local architecture suite still report independent governance and code-quality
failures; tracker #12094 remains open. The complete measured module inventory
is bound to the same source hash. It contains no uncovered or unmeasured
modules, and three modules remain below the default 85% per-module floor. These
residuals are preserved rather than hidden by changing thresholds or
historical measurements.

## Required follow-up

- Keep tracker #12094 open until required hosted checks and final review pass.
- Review the three measured modules below 85% as separate coverage work.
- Reconcile older lifecycle, contract, UTC metadata, and security backlog
  signals against their current owners and issues before changing their status.

## Freshness note

Re-verified on 2026-10-08. The path-free manifest records all 17 shard exit
codes, per-shard coverage and JUnit digests, the raw runner-manifest digest,
source/test fingerprints, and aggregate threshold results. The local runner
also retains raw JUnit, log, coverage, and SQLite files under its ignored
scratch directory; those machine-local files are not required to verify the
tracked manifest's recorded outcomes. The tracked `tests/**/test_*.py`
inventory and canonical source files were checked on this revision. This
summary remains backlog signal only, not proof of hosted CI or complete
repository lifecycle acceptance. A fresh evidence-pack rebaseline is required
before it can support broader test-health conclusions.

This summary is a non-canonical repo-only evidence layer. The canonical sources
of truth are:

- `configs/quality/test_matrix.yaml`
- `configs/quality/test_health_reporting.yaml`
- `configs/quality/fixture_governance_ledger.yaml`

Refresh this summary from the next significant test campaign or infrastructure
change, while preserving the distinction between local evidence and hosted
acceptance.
