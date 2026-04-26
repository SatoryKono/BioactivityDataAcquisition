______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Class Diagram: 12 Composite Pipeline

- Исходная диаграмма: `class-diagrams/12-composite-pipeline.mmd`

## Описание

Диаграмма Composite Pipeline Components показывает архитектурную модель модуля `12-composite-pipeline` и фиксирует контракты, роли и отношения между сущностями слоя `Class / Interface`. Основной фокус: Runner, coordinators, merge service, and FSM. На схеме отражено примерно 14 классов и 13 связей, поэтому её удобно использовать для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга. Ключевые элементы для быстрого чтения: CompositePipelineRunner, CompositeRuntimeConfig, EnrichmentCoordinator, DependencyCoordinator, MergeService, EnricherAggregator.

## Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата метаданных: `2026-03-01`
