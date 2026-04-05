______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-02'

______________________________________________________________________

# Title: Composite Pipeline Full Workflow — Seed to Gold (ADR-026)

- Исходная диаграмма: `foundation/29-composite-pipeline-workflow.mmd`

## Описание

Диаграмма показывает полный composite workflow от seed до Gold с актуальной resume-моделью. Runtime bootstrap здесь больше не описывается как legacy FSM adapter path: `bootstrap_composite_runner()` собирает runner factories, support services и control-plane dependencies для manifest/ledger. После этого execution сначала проходит через resume gate: checkpoint snapshot загружается, anchors валидируются, а затем поверх snapshot применяется suffix replay из run ledger по `last_event_id`. Только после этого composite run продолжает нужную фазу.

Важные точки схемы:

- seed, dependencies, enrichment и merge остаются основными execution phases;
- key extraction остаётся отдельной bridge-фазой между seed и fan-out enrichment;
- checkpointing больше не трактуется как hidden FSM internals: отдельно показаны `load`, `save` и control-plane `ledger`;
- Gold write теперь явно отмечен как version-aware contract/schema routing path, а не просто финальный write.

Эта диаграмма особенно полезна для ревью composite resume semantics, control-plane observability и phase-by-phase persistence contract.

## Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-04-02`
