______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Batch Processing Flow — BatchProcessingService choreography

- Исходная диаграмма: `foundation/34-batch-processing-flow.mmd`

## Описание

Диаграмма Title: Batch Processing Flow — BatchProcessingService choreography фиксирует актуальный batch-processing path после выноса processing choreography из `BatchExecutor` в `BatchProcessingService` и `BatchProcessingSupportService`. Она представлена в формате sequenceDiagram и используется как опорная foundation-view для ревью изменений в extract/transform/write flow. Уровень детализации обозначен как Component / Class, поэтому схема концентрируется на актуальной последовательности вызовов между `BatchExecutor`, `BatchProcessingService`, `BatchTracingManagerService`, `BatchProcessingSupportService`, `BatchTransformer`, `BatchWriter` и `BatchExecutionStateService`, а не на старом монолитном executor flow. В комментариях исходника зафиксирован фокус диаграммы: Covers: RULES.md §2.1 (Data Flow), application/core/{batch_executor,batch_processing_service,batch_processing_support}.py. По этой схеме удобно валидировать extract phase, source metadata enrichment, Bronze write, transform metrics, concurrent Silver/Gold writes и state commit после успешного batch outcome.

## Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Component / Class`
- Дата метаданных: `2026-03-24`
