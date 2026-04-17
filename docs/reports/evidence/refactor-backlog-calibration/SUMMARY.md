# Сбор evidence завершён: refactor-backlog-calibration

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

**Создано объектов evidence:** 6
**Gate Статус:** PASSED

## Интерпретация верхнего уровня

- Формальная cross-pack интерпретация теперь находится в [03-synthesis/CROSS-SYNTHESIS.md](./03-synthesis/CROSS-SYNTHESIS.md).
- Принятая planning-позиция теперь находится в [04-decisions/DECISIONS.yaml](./04-decisions/DECISIONS.yaml).
- Активные planning-риски теперь находятся в [05-risks/RISKS.yaml](./05-risks/RISKS.yaml).

## Сводка evidence

| ID                                                                                                   | Claim Summary                                                                                       | Confidence |
| ---------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ---------- |
| EV-refactor-backlog-governance-baseline-now-fails-only-on-scripts-inventory-drift                    | RF-01 is no longer a broad baseline task; the only red gate is scripts inventory drift.             | 0.98       |
| EV-refactor-backlog-registration-biblio-is-now-a-contained-provider-internal-seam                    | `registration_biblio.py` is now a contained internal seam with guardrails and direct tests.         | 0.90       |
| EV-refactor-backlog-pipeline-builder-and-composite-support-remain-the-main-open-composition-seams    | RF-04 should narrow to `pipeline_builder.py` and `composite_support_service_builders.py`.           | 0.92       |
| EV-refactor-backlog-domain-facade-policy-already-settles-runtime-port-placement-and-pipeline-context | Current code/policy already settle the old RF-06 dispute over `domain.ports` and `PipelineContext`. | 0.96       |
| EV-refactor-backlog-provider-registry-runtime-ownership-remains-a-deferred-watchpoint                | RF-07 is still best treated as deferred until a new natural runtime owner appears.                  | 0.95       |
| EV-refactor-backlog-active-implementation-work-now-concentrates-on-rf01-and-rf04                     | The active implementation queue now concentrates on RF-01 and RF-04.                                | 0.89       |

## Ключевые выводы

- The old “remaining tasks” list is stale relative to the current codebase.
- `RF-01` is now a one-gate cleanup task: refresh and validate the scripts inventory manifest.
- `RF-04` should be narrowed to the remaining composition assembly hubs, especially `pipeline_builder.py` and `composite_support_service_builders.py`.
- `RF-06` no longer reads as an implementation refactor. The current code and docs already make the project’s position explicit.
- `RF-07` is supported as a deferred/watchlist item, not as active implementation work.

## Обновлённые оставшиеся задачи

1. **RF-01 — Finish governance baseline**
   Scope now: `scripts inventory` only.
   Verify with:
   `./.venv/Scripts/python.exe -m scripts.engineering.repo check-inventory --check`

1. **RF-04 — Focused composition decomposition**
   Primary targets:

   - `src/bioetl/composition/factories/services/pipeline_builder.py`
   - `src/bioetl/composition/bootstrap/runtime/composite_support_service_builders.py`
     Secondary watchlist:
   - `src/bioetl/composition/providers/registration_biblio.py`

1. **RF-06 — Downgrade to docs/governance watchpoint**
   No active code migration recommended.
   Keep architecture narrative and guardrails aligned if future changes reopen the question.

1. **RF-07 — Keep deferred**
   Reopen only if a new runtime caller naturally owns explicit `ProviderRegistry` instance lifecycle.

## Отмеченные противоречия

- Historical planning treated `RF-06` and `RF-07` as active implementation work; current code/test/governance evidence no longer supports that framing.
- `registration_biblio.py` was previously grouped with open composition hotspots, but current evidence places it behind stronger confinement and direct unit coverage than the remaining open assembly hubs.

## Оставшиеся пробелы

- This calibration does not measure churn or defect density for the composition hotspots; it only recalibrates the backlog against the present code, tests, and guardrails.
- Inventory drift is confirmed, but this evidence set does not yet enumerate the exact manifest delta that must be updated.
