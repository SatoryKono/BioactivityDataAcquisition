> Scope:
> - USE WHEN writing or modifying documentation files or file names; enforce lowercase-hyphen names and NN- sequencing
> - Use when editing files matching: `docs/**/*.md`, `**/INDEX.md`, `**/README.md`
# GOAL

Keep doc navigation predictable.

## RULES

- Filenames in English, lowercase, words separated by hyphens.
- Sequenced docs use two-digit prefix `NN-` (e.g., `01-overview.md`).
- Landing-page naming details live in `docs-landing-pages-index-readme.mdc`.

## EXAMPLES

Valid: `docs/etl_contract/00-etl-overview.md`, `docs/pipelines/10-chembl-pipelines-catalog.md`
Invalid: `Docs/Overview.MD`, `etlOverview.md`, `01_overview.md`

## REFERENCE

See [docs/styleguide/00-naming-conventions.md](../../docs/styleguide/00-naming-conventions.md) for detailed documentation.
