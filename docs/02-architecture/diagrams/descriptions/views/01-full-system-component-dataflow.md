______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Full System Component Dataflow

- Исходная диаграмма: `views/01-full-system-component-dataflow.mermaid`

## Описание

Эта views-диаграмма Full System Component Dataflow представляет срез типа dataflow для родительской схемы `01-full-system-component-full.mermaid` и использует нотацию `flowchart`. Она показывает текущий верхнеуровневый execution path: `CLI -> build_pipeline_runner -> PipelineRunnerService -> PipelineRunner -> BatchExecutor -> BatchProcessingService -> BatchTransformer / BatchWriter -> Storage adapters -> Bronze / Silver / Gold`. Такой формат удобен для быстрой проверки того, как интерфейсный вход превращается в runtime orchestration и затем в medallion persistence.

Ключевые опорные узлы здесь: `CLI`, `build_pipeline_runner`, `PipelineRunnerService`, `PipelineRunner`, `BatchExecutor`, `BatchProcessingService`, `BatchTransformer / BatchWriter`, `Storage adapters`, `Bronze / Silver / Gold`. По этому срезу удобно валидировать, что high-level dataflow больше не описывается через старый `PipelineExecutor`, а строится вокруг актуальных runner и batch-processing seams.

## Метаданные

- Тип: `flowchart`
- View: `Data-Flow`
- Parent: `01-full-system-component-full.mermaid`
