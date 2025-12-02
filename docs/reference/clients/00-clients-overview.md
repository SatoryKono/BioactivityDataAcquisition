# 00 Clients Overview

## Паттерн
Клиенты строятся по схеме: RequestBuilder + HttpBackend + Parser + Paginator, объединённые в доменный сервис извлечения.

## Компоненты Chembl
- **ChemblClient** — реализует BaseClient для ChEMBL, использует UnifiedAPIClient.
- **ChemblRequestBuilder** — формирует запросы к ChEMBL API с учётом фильтров и релиза.
- **ChemblResponseParser** — переводит ответы API в структурированные записи.
- **ChemblPaginator** — управляет постраничной навигацией и лимитами.
- **RequestsBackend** — HTTP-бэкенд на основе requests или аналога.
- **ChemblExtractionService** — оборачивает клиента и дескрипторы для пайплайнов.

## Связь с UnifiedAPIClient
UnifiedAPIClient конфигурирует ретраи, лимиты и кэш и делегирует доменные детали ChemblClient. Такой паттерн применяется и к другим источникам (Semantic Scholar, PubMed и др.).
