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
