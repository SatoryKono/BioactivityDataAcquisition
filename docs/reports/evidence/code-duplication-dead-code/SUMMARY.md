# Сводка evidence по дублированию кода и мёртвому коду

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

Дата: 2026-03-21

## Интерпретация верхнего уровня

- Формальная cross-shard интерпретация теперь находится в [03-synthesis/CROSS-SYNTHESIS.md](./03-synthesis/CROSS-SYNTHESIS.md).
- Принятая позиция теперь находится в [04-decisions/DECISIONS.yaml](./04-decisions/DECISIONS.yaml).
- Активные риски теперь находятся в [05-risks/RISKS.yaml](./05-risks/RISKS.yaml).

## Общий результат

- Режим сбора evidence: hierarchical
- Завершённые pillars: `duplication`, `dead-code`
- Всего семантических объектов evidence: `11`
- Итоговый результат gate: `PASS`

## Выходы shard-ов

- Duplication shard: [duplication/SUMMARY.md](./duplication/SUMMARY.md)
- Dead-code shard: [dead-code/SUMMARY.md](./dead-code/SUMMARY.md)
- Orchestration log: [ORCHESTRATION.md](./ORCHESTRATION.md)

## Что подтверждает текущее evidence

- The strongest duplication pressure is not broad project-wide copy/paste, but a small number of repeated composition and registry seams.
- The clearest reducible duplication cluster is shared provider-registry resolution and closely related provider-config assembly scaffolding.
- A large part of the apparent duplication is intentional compatibility duplication that preserves class-level and bootstrap-oriented registry behavior.
- The dead-code pass is conservative: most suspicious files in this slice are retained compatibility wrappers or sanctioned aggregate seams, not deletion candidates.
- The only moderate deletion-review candidate surfaced by this run is `src/bioetl/application/core/batch_transformer_orchestration.py`.

## Интерпретация

- This evidence package does not support a broad rename-or-delete campaign.
- It does support targeted follow-up review in a few narrow areas:
  - provider-registry and factory resolution seams where duplication appears structurally real
  - provider registration families where helper consolidation is partial but not complete
  - `batch_transformer_orchestration.py` as a deletion-or-repurpose review candidate
- Compatibility wrappers and sanctioned aggregate seams should stay out of generic dead-code cleanup queues unless a separate migration plan removes their public obligations.

## Уровень уверенности

- Higher confidence on duplication findings around registry and registration seams because they are corroborated by code structure and existing compatibility/test surfaces.
- Higher confidence on the retained-wrapper classification in the dead-code shard.
- Moderate confidence only on the dormant-code finding for `batch_transformer_orchestration.py`; this one should move to a targeted review queue rather than straight deletion.
