# Documentation Audit 2026-06-19 Issue Pack

This pack converts the validated 2026-06-19 documentation audit into a
publish-ready GitHub issue set.

## Scope

The pack covers only findings re-verified against the current repository state:

- invalid CLI examples in deployment/bootstrap docs
- stale Grafana provisioning paths in active observability/dashboard docs
- stale Windows mixed-checkout pytest examples
- architecture/ADR drift in control-plane and observability decision docs
- stale current-state inventory fields and missing domain control-plane
  reference coverage

## Issue Set

1. `DOC-AUDIT-001` — fix invalid BioETL CLI examples in deployment and bootstrap docs — [#5438](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5438)
2. `DOC-AUDIT-002` — refresh Grafana provisioning path docs to the current split datasource layout — [#5439](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5439)
3. `DOC-AUDIT-003` — align mixed Windows + WSL pytest examples with the current xdist worker cap — [#5440](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5440)
4. `DOC-AUDIT-004` — repair control-plane ADR cross-links and ADR-022 observability guidance — [#5441](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5441)
5. `DOC-AUDIT-005` — refresh current-state inventory and publish a dedicated domain control-plane reference page — [#5442](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5442)

## Recommended Execution Order

### Phase 1: operator-facing correctness

1. `DOC-AUDIT-001`
2. `DOC-AUDIT-002`
3. `DOC-AUDIT-003`

### Phase 2: architecture/reference cleanup

4. `DOC-AUDIT-004`
5. `DOC-AUDIT-005`

## Notes

- This pack intentionally does **not** propose runtime refactoring.
- The issues are documentation-governance workstreams derived from
  [review_documentation-cascade-audit_20260619_1230.md](../../reports/codex/review_documentation-cascade-audit_20260619_1230.md).
- The split keeps immediate operator-facing breakage separate from slower
  architecture/reference cleanup.
