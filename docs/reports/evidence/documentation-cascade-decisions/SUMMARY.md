# Summary: documentation-cascade-decisions

Date: 2026-03-26
Status: completed

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

## Evidence Gate

- semantic evidence objects: `9`
- result: `PASSED`

## Accepted Position

- Publish dedicated composite-validation reference pages and restore internal links.
- Treat `_diagnostic` as hybrid contract:
  - strict versioned core envelope,
  - optional correlation anchors with explicit gap accounting.
- Keep current all-top-level `run-manifest diff` semantics in this wave; defer
  reproducibility-only filtering to separate feature work.
- Follow-up gate revalidation confirms no new link/spec/config/drift regressions
  in audited shards.
- Coverage command surfaces are now aligned on `coverage combine --keep`.
- Published ORCHESTRATION runtime mirror is re-synced with canonical `.codex` source.
