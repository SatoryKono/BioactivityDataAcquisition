# 08 ChEMBL Extraction Service Descriptor

## Описание

`ChemblExtractionServiceDescriptor` — описание параметров извлечения сущности ChEMBL (service-дескриптор). Содержит функции для построения контекста (`build_context`), фабрики выборки (`fetcher_factory`) и финализатора (`finalizer_factory`), используемые `ChemblExtractionService` для получения и обработки данных.

## Модуль

`src/bioetl/core/pipeline/unified.py`

## Структура

Дескриптор содержит следующие компоненты:

- `build_context` — функция для построения контекста выполнения (`Callable[[ChemblPipelineT], Mapping[str, Any]]`)
- `fetcher_factory` — фабрика функций выборки данных (`Callable[[Mapping[str, Any]], Callable[[Sequence[str] | None], Any]]`)
- `finalizer_factory` — фабрика функций финализации результатов (`Callable[[Mapping[str, Any]], Callable[[pd.DataFrame], pd.DataFrame]]`)

## Основные методы

### `__init__(self, *, build_context: Callable[[ChemblPipelineT], Mapping[str, Any]], fetcher_factory: Callable[[Mapping[str, Any]], Callable[[Sequence[str] | None], Any]], finalizer_factory: Callable[[Mapping[str, Any]], Callable[[pd.DataFrame], pd.DataFrame]])`

Конструктор, сохраняет переданные фабричные функции (контекста, выборки, финализации).

**Параметры:**
- `build_context` — функция для построения контекста выполнения
- `fetcher_factory` — фабрика функций выборки данных
- `finalizer_factory` — фабрика функций финализации результатов

## Использование

Дескриптор используется `ChemblExtractionService` для:

- Формирования контекста выполнения выборки
- Создания функции выборки данных из ChEMBL API
- Финализации объединённого DataFrame результатов

## Related Components

- **ChemblExtractionService**: использует дескриптор для извлечения данных (см. `docs/02-pipelines/chembl/common/06-chembl-extraction-service.md`)
- **ChemblDescriptorFactory**: создаёт дескрипторы (см. `docs/02-pipelines/chembl/common/07-chembl-descriptor-factory.md`)

