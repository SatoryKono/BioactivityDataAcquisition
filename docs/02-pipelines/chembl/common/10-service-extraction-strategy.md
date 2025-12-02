# 10 Service Extraction Strategy

## Описание

`ServiceExtractionStrategy` — стратегия извлечения через сервис-дескрипторы. Реализует логику выборки данных для дескриптора типа `"service"`: вызывает у пайплайна построение дескриптора (если не передан) и метод `run_descriptor_extraction` для получения данных из ChEMBL API; возвращает объединённый DataFrame результатов или пустой DataFrame, если выборка не вернула данных.

## Модуль

`src/bioetl/pipelines/chembl/common/strategies.py`

## Основные методы

### `supports(self, descriptor_type: str) -> bool`

Возвращает `True`, если тип дескриптора равен `"service"`.

**Параметры:**
- `descriptor_type` — тип дескриптора

**Возвращает:** `True` если стратегия поддерживает тип, иначе `False`.

### `run(self, pipeline: ChemblBasePipeline, descriptor: ChemblExtractionServiceDescriptor | ChemblExtractionDescriptor | None, options: StageExecutionOptions) -> pd.DataFrame`

Выполняет извлечение: строит дескриптор (если не задан) и вызывает у пайплайна `run_descriptor_extraction` с необходимыми параметрами (IDs, batch_size и пр.).

**Параметры:**
- `pipeline` — пайплайн ChEMBL
- `descriptor` — дескриптор извлечения (опционально)
- `options` — опции выполнения стадии

**Процесс:**
1. Определение идентификаторов из конфигурации
2. Построение дескриптора (если не передан) через `pipeline.build_descriptor()`
3. Вызов `pipeline.run_descriptor_extraction(...)` для получения данных с параметрами (IDs, batch_size и пр.)
4. Обработка пустого результата (возврат пустого DataFrame или пустой рамки от ValidationService)

**Возвращает:** DataFrame с извлечёнными данными или пустой DataFrame.

## Related Components

- **ExtractionStrategyFactory**: фабрика стратегий (см. `docs/02-pipelines/chembl/common/09-extraction-strategy-factory.md`)
- **ChemblBasePipeline**: использует стратегию для извлечения данных (см. `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md`)

