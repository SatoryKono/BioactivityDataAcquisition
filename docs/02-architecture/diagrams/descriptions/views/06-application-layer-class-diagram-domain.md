______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Application Layer Class Diagram Domain

- Исходная диаграмма: `views/06-application-layer-class-diagram-domain.mermaid`

## Описание

Эта views-диаграмма Application Layer Class Diagram Domain представляет срез типа domain для родительской схемы `06-application-layer-class-diagram-full.mermaid` и использует нотацию `flowchart`. Она концентрируется на том, как pipeline-definition и transform-oriented классы стыкуются с runtime data: `BasePipeline`, `PipelineService`, `BaseTransformer`, `BatchTransformer`, `BatchProcessingService`, `BatchWriter`, `QuarantineManagerService`, `PipelineContext`, `BatchProcessingOutcome`.

Этот view нужен не для полного каталога классов, а для проверки domain-facing seams внутри application-слоя: где pipeline определяет transform contract, как batch-processing связывает transform и write path, и где появляются runtime результаты. Он подчёркивает, что текущая модель больше не описывается старым `RecordProcessor`, а держится на `BatchProcessingService` и связанных explicit collaborators.

## Метаданные

- Тип: `flowchart`
- View: `Domain-Focus`
- Parent: `06-application-layer-class-diagram-full.mermaid`
