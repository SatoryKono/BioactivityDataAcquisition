______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Class Diagram: 07 Application Core Services

- Исходная диаграмма: `class-diagrams/07-application-core-services.mmd`

## Описание

Диаграмма Application Core Services показывает актуальную архитектурную модель `application/core` после decomposition waves в runtime/lifecycle/postrun. Это representative view, а не полный перечень всех helper-модулей: схема специально удерживает основной execution surface вокруг `PipelineRunner`, `PipelineService`, `BatchExecutor`, `BatchTransformer`, `BatchWriter`, `CheckpointManagerService`, `LockCoordinator`, `PreflightService`, `PostrunService`, `MedallionLifecycleService`, `PipelineObserver`, `QuarantineManagerService`, `BatchMetricsRecorderService` и `BatchTracingManagerService`. Диаграмму удобно использовать для оценки влияния изменений в orchestration seams и для проверки, что cleanup/refactor waves по-прежнему сохраняют границы между batch processing, lifecycle coordination, observability и support services.

## Метаданные

- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата метаданных: `2026-03-24`
