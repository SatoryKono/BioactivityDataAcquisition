# 23 Extraction Strategy Factory

## Описание

`ExtractionStrategyFactory` — фабрика стратегий извлечения данных. Инкапсулирует две реализации стратегии – через dataclass-дескриптор и service-дескриптор – и по запросу возвращает подходящую стратегию в зависимости от типа дескриптора, указанного в конфигурации пайплайна.

## Модуль

`src/bioetl/pipelines/chembl/common/strategies.py`

## Основные методы

### `__init__(self, strategies: Iterable[ExtractionStrategy] | None = None)`

При создании фабрики инициализирует список стратегий; если не задано, регистрирует стратегии по умолчанию (dataclass, service).

**Параметры:**
- `strategies` — список стратегий извлечения (опционально, по умолчанию регистрируются обе стратегии)

### `get(self, descriptor_type: str) -> ExtractionStrategy`

Возвращает первую подходящую стратегию для данного типа дескриптора или выбрасывает `ValueError`, если тип не поддерживается.

**Параметры:**
- `descriptor_type` — тип дескриптора ("dataclass" или "service")

**Процесс:**
1. Поиск стратегии, поддерживающей указанный тип (через `strategy.supports(descriptor_type)`)
2. Возврат первой найденной стратегии
3. Выбрасывание `ValueError`, если тип не поддерживается

**Возвращает:** стратегию извлечения для указанного типа дескриптора.

## Поддерживаемые типы

Фабрика поддерживает два типа дескрипторов:

- `"dataclass"` — дескриптор на основе dataclass
- `"service"` — дескриптор на основе сервиса

## Использование

Фабрика используется в `ChemblCommonPipeline` для выбора стратегии извлечения:

```python
factory = ExtractionStrategyFactory()
strategy = factory.get("service")
df = strategy.run(pipeline, descriptor, options)
```

## Related Components

- **ServiceExtractionStrategy**: стратегия извлечения через сервис (см. `docs/02-pipelines/chembl/common/24-service-extraction-strategy.md`)
- **ChemblCommonPipeline**: использует фабрику для выбора стратегии (см. `docs/02-pipelines/chembl/common/18-chembl-common-pipeline.md`)

