# Сводка evidence: reference-guide-doc-drift

Дата: 2026-03-21
Статус: ребейзлайнено под текущее состояние

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

## Созданные объекты evidence

1. `EV-reference-guide-doc-drift-application-services-now-separates-root-and-nested-symbols`
1. `EV-reference-guide-doc-drift-application-composite-now-separates-root-and-nested-symbols`
1. `EV-reference-guide-doc-drift-composition-factories-now-separates-root-and-nested-symbols`
1. `EV-reference-guide-doc-drift-runtime-builders-now-state-root-export-boundary-explicitly`
1. `EV-reference-guide-doc-drift-pipeline-configuration-now-uses-category-based-inventory`

## Проверка gate

Minimum evidence required: `5`

Collected: `5`

Статус gate: `PASSED`

## Сводка evidence

| ID                                                                                       | Claim Summary                                                                                                                     | Confidence |
| ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| EV-reference-guide-doc-drift-application-services-now-separates-root-and-nested-symbols  | `application.md` now separates the `application.services` package-root facade from nested service symbols.                        | 0.97       |
| EV-reference-guide-doc-drift-application-composite-now-separates-root-and-nested-symbols | `application.md` now separates the `application.composite` package-root facade from nested composite helpers.                     | 0.97       |
| EV-reference-guide-doc-drift-composition-factories-now-separates-root-and-nested-symbols | `composition.md` now separates the `composition.factories` root facade from nested factory symbols.                               | 0.97       |
| EV-reference-guide-doc-drift-runtime-builders-now-state-root-export-boundary-explicitly  | `composition.md` now states the `composition.runtime_builders` root-export boundary explicitly and keeps nested symbols distinct. | 0.97       |
| EV-reference-guide-doc-drift-pipeline-configuration-now-uses-category-based-inventory    | The pipeline configuration guide now uses category-based inventory wording instead of a brittle total-YAML count.                 | 0.98       |

## Ключевые выводы

- The sampled reference and guide pages now align with the narrow-facade model used by the codebase.
- The main improvement is structural: package-root exports and nested symbols are now distinguished instead of being blended together.
- The config guide no longer depends on a fast-drifting filesystem total, which removes one recurring source of stale documentation.
