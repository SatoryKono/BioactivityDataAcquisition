# Сводка evidence: variable-naming-drift

Дата: 2026-03-23
Статус: завершено

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Примечание о rebaseline: completed runtime and CLI cleanup passes plus
`vacuum_enabled_override` moved this pack firmly into historical-trigger mode;
remaining work is now optional and narrow.

## Созданные объекты evidence

1. `EV-variable-naming-drift-pipeline-bootstrap-ctx-abbreviation-hides-context-object`
1. `EV-variable-naming-drift-run-all-registry-resolution-uses-opaque-ctx-and-candidate-temporaries`
1. `EV-variable-naming-drift-gold-dq-dispatch-uses-handler-and-result-temporaries`
1. `EV-variable-naming-drift-pipelinecontext-vacuum-enabled-is-tristate-but-reads-like-bool`
1. `EV-variable-naming-drift-tests-reinforce-ctx-shorthand-in-pipelinecontext-fixtures`
1. `EV-variable-naming-drift-composite-runner-preflight-uses-generic-context-and-result-temporaries`
1. `EV-variable-naming-drift-rules-canonicalize-pipelinecontext-but-code-uses-ctx-shorthand`

## Проверка gate

Minimum evidence required: `5`

Collected: `7`

Статус gate: `PASSED`

## Ключевые выводы

- This pack remains useful as historical trigger evidence, but several highest-signal runtime seams are now remediated in code.
- Core composition and CLI paths no longer rely as heavily on opaque `ctx`/`result` shorthands in the specific hotspots sampled by this pack; recent runtime passes introduced `click_context`, `run_context`, `run_result`, and `pipeline_run_result` in those seams.
- The strongest semantic mismatch in this pack is now narrowed rather than fully open: `PipelineRunContext.vacuum_enabled` was renamed to `vacuum_enabled_override`, while broader `VacuumSettings.enabled` semantics remain an intentional follow-up design question.
- Tests and project rules still reinforce the canonical `PipelineContext` naming baseline, which remains useful calibration for any future cleanup.

## Gaps

- This pack samples the most important hotspots only; it does not claim every short local name in the repo is a defect.
- Some short names are still acceptable in narrow helper scopes and were not treated as evidence here.
- The remaining open work is now smaller: deciding whether any additional variable-level cleanup beyond the completed runtime/CLI passes is worth the churn.
