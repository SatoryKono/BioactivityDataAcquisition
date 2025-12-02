# 25 Dataclass Extraction Strategy

## Описание

`DataclassExtractionStrategy` — стратегия выполнения *extract* через *dataclass*-дескриптор. Поддерживает тип `"dataclass"` и запускает кастомную логику извлечения, определённую в пайплайне для dataclass-дескриптора (например, для ActivityPipeline).

## Модуль

`src/bioetl/pipelines/chembl/common/strategies.py`

## Основные методы

### `supports(self, descriptor_type: str) -> bool`

Возвращает `True` для типа дескриптора `"dataclass"`.

**Параметры:**
- `descriptor_type` — тип дескриптора

**Возвращает:** `True` если стратегия поддерживает тип, иначе `False`.

### `run(self, pipeline: ChemblCommonPipeline, descriptor: ChemblExtractionServiceDescriptor | ChemblExtractionDescriptor | None, options: StageExecutionOptions) -> pd.DataFrame`

Выполняет извлечение: если дескриптор не задан – строит через `pipeline.build_descriptor()`, затем вызывает `_extract_with_dataclass_descriptor` у пайплайна (если дескриптор типа ChemblExtractionDescriptor); при отсутствии дескриптора или в dry-run возвращает пустой DataFrame.

**Параметры:**
- `pipeline` — пайплайн ChEMBL
- `descriptor` — дескриптор извлечения (опционально)
- `options` — опции выполнения стадии

**Процесс:**
1. Проверка режима dry-run (возврат пустого DataFrame)
2. Построение дескриптора (если не передан) через `pipeline.build_descriptor()`
3. Проверка типа дескриптора (должен быть `ChemblExtractionDescriptor`)
4. Вызов `pipeline._extract_with_dataclass_descriptor(...)` для выполнения извлечения

**Возвращает:** DataFrame с извлечёнными данными или пустой DataFrame.

## Использование

Стратегия используется для пайплайнов, работающих с dataclass-дескрипторами (например, ActivityPipeline):

```python
factory = ExtractionStrategyFactory()
strategy = factory.get("dataclass")
df = strategy.run(pipeline, descriptor, options)
```

## Related Components

- **ExtractionStrategyFactory**: фабрика стратегий (см. `docs/02-pipelines/chembl/common/23-extraction-strategy-factory.md`)
- **ChemblExtractionDescriptor**: dataclass-дескриптор извлечения (см. `docs/02-pipelines/chembl/common/26-chembl-extraction-descriptor.md`)
- **ChemblCommonPipeline**: использует стратегию для извлечения данных (см. `docs/02-pipelines/chembl/common/18-chembl-common-pipeline.md`)

