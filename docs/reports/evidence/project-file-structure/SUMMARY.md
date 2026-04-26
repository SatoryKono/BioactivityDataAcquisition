# Сводка evidence: project-file-structure

Дата: 2026-03-26
Статус: завершено; freshness note added

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Примечание о follow-up: cleanup wave 2026-03-26 архивировала stray root-level
working docs и перевела merged export artifacts в generated-on-demand режим.
Это слегка упростило repo surface, но не изменило базовую интерпретацию пакета:
верхнеуровневое дерево всё так же читается через стабильные primary zones.

> Это summary — repo-only evidence layer для file-structure
> interpretation. Он полезен для repo-shape calibration и traceability, но не
> заменяет canonical project guidance в `docs/00-project/` и active
> architecture/reference docs.

## Созданные объекты evidence

1. `EV-project-file-structure-top-level-repo-is-organized-into-seven-primary-zones`
1. `EV-project-file-structure-src-bioetl-is-partitioned-into-five-main-runtime-layers`
1. `EV-project-file-structure-configs-separate-schema-base-provider-entity-composite-and-quality-assets`
1. `EV-project-file-structure-tests-are-partitioned-by-test-purpose-and-scope`
1. `EV-project-file-structure-docs-separate-active-archive-plans-and-evidence-spaces`
1. `EV-project-file-structure-scripts-are-grouped-by-operational-function-with-an-archive-subtree`

## Проверка gate

Minimum evidence required: `5`

Collected: `6`

Статус gate: `PASSED`

## Ключевые выводы

- The repository has a stable top-level split between source, configs, tests, scripts, docs, and reports.
- `src/bioetl/` follows a clear five-layer package partition at the first level.
- Supporting trees (`configs`, `tests`, `docs`, `scripts`) are also grouped by function rather than remaining flat.

## Gaps

- This package describes structure only; it does not evaluate ownership, code health, or whether each subtree is equally active.
