______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Record Processing Pipeline — Single Record Journey

- Исходная диаграмма: `foundation/32-single-record-journey.mmd`

## Описание

Диаграмма Title: Record Processing Pipeline — Single Record Journey показывает актуальный путь одной записи через современный batch-processing stack BioETL. Она представлена в формате `flowchart` и используется как onboarding-friendly foundation-view для понимания того, как `BronzeRecord` проходит через `BatchProcessingService`, Bronze capture, `BatchTransformer`, DQ/quarantine routing и concurrent Silver/Gold persistence.

Ключевые узлы здесь: `DataSourcePort.fetch()`, `BatchProcessingService.process_batch()`, `write_bronze_layer()`, `BatchTransformer.transform_batch()`, `BaseTransformer._transform_impl()`, нормализация, run metadata, `_content_hash`, `TransformResult`, `flush_filtered_records() / flush_dq_records()`, `write_silver_gold_concurrent()`, `BatchWriter.write_silver()`, `BatchWriter.write_gold()`. По этой схеме удобно видеть, что single-record path больше не описывается старым `RecordProcessor`, а раскладывается на явные modern seams в application/core.

## Метаданные

- Тип: `flowchart`
- Уровень: `Component / Class`
- Дата метаданных: `2026-03-24`
