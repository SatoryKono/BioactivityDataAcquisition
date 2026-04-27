# Project File Structure — Decisions Summary

Status: active

## Decisions

- Canonical source layout follows `src/bioetl/` with domain, application,
  infrastructure, composition, and interfaces layers.
- Test files mirror the source layout under `tests/unit/`, `tests/integration/`,
  and `tests/architecture/`.
- Generated reports and evidence packs live under `docs/reports/` and
  `reports/quality/`.
