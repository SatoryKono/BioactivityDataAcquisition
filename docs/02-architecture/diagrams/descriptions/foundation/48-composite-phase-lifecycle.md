______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-02'

______________________________________________________________________

# Title: Composite Pipeline Phase Lifecycle and Resume Semantics

- Исходная диаграмма: `foundation/48-composite-phase-lifecycle.mmd`

## Описание

Диаграмма фиксирует composite FSM уже в актуальной operational интерпретации: state machine управляет фазами seed/dependencies/enrichment/merge, а resume semantics строятся поверх checkpoint snapshot и suffix replay из run ledger. Это важное отличие от старых описаний, где checkpoint трактовался почти как единственный источник resume state.

Что важно в текущей версии:

- checkpoint snapshot хранит anchors, phase results и `last_event_id`;
- `CompositeCheckpointLoadService` сначала валидирует совместимость anchors, затем применяет ledger replay suffix;
- entering phases публикует `stage_started`, а успешное завершение — `stage_completed`;
- published baseline intentionally не использует отдельный `stage_failed`: failure документируется через `run_failed` и terminal checkpoint state.

Диаграмма нужна для ревью resumability, stage semantics и coarse-grained replay contract.

## Метаданные

- Тип: `stateDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-04-02`
