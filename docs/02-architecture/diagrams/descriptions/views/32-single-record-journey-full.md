______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Single Record Journey Full

- Исходная диаграмма: `views/32-single-record-journey-full.mermaid`

## Описание

Эта views-диаграмма Single Record Journey Full представляет полный onboarding-срез для одного record path и использует нотацию `flowchart`. Она показывает современную последовательность: provider response -> `DataSourcePort.fetch()` -> `BatchProcessingService.process_batch()` -> `write_bronze_layer()` -> `BatchTransformer.transform_batch()` -> normalization + metadata + `_content_hash` -> `TransformResult` -> route to clean/quarantine -> `write_silver_gold_concurrent()` -> Silver/Gold/Quarantine outputs.

Ключевые блоки здесь: `Source Record`, `Bronze Capture`, `Transform Record`, `DQ + Route`, `Persist Outputs`. Показательные узлы: `DataSourcePort.fetch()`, `BatchProcessingService.process_batch()`, `BatchWriter.write_bronze()`, `BatchTransformer.transform_batch()`, `TransformResult`, `flush_filtered_records() / flush_dq_records()`, `BatchWriter.write_silver()`, `BatchWriter.write_gold()`. По этой схеме удобно видеть, что single-record path уже не описывается старым `RecordProcessor`, а разложен на нынешние seams из `application/core`.

## Метаданные

- Тип: `unknown`
- View: `Full`
- Parent: `(root)`
