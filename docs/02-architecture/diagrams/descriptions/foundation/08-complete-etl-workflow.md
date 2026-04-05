______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Complete ETL Workflow (6 Phases)

- Исходная диаграмма: `foundation/08-complete-etl-workflow.mmd`

## Описание

Диаграмма Title: Complete ETL Workflow (6 Phases) показывает актуальный end-to-end runtime flow пайплайна после стабилизации `PipelineRunner`, `BatchExecutor`, `BatchProcessingService` и `PostrunService` как отдельных orchestration seams. Она представлена в формате `flowchart` и используется как foundation-view для просмотра полного пути выполнения: managed startup, extraction loop, Bronze/transform choreography, concurrent Silver/Gold writes, postrun finalization и cleanup.

Ключевые узлы здесь: `validate_infrastructure`, `prepare_for_run`, `BatchExecutor.execute`, `extract_records via DataSourcePort.fetch`, `write_bronze_layer`, `transform_batch`, `write_silver_gold_concurrent`, `PostrunService.run`, `finalize_run vacuum`, `PipelineService.aclose`. По этой схеме удобно валидировать, что execution path больше не завязан на старый `PipelineExecutor`, а строится вокруг текущих runtime collaborators и явных postrun/cleanup phases.

## Метаданные

- Тип: `flowchart`
- Уровень: `Component / Class`
- Дата метаданных: `2026-03-24`
