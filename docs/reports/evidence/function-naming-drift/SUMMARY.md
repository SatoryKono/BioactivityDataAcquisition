# Сводка evidence: function-naming-drift

Дата: 2026-03-23
Статус: актуализировано как historical-trigger-plus-watchlist pack

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Примечание о rebaseline: первая naming wave уже закрыла самые misleading
runtime seams. Этот pack теперь лучше читать как historical trigger и residual
watchlist для second-wave object/function-family convergence, а не как описание
широкого текущего runtime drift.

## Созданные объекты evidence

- `EV-function-naming-drift-vectorized-is-predicates-return-series-not-bool`
- `EV-function-naming-drift-composition-service-getters-bootstrap-and-construct-services`
- `EV-function-naming-drift-create-pipeline-runner-is-bootstrap-orchestrator-not-simple-constructor`
- `EV-function-naming-drift-build-result-build-request-repeats-result-noun-and-constructs-request`
- `EV-function-naming-drift-run-all-validate-provider-returns-status-plus-error`
- `EV-function-naming-drift-resource-manager-getters-bootstrap-created-managers`

## Проверка gate

Minimum evidence required: `5`

Collected: `6`

Статус gate: `PASSED`

## Сводка evidence

| ID                                                                                               | Claim Summary                                                                                    | Confidence |
| ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ | ---------- |
| EV-function-naming-drift-vectorized-is-predicates-return-series-not-bool                         | Remaining `is_*` Pandera helpers return `pd.Series` masks, not scalar bools                      | 0.97       |
| EV-function-naming-drift-composition-service-getters-bootstrap-and-construct-services            | composition `get_*_service()` helpers bootstrap services instead of looking them up              | 0.90       |
| EV-function-naming-drift-create-pipeline-runner-is-bootstrap-orchestrator-not-simple-constructor | pipeline runner creation is a bootstrap/orchestration path                                       | 0.88       |
| EV-function-naming-drift-build-result-build-request-repeats-result-noun-and-constructs-request   | `build_result_build_request()` repeats the result noun chain and returns a request object        | 0.83       |
| EV-function-naming-drift-run-all-validate-provider-returns-status-plus-error                     | `validate_provider()` returns a boolean+error pair and gates run-all planning                    | 0.86       |
| EV-function-naming-drift-resource-manager-getters-bootstrap-created-managers                     | pipeline-scoped resource manager getters bootstrap managers rather than retrieving existing ones | 0.90       |

## Ключевые выводы

- The sharpest first-wave naming defects from the earlier pass are now gone; this pack no longer describes a broad active runtime naming problem.
- The remaining evidence is narrower and mostly interpretive: accepted bootstrap facades, a few tuple-return or request-assembly helper names, and the Pandera scalar-vs-vectorized predicate family.
- `create_pipeline_runner()` and composition-root bootstrap getters are now better read as reviewed-and-retained seams unless future code changes make their contracts harder to explain.
- The strongest still-open semantic mismatch in this pack is the Pandera scalar-vs-vectorized `is_*` family, now narrowed to `is_non_negative()` and `is_positive()`.

## Оставшиеся пробелы

- This pack samples the current hotspot families only; it does not claim every function or method in the repo is a naming defect.
- Some bootstrap-heavy accessors are still tolerated by design, so the evidence here is about contract clarity rather than a blanket rename mandate.
- Any future cleanup beyond these hotspots should be justified by new evidence, not by the older removed helper names.
