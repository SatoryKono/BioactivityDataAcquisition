______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Title: Delta Lake Write Sequence (Silver Layer)

- Исходная диаграмма: `foundation/19-delta-lake-write-sequence.mmd`

## Описание

Диаграмма фиксирует актуальный silver write choreography: `BatchProcessingService` передаёт нормализованные записи в `SilverWriter`, тот подготавливает payload через validation/Arrow seam, затем dispatch-политика выбирает merge или plain Delta write path, а финализация отдельно собирает metadata и `SilverWriteResult`. Старый `RecordProcessor` и lock-check этап удалены, потому что они больше не отражают реальную структуру silver writer.

Схема помогает быстро проверить текущую ответственность слоёв: где заканчивается application-orchestration, где начинается `SilverWriter`, как выглядит mode-based dispatch и где возникает Delta/metadata side effect. Ключевые участники: `BatchProcessingService`, `SilverWriter`, `Validation + Arrow prep`, `Delta dispatch policy`, `DeltaTable / write_deltalake`, `Delta log + parquet files`, `Silver metadata finalization`.

## Метаданные

- Тип: `sequenceDiagram`
- Уровень: `Mixed (System / Component / Class)`
- Дата метаданных: `2026-03-24`
