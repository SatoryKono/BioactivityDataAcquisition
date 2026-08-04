______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-16'

______________________________________________________________________

# Archive Index

This repository path exists as the stable archive entrypoint referenced by
current documentation.

## Purpose

- Preserve a canonical repository-path target for historical and superseded
  materials.
- Keep archive references resolvable even though archive content is excluded
  from the published MkDocs navigation by default.

## Current Archive Entry Points

- [Operations Archive Index](../05-operations/archive-index.md) — published
  archive lane for historical operational and deployment material.
- [Plans Index](../plans/README.md) — retained planning artifacts that may still
  provide useful historical context.
- [Archived Plans Index](plans/README.md) — completed or superseded plan
  artifacts moved out of the active plan set.
- [Archived Engineering](engineering/README.md) — closeouts relocated from
  `docs/05-engineering/` (DOC-GOV-08).
- [Archived Fix Notes](fixes/) — one-off Windows/WSL and dependency fix notes
  relocated from `docs/fixes/` (docs audit cycle 1 / #7420).
- [Archived Refactoring Plans](refactoring_plans/) — completed naming/refactor
  plans relocated from `docs/refactoring_plans/` (#7420).
- [Archived Filters Migration Prose](filters/) — historical silver→gold
  migration plan and retired draft relocated from `docs/filters/` (#7428).
- [Archived Tools](tools/) — obsolete pygrok CLI notes (#7432).
- [Archived Dashboard UX Checks](reports/dashboard-ux-checks/) — dated UX
  residual reports (#7433); active gate stays at `docs/reports/dashboard-ux-checks/`.
- [Archived Reports Index](reports/README.md) — superseded documentation-audit
  issue packs and generated report snapshots moved out of active report
  surfaces.
- `reports/quality/` and `reports/semantic_pipeline_audit/` — superseded
  quality and semantic report snapshots moved out of active report surfaces.
- [Reports Index](../reports/index.md) — curated repo-only evidence and bounded
  internal reports.
- [Root Status Artifacts](root-status-artifacts/README.md) — historical root
  completion notes, sync summaries, and one-off setup/recovery artifacts moved
  out of the repository root.
- [Pipeline Specifications](pipelines/) — historical pipeline specifications and legacy contract details.

## Usage Rules

- Treat archive material as historical context, not as current normative
  guidance.
- Prefer active documentation under `docs/00-05` for current workflows,
  contracts, and architecture statements.
- When an archive page is still linked from an active document, the link should
  explain why that historical context remains relevant.
- `docs/99-archive/**` is a blocked cleanup zone in
  `configs/quality/repo_structure_catalog.yaml`; archive material must not be
  swept up by broad structure-cleanup passes.
