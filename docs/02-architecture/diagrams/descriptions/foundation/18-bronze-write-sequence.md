______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Bronze Write Sequence (JSONL + zstd)

- Исходная диаграмма: `foundation/18-bronze-write-sequence.mmd`

## Описание

Диаграмма описывает текущий Bronze write path в BioETL: `BatchProcessingService` вызывает `BronzeWriter.write_bronze(...)`, после чего writer проходит через подготовку запроса, потоковую zstd-компрессию, atomic rename и post-write side effects. В отличие от старой версии, здесь больше нет искусственного шага с `PipelineExecutor` и отдельной lock-валидации внутри bronze writer: фактический контракт держится на `prepare_bronze_write(...)`, файловой атомарности и последующих metadata/audit действиях.

Схема полезна как опорная карта для обсуждения append-only поведения Bronze слоя, sidecar metadata и failure semantics. Ключевые участники: `BatchProcessingService`, `BronzeWriter`, `prepare_bronze_write()`, `zstd + atomic file write`, `Metadata/Audit side effects`, `Tracing + Metrics`.

## Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-03-24`
