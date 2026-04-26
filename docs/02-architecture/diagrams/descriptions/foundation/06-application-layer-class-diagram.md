______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Application Layer Class Diagram

- Исходная диаграмма: `foundation/06-application-layer-class-diagram.mmd`

## Описание

Диаграмма Title: Application Layer Class Diagram показывает актуальную верхнеуровневую topology слоя `application` после decomposition waves в `core`, `services` и `observability`. Она представлена в формате classDiagram и используется как foundation-map для навигации между `BasePipeline`, `PipelineRunner`, `BatchExecutor`, `BatchProcessingService`, `PipelineService`, lifecycle/postrun collaborators и transformer-facing contracts. Уровень детализации обозначен как Component / Class, поэтому схема не пытается перечислить все provider-specific transformers или все leaf helpers, а фиксирует канонические application seams и их связи. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §1.1 (Application Layer), application/core/, application/services/, application/observability/. По этой схеме удобно проверять, что orchestration, processing, lifecycle и observability остаются разделёнными и собираются вокруг DI-bound contracts, а не вокруг старых монолитных executor/service bundles.

## Метаданные

- Тип: `classDiagram`
- Уровень: `Component / Class`
- Дата метаданных: `2026-03-24`
