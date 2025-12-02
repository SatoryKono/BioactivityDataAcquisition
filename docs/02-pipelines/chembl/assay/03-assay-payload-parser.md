# 03 Assay Payload Parser

## Описание

`AssayPayloadParser` — парсер payload'ов ассая. Должен разбирать сырой JSON-ответ ChEMBL (например, поле `assay_parameters` и связанные сущности) в структурированный вид (DataFrame или dict).

## Модуль

`src/bioetl/pipelines/chembl/assay/parsers.py`

## Основной метод

### `parse(self, payload: Any) -> Any`

Разбирает сырой JSON-ответ ChEMBL для assay в структурированный вид.

**Параметры:**
- `payload` — сырой JSON-ответ от ChEMBL API

**Процесс:**
1. Извлечение поля `assay_parameters` и связанных сущностей
2. Развёртывание вложенных структур
3. Преобразование в структурированный формат (DataFrame или dict)

**Возвращает:** структурированные данные (DataFrame или dict).

## Использование

Парсер используется для обработки ответов от ChEMBL API:

```python
from bioetl.pipelines.chembl.assay.parsers import AssayPayloadParser

parser = AssayPayloadParser()
structured_data = parser.parse(json_payload)
```

## Related Components

- **ChemblAssayPipeline**: использует парсер для обработки ответов API (см. `docs/02-pipelines/chembl/assay/00-assay-chembl-overview.md`)
- **ChemblClient**: клиент ChEMBL API (см. `docs/02-pipelines/chembl/common/01-chembl-client.md`)

