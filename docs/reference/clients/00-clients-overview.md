# Clients Overview

Этот раздел описывает реализацию клиентов для доступа к ChEMBL API.

## Архитектура

```text
┌─────────────────────────────────────────┐
│          ChemblClient (High-Level)      │
│   (request_activity, request_assay)     │
├─────────────────────────────────────────┤
│       ConfiguredHttpClient (Mid-Level)  │
│   (UnifiedAPIClient logic: retry, rate) │
├─────────────────────────────────────────┤
│        RequestsBackend (Low-Level)      │
│   (requests.Session, raw HTTP)          │
└─────────────────────────────────────────┘
```

## Компоненты

### ChemblClient
**Модуль:** `src/bioetl/clients/chembl/client.py`

Высокоуровневый фасад. Предоставляет семантические методы для запроса данных:
- `request_activity(**filters)`
- `request_assay(**filters)`
- `request_target(**filters)`

### ChemblRequestBuilder
**Модуль:** `src/bioetl/clients/chembl/request_builder.py`

Отвечает за формирование корректных URL и параметров запроса для различных эндпоинтов ChEMBL. Знает о специфике фильтрации (например, `__in`, `__gte`).

### ChemblResponseParser
**Модуль:** `src/bioetl/clients/chembl/response_parser.py`

Парсит JSON-ответы ChEMBL, извлекает список записей и метаданные пагинации (`page_meta`).

### ChemblExtractionService
**Модуль:** `src/bioetl/services/chembl_extraction_service.py`

Оркестратор процесса извлечения.
- Определяет версию API (`chembl_release`).
- Управляет итерацией по страницам через `ChemblPaginator`.
- Собирает результаты в единый DataFrame.

