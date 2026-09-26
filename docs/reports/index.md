# Reports Index (Non-Normative)

Thin curated reports surface (DOC-GOV-01). **Non-normative**: authoritative
guidance lives under `docs/00-05`.

## Canonical sources

- docs/02-architecture — ADRs, architecture policies, diagrams
- docs/03-guides — implementation and operational guides
- docs/04-reference — pipeline, provider, and contract specifications

## Publication hygiene

- `docs/reports/` is **repo-only** and excluded from MkDocs.
- Bulk evidence packs live under `reports/docs-evidence/` after 2026-07-28.
- top-level `reports/` remains the working area for generated and
  iteration-heavy outputs.

## Boundary contract

- current instructions / contracts → `docs/00-05/`
- curated manifests → `docs/reports/` (thin)
- generated / iterative / bulk evidence → `reports/`
- historical retained context → `docs/99-archive/`

## Main entry points

- this index — curated reports map
- [evidence/INDEX.md](evidence/INDEX.md) — thin evidence + freshness model
- [../../reports/docs-evidence/README.md](../../reports/docs-evidence/README.md)
  — bulk relocated evidence
- [../../reports/README.md](../../reports/README.md) — working-output taxonomy
- [docs/plans/README.md](../plans/README.md) — planning lane (thin)
- [docs/99-archive/README.md](../99-archive/README.md) — archive index

## Allowlisted generated artifacts

- [generated/documentation-cleanup-inventory.md](generated/documentation-cleanup-inventory.md)
- `generated/documentation-cleanup-inventory.json`
- `generated/chembl_matrix_structural_contract_v1.json`
- `generated/pipeline_normalization_field_matrix/`

Use reports for situational evidence; always cross-check canonical docs before
applying changes.
