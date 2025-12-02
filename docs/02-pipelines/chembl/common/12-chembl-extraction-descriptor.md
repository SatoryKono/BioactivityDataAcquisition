# 12 ChEMBL Extraction Descriptor

## Описание

`ChemblExtractionDescriptor` — облегчённый описатель извлечения данных из ChEMBL, используемый в "dataclass"-стратегии. Хранит список идентификаторов *ids*, параметры пагинации, режим (`mode`, напр. "chembl" или "all") и план разбиения на батчи. Предназначен для конвейеров, использующих dataclass-дескрипторы (например, активности).

## Модуль

`src/bioetl/pipelines/chembl/common/descriptor.py`

## Наследование

Класс является dataclass и наследуется от `object`.

## Структура

Дескриптор содержит следующие поля:

- `ids: Sequence[str] | None` — список идентификаторов для извлечения (опционально)
- `filters: Mapping[str, object] | None` — параметры фильтрации (опционально)
- `pagination: PaginationParams | None` — настройки пагинации (limit/offset)
- `mode: str` — режим выгрузки (`"chembl"` или `"all"`)
- `batch_plan: BatchPlan | None` — план батчирования запросов

## Основные методы

### `__post_init__(self) -> None`

Пост-инициализация (dataclass), проверяет корректность поля `mode` (должно быть "chembl" или "all", иначе вызывает исключение).

**Процесс:**
1. Проверка значения поля `mode`
2. Выбрасывание `ConfigValidationError`, если значение недопустимо

## Использование

Дескриптор используется пайплайнами для:

- Разбиения работы на части (батчи)
- Логирования целей выгрузки
- Передачи параметров извлечения в экстракторы

## Related Components

- **DataclassExtractionStrategy**: стратегия извлечения через dataclass (см. `docs/02-pipelines/chembl/common/11-dataclass-extraction-strategy.md`)
- **BatchPlan**: план батчирования запросов
- **ChemblBasePipeline**: использует дескриптор для извлечения данных (см. `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md`)

