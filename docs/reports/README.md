# Reports (Non-Normative, thin curated surface)

**Rebaseline:** 2026-07-28 (DOC-GOV-01 / #6873)

This folder is a **thin curated map**, not a dump of working evidence.
Authoritative guidance remains in:

- docs/02-architecture (ADRs, policies, diagrams)
- docs/03-guides (implementation and operations guides)
- docs/04-reference (pipelines, providers, contracts)

## Surface model

| Path | Role |
| --- | --- |
| `docs/reports/README.md` / `index.md` | Orientation for the curated surface |
| `docs/reports/evidence/` | Thin curated manifests only (freshness governance) |
| `docs/reports/generated/` | Allowlisted generated inventories/matrices |
| `reports/docs-evidence/` | Bulk historical evidence packs (relocated) |
| `reports/` | Working / model-specific / iterative outputs |

## Boundary contract

- current instructions / operator workflow / contracts → `docs/00-05/`
- curated repo-only manifests → `docs/reports/` (thin)
- bulk evidence / investigations → `reports/docs-evidence/` or `reports/{LLM}/`
- historical retained context → `docs/99-archive/`

`docs/reports/**` remains a blocked cleanup zone in
`configs/quality/repo_structure_catalog.yaml`. Cleanup stays curated; do not
treat allowlisted manifests as disposable, and do not reintroduce multi-MB
bulk packs into this tree.

## Entry points

- [index.md](index.md)
- [evidence/INDEX.md](evidence/INDEX.md)
- [evidence/README.md](evidence/README.md)
- [../../reports/docs-evidence/README.md](../../reports/docs-evidence/README.md)
- [../../reports/README.md](../../reports/README.md)
