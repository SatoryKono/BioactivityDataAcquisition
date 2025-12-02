# 07 Activity ChEMBL Descriptor

## Описание

`ChemblExtractionDescriptor` — описание задачи извлечения данных из ChEMBL. Хранит параметры, определяющие, *что* извлекать: список идентификаторов `ids` (ChEMBL IDs интересующих объектов) либо параметры фильтрации, настройки пагинации (`limit/offset`), режим выгрузки и т.д. Кроме того, содержит вложенный `BatchPlan` для управления размером батча и числом чанков при извлечении.

## Модуль

`bioetl/pipelines/chembl/common/descriptor.py`

## Структура

Дескриптор является dataclass и содержит следующие поля:

- `ids: Sequence[str] | None` — список ChEMBL IDs для извлечения (опционально)
- `filters: Mapping[str, object] | None` — параметры фильтрации (опционально)
- `pagination: PaginationParams | None` — настройки пагинации (limit/offset)
- `mode: str` — режим выгрузки (`"chembl"` или `"all"`)
- `batch_plan: BatchPlan | None` — план батчирования запросов

## Валидация

### `__post_init__(self) -> None`

Проверяет корректность поля `mode` при инициализации. Разрешены только значения `"chembl"` или `"all"`, иначе выбрасывается `ConfigValidationError`.

## Использование

Дескриптор используется пайплайном для:

- Разбиения работы на части (батчи)
- Логирования целей выгрузки
- Передачи параметров извлечения в `ActivityExtractor`

## Related Components

- **BatchPlan**: план батчирования запросов (см. `docs/02-pipelines/chembl/activity/09-activity-chembl-batch-plan.md`)
- **ActivityExtractor**: использует дескриптор для извлечения данных (см. `docs/02-pipelines/chembl/activity/01-activity-chembl-extraction.md`)
- **ChemblActivityPipeline**: создаёт дескриптор через `build_descriptor()` (см. `docs/02-pipelines/chembl/activity/00-activity-chembl-overview.md`)

