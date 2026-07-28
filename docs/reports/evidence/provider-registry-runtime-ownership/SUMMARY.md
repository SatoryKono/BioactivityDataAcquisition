# Provider Registry Runtime Ownership Evidence Summary

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Примечание о rebaseline: the runtime seam is still the correct stopping point for the current repo state; no new caller-driven case for explicit runtime instance ownership has emerged.

## Question

Do runtime/bootstrap paths still need explicit `ProviderRegistry` instance
ownership, or is the current named runtime bootstrap seam already sufficient?

## Evidence Collected

- `EV-provider-registry-runtime-bootstrap-now-flows-through-named-seam`
- `EV-provider-registry-runtime-tests-now-bind-to-the-named-bootstrap-seam`
- `EV-provider-registry-runtime-ratchet-already-prevents-raw-regression`
- `EV-provider-registry-explicit-instance-threading-already-pays-off-in-local-factory-seams`
- `EV-provider-registry-runtime-callers-do-not-yet-own-provider-instance-lifecycle`
- `EV-provider-registry-governance-still-defers-runtime-instance-ownership-decision`

## What The Evidence Currently Supports

1. The previous runtime problem has already been reduced from raw
   `ProviderRegistry.ensure_loaded()` calls to an explicit named bootstrap seam.
1. That seam is now directly exercised by unit tests and protected by an
   architecture ratchet.
1. Explicit `ProviderRegistry` instance threading is clearly beneficial in
   datasource and nearby factory seams where provider lookup is naturally local.
1. Runtime/bootstrap entrypoints still look like owners of pipeline-registry
   lifecycle and bootstrap ordering, not natural owners of `ProviderRegistry`
   instance lifecycle.

## Текущая интерпретация Boundary

This evidence pack supports a conservative interpretation:

- the current named runtime bootstrap seam appears sufficient for the present
  runtime architecture;
- explicit runtime `ProviderRegistry` instance ownership is not yet supported as
  a necessary next step by the current code/test/governance evidence.

## Remaining Gap

What is still missing is a concrete runtime caller that naturally owns a
`ProviderRegistry` instance and would become materially easier to reason about,
test, or isolate if that instance were threaded explicitly. Until such a caller
exists, the cost/benefit case for RF-07D4 remains weak.
