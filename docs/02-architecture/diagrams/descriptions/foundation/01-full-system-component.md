______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Full System Component Diagram

- Исходная диаграмма: `foundation/01-full-system-component.mmd`

## Описание

Диаграмма Title: Full System Component Diagram теперь показывает актуальную top-level карту BioETL после перехода runtime assembly на `build_pipeline_runner`, стабилизации `PipelineRunnerService`, `GenericPipelineFactory`, `StorageFactory` и современного application/core path через `PipelineRunner -> BatchExecutor -> BatchProcessingService`. Она представлена в формате `flowchart` и используется как самый широкий foundation-view для навигации по слоям, runtime ownership и направлению зависимостей между interfaces, composition, application, domain, infrastructure и data lake/state.

Ключевые узлы здесь: `build_pipeline_runner`, `PipelineRegistry`, `GenericPipelineFactory`, `StorageFactory`, `PipelineRunnerService`, `PipelineRunner`, `PipelineRunnerDependencies`, `BatchExecutor`, `BatchProcessingService`, `PipelineService`, `Composite runtime`, domain port facade, provider/storage/state/observability adapters и medallion stores. По этой схеме удобно быстро проверять, где заканчивается composition wiring, где начинается application orchestration, и как infrastructure adapters соотносятся с domain contracts и медальонными слоями.

## Метаданные

- Тип: `flowchart`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-03-24`
