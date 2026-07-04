______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# BatchExecutor Internal Architecture

- Исходная диаграмма: `architecture/15-batch-executor-internals.mmd`

## Описание

Диаграмма BatchExecutor Internal Architecture показывает актуальный architecture-срез `BatchExecutor` после decomposition wave в `application/core`. Она использует нотацию flowchart и фиксирует не старый helper-bundle view, а текущий runtime path: `prepare_execution_context()` и `BatchExecutionContext`, `BatchExecutionRunService`, `BatchExecutionLifecycleService`, `BatchExtractionLoopService`, `PipelineProcessingPort`, `BatchStateCommitPort` и внутренний `BatchProcessingService` choreography. Это делает схему полезной для ревью изменений вокруг `batch_execution`, extraction loop, state commit и failure/finalization policy. Ключевые подграфы теперь: `BatchExecutor Shell`, `Run Orchestration`, `Processing And State Contracts`, `BatchProcessingService Internals`. По этим блокам удобно валидировать, что `BatchExecutor` больше работает как orchestration shell поверх injected contracts и grouped dependencies, а трансформация/запись/метрики/трейсинг остаются в downstream services. В метаданных зафиксирована текущая плотность (`@nodes=16`), что помогает контролировать читаемость и дальнейшую декомпозицию без потери архитектурного смысла.

## Метаданные

- Тип: `flowchart`
- Уровень: `Component / Service`
- Дата метаданных: `2026-03-24`
