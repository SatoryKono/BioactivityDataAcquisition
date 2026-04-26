______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Layer Interaction — Hexagonal Runtime Topology

- Исходная диаграмма: `foundation/05-layers-interaction.mmd`

## Описание

Диаграмма Title: Layer Interaction — Hexagonal Runtime Topology показывает актуальную карту взаимодействия между слоями BioETL после выноса runtime assembly в `build_pipeline_runner`, стабилизации `GenericPipelineFactory` и перехода application/core на `PipelineRunner -> BatchExecutor -> BatchProcessingService`. Она представлена в формате `flowchart` и служит foundation-view для быстрой проверки layer ownership, DI seams и направления зависимостей между interfaces, composition, application, domain и infrastructure.

Ключевые узлы здесь: `PipelineRunnerService`, `build_pipeline_runner`, `PipelineRegistry`, `GenericPipelineFactory`, `StorageFactory`, `PipelineRunner`, `BasePipeline`, `BatchExecutor`, `BatchProcessingService`, `PipelineService`, composite runtime блок, а также domain port facade и infrastructure adapters. По этой схеме удобно валидировать, что composition собирает concrete collaborators, application работает через domain contracts, а infrastructure остаётся реализацией портов, а не прямой зависимостью application/core.

## Метаданные

- Тип: `flowchart`
- Уровень: `Component / Class`
- Дата метаданных: `2026-03-24`
