______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Pipeline Execution Sequence — Runner to Postrun

- Исходная диаграмма: `foundation/06-pipeline-execution.mmd`

## Описание

Диаграмма Title: Pipeline Execution Sequence — Runner to Postrun показывает актуальный execution path после выноса batch choreography в `BatchExecutor` и `BatchProcessingService`, а также после стабилизации `PostrunService` и `MedallionLifecycleService` как отдельных lifecycle collaborators. Она представлена в формате `sequenceDiagram` и используется как компактная foundation-view для ревью изменений вокруг `application/core/runner.py`, `application/core/batch_executor.py`, `application/core/batch_processing_service.py`, `application/core/preflight/service.py` и `application/core/postrun/service.py`. Уровень детализации обозначен как `Component / Class`, поэтому схема концентрируется на наблюдаемом runtime порядке вызовов: создание `PipelineRunner`, вход в managed contexts, preflight, подготовка medallion layers, batch execution, checkpoint persistence и postrun finalization.

Значимые участники последовательности: `build_pipeline_runner`, `PipelineRunner`, `PipelineService`, `LockCoordinator`, `PreflightService`, `MedallionLifecycleService`, `CheckpointRuntimeService`, `BatchExecutor`, `BatchProcessingService`, `BaseTransformer`, `StoragePort`, `PostrunService`. По этой схеме удобно валидировать, что runtime flow больше не идёт через устаревший `PipelineExecutor`, а строится вокруг `PipelineRunner -> BatchExecutor -> BatchProcessingService` с отдельной postrun/lifecycle фазой.

## Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Component / Class`
- Дата метаданных: `2026-03-24`
