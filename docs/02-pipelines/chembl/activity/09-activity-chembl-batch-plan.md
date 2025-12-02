# 09 Activity ChEMBL Batch Plan

## Описание

`BatchPlan` — простая структура для параметров пакетирования запросов. Содержит размер батча (`batch_size`) – число идентификаторов в одном запросе к API – и размер чанка (`chunk_size`) – количество батчей, объединяемых в одну запись результатов. Эти параметры влияют на стратегию извлечения данных из API (ограничение в 25 ID на запрос у ChEMBL).

## Модуль

`bioetl/clients/chembl/descriptor_factory.py`

## Структура

BatchPlan является dataclass и содержит следующие поля:

- `batch_size: int` — размер батча (количество ID в одном запросе к API)
- `chunk_size: int` — размер чанка (количество батчей, объединяемых в одну запись)

## Использование

План батчирования используется для:

- Оптимизации запросов к ChEMBL API (ограничение в 25 ID на запрос)
- Управления размером обрабатываемых данных
- Контроля использования памяти при извлечении больших объёмов данных

## Пример

```python
batch_plan = BatchPlan(
    batch_size=25,  # 25 ID на запрос (ограничение ChEMBL)
    chunk_size=10   # 10 батчей в одном чанке
)
```

## Related Components

- **ChemblExtractionDescriptor**: содержит BatchPlan для управления извлечением (см. `docs/02-pipelines/chembl/activity/07-activity-chembl-descriptor.md`)
- **ActivityExtractor**: использует BatchPlan для разбиения запросов на батчи (см. `docs/02-pipelines/chembl/activity/01-activity-chembl-extraction.md`)

