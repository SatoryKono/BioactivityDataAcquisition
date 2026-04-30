______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Pipeline Execution — Happy Path

- Исходная диаграмма: `foundation/03-pipeline-execution-happy-path.mmd`

## Описание

Диаграмма Title: Pipeline Execution — Happy Path показывает сокращённый, но уже актуальный execution path для обычного успешного запуска пайплайна. Она представлена в формате `sequenceDiagram` и используется как foundation-view для быстрого чтения жизненного цикла без детализации по Bronze/Silver/Gold writer internals. Уровень детализации обозначен как `Component / Class`, поэтому схема акцентирует только основные фазы: создание `PipelineRunner`, managed startup с lock/preflight/medallion prepare, batch execution через `BatchExecutor` и `BatchProcessingService`, postrun finalization и cleanup.

Значимые участники последовательности: `build_pipeline_runner`, `PipelineRunner`, `LockCoordinator`, `PreflightService`, `MedallionLifecycleService`, `CheckpointRuntimeService`, `BatchExecutor`, `BatchProcessingService`, `PostrunService`. По этой схеме удобно быстро проверять happy-path порядок вызовов после удаления старого `PipelineExecutor` choreography из application/core.

## Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Component / Class`
- Дата метаданных: `2026-03-24`
