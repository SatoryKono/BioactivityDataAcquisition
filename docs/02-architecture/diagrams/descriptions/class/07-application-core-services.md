# Class Diagram: 07 Application Core Services

- Исходная диаграмма: `class-diagrams/07-application-core-services.mmd`

## Описание
Диаграмма Application Core Services показывает архитектурную модель application-core orchestration и фиксирует контракты, роли и отношения между runner, batch-execution, lifecycle, preflight и postrun service families. Это representative view, а не полный перечень всех runtime helpers внутри `application/core`: схема выделяет основные execution seams вокруг `PipelineRunner`, `BatchExecutor`, `RecordProcessor`, `BatchWriter`, `CheckpointManagerService`, `BatchMemoryManagerService`, `BatchMetricsRecorderService`, `BatchTracingManagerService`, `PreflightService`, `PostrunService` и `CleanupService`. Диаграмму удобно использовать для оценки влияния изменений в runtime orchestration и для проверки, что новые decomposition waves не размывают границы между execution loop, lifecycle coordination и support services.

## Метаданные
- Тип: `classDiagram`
- Уровень: `Class / Interface`
- Дата метаданных: `2026-03-20`
