# Evidence Index (curated thin surface)

Status: rebaselined 2026-07-28 (DOC-GOV-01 / #6873)

## Freshness Model

- `SUMMARY.md`, this `INDEX.md`, and cross-synthesis pages are the preferred
  refresh layer for evidence packs.
- Raw notes, dated backlog items, and historical shard captures should usually
  remain unchanged unless they are themselves the subject of the audit.
- If a formerly current recommendation becomes historical trigger evidence,
  mark that fact in the top summary instead of rewriting the whole pack.
- **Rebaseline (2026-07-28):** bulk historical packs moved to
  `reports/docs-evidence/`. This path retains only curated governance
  manifests. Treat bulk relocated packs as historical unless re-verified.

## Surface Type

- `docs/reports/evidence/` is a **repo-only curated evidence surface**.
- Bulk research packs live under **`reports/docs-evidence/`** (working /
  historical; not MkDocs SSOT).
- Evidence packs never replace active guidance in `docs/00-project/`,
  `docs/02-architecture/`, `docs/03-guides/`, or `docs/04-reference/`.
- When evidence and canonical guidance disagree, verify against code/config
  and reconcile; do not treat evidence as automatic authority.

## Curated retained packages (tracked / governance)

| Package | Role |
| --- | --- |
| `project-test-health/` | Non-canonical test-health backlog signal + freshness metadata |
| `project-legacy-compatibility-remediation/` | Legacy seam remediation decisions/risks |
| `project-package-topology/` | Package topology decisions |
| `technical-debt/` | Historical tech-debt rebaseline markers |

## Bulk historical inventory

Full pack inventory after DOC-GOV-01 relocate:

- Root: [reports/docs-evidence/](../../../reports/docs-evidence/)
- Orientation: [reports/docs-evidence/README.md](../../../reports/docs-evidence/README.md)

Do **not** re-copy bulk packs into `docs/reports/evidence/`. New investigations
write under `reports/` first.

## Related

- [docs/reports/README.md](../README.md)
- [docs/reports/index.md](../index.md)
- [reports/README.md](../../../reports/README.md)
