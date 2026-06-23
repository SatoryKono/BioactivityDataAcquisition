______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Application Layer Class Diagram Dataflow

- Исходная диаграмма: `views/06-application-layer-class-diagram-dataflow.mermaid`

## Описание

Эта views-диаграмма Application Layer Class Diagram Dataflow представляет срез типа dataflow для родительской схемы `06-application-layer-class-diagram-full.mermaid` и использует нотацию `flowchart`. Она фиксирует современный execution spine application-слоя: `PipelineRunner -> BatchExecutor -> BatchProcessingService -> BatchTransformer / BatchWriter`, а рядом показывает injected context через `BasePipeline`, `PipelineService`, `BaseTransformer` и `QuarantineRuntimeService`.

Ключевые узлы здесь: `PipelineRunner`, `BatchExecutor`, `BatchProcessingService`, `BatchTransformer`, `BatchWriter`, `BasePipeline`, `PipelineService`, `BaseTransformer`, `QuarantineRuntimeService`. Этот view полезен для проверки того, что runtime flow больше не завязан на старые `RecordProcessor` / `PipelineExecutor`, а разложен на явные orchestration и processing seams.

## Метаданные

- Тип: `flowchart`
- View: `Data-Flow`
- Parent: `06-application-layer-class-diagram-full.mermaid`
