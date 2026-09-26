______________________________________________________________________

Version: 1.0.0
Status: Accepted (Implemented #10490)
Class: published
Owner: BioETL Team
Last verified: '2026-09-16'

______________________________________________________________________

# ADR-061: Persisted selected-run assessment

**Date:** 2026-09-16
**Status:** Accepted (implemented by PR #10490, merged 2026-09-16)
**Linked issues:** #10486, #10487, #10488, #10489

## Context

Prometheus freshness and dashboard ranges describe current telemetry and chart
coverage. They cannot define the outcome of a completed run. A successful execution
also does not prove that all checks ran or that replay is currently allowed.
The strict v1 report schema rejects new top-level evidence fields.

## Decision

Publish new pipeline reports as `pipeline_run_report_v2`, with optional observations
and a content-addressed `selected_run_snapshot_v1` envelope. Keep the v1 schema
semantically unchanged. Readers accept v1 and v2; absent snapshots remain explicitly
incomplete. Persist exact identity and executed checks in six domains. Commit each
immutable revision before replacing the report; retry interrupted publication
idempotently. Publish workflow children before the parent commit and retry the same
workflow report after repairing invalid child evidence.

Use versioned deterministic assessment rules. `selected-run-v1` remains verifiable;
`selected-run-v2` additionally treats explicit `io.skip_gold=true` as Data Validation
N/A. Never rewrite old revisions during reads. Unknown versions fail closed. An
explicit new publication creates a new revision and records the rules version.

Archive keys include the validated report/revision inventory when report evidence
is configured. Late workflow observations create another archive version; previous
packs remain untouched. Every revision must belong to the selected run and pipeline.
CURRENT diagnostics use the existing runtime clock seam and remain separate.

## Migration

Deploy dual-version readers before v2 writers. Consumers validating new report
files must select `pipeline_run_report.v2.json` by `schema_version`. Retain v1 fixtures
and old reports unchanged. Do not backfill unexecuted checks. The selected-run API
returns its rules version, revision, execution, checks, completeness and availability
in both success and unavailable responses. Existing chart endpoints stay available.

## Rollback

Stop new v2 writes by rolling back the writer deployment; retain dual-version readers
and all v2 report/revision/archive files. Do not relabel a v2 report as v1 or replace
its saved evaluation. If an old v1-only consumer must be restored, point it to its
preserved v1 report root and retain the newer root for later forward migration.
Dashboard rollback uses the prior generated dashboards; it does not delete evidence.

## Consequences and validation

Local files remain the source of evidence; no new external service is required.
Disk usage grows with explicitly published revisions. Missing/corrupt evidence is
never a cached OK. Tests cover aggregate selectors, ambiguous identity, active
workflow context, rejected foreign revisions, archive version advance, corrupt
serialization, legacy rule verification and v2 schema structure. Browser and CI
acceptance are reported separately; this ADR does not assert release approval.
