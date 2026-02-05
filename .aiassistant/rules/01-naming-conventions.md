---
apply: always
---

Keep doc navigation predictable.

> Scope:
> - USE WHEN writing or modifying documentation files or file names; enforce lowercase-hyphen names and NN- sequencing
> - Use when editing files matching: `docs/**/*.md`, `**/INDEX.md`, `**/README.md`
# GOAL

Keep doc navigation predictable.

## RULES

- Filenames in English, lowercase, words separated by hyphens (`-`). **Underscores (`_`) MUST NOT be used** in documentation filenames.
- Sequenced docs use two-digit prefix `NN-` (e.g., `01-overview.md`).
- Pipeline docs format: `NN-<entity>-<provider>-<topic>.md` (e.g., `09-document-chembl-extraction.md`).
- H1 heading MUST duplicate filename in Title Case.
- Internal anchors from `##` headings in kebab-case.
- Auto-generated sections MUST be marked: `<!-- generated -->`.
- Landing-page naming details live in `docs-landing-pages-index-readme.mdc`.
- Canonical identifiers: code/configs use `snake_case`, docs filenames use `kebab-case`.

## EXAMPLES

Valid: 
- `docs/etl_contract/00-etl-overview.md`
- `docs/pipelines/10-chembl-pipelines-catalog.md`
- `docs/pipelines/chembl/activity/09-activity-chembl-extraction.md`
- `docs/INDEX.md`

Invalid: 
- `Docs/Overview.MD` (uppercase)
- `etlOverview.md` (camelCase)
- `01_overview.md` (underscores instead of hyphens)
- `docs/pipelines/chembl/activity/extraction.md` (missing NN- prefix)

## REFERENCE

See [docs/styleguide/00-naming-conventions.md](../../docs/styleguide/00-naming-conventions.md) for detailed documentation.
