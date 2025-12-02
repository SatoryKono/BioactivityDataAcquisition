# 00 Target ChEMBL Overview

## Описание

`ChemblTargetPipeline` — основной класс пайплайна для сущности *target* из ChEMBL (включая обогащение данными UniProt/IUPHAR). Наследует общий Chembl-пайплайн и определяет специфичные шаги для *target*.

## Модуль

`src/bioetl/pipelines/chembl/target/run.py`

## Наследование

Пайплайн наследуется от `ChemblCommonPipeline` и использует общую инфраструктуру ChEMBL-пайплайнов. При инициализации устанавливает схему валидации *TargetSchema* и сервис валидации.

## Основные методы

### `__init__(self, config: Mapping[str, Any], *, run_id: str | None = None)`

Конструктор, инициализирует родительский класс с типом дескриптора *service*, устанавливает схему валидации *TargetSchema* и сервис валидации.

**Параметры:**
- `config` — конфигурация пайплайна
- `run_id` — идентификатор запуска (опционально)

### `build_descriptor(self) -> Any`

Строит дескриптор вызовом реализации из базового класса.

**Возвращает:** дескриптор извлечения данных для target.

### `validate(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Выполняет валидацию через базовый метод и дополнительно проверяет наличие `target_chembl_id` (обязательное поле).

**Параметры:**
- `df` — DataFrame для валидации
- `options` — опции выполнения стадии

**Процесс:**
1. Вызов базовой валидации через родительский класс
2. Проверка наличия обязательного поля `target_chembl_id`
3. Возврат валидированного DataFrame

**Возвращает:** валидированный DataFrame.

### `save_results(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions) -> WriteResult`

Сохраняет результат через `PipelineOutputService`, при ошибках откатывается к реализации родителя.

**Параметры:**
- `df` — DataFrame с данными для сохранения
- `artifacts` — объект `WriteArtifacts` с путями к артефактам
- `options` — опции выполнения стадии

**Процесс:**
1. Попытка сохранения через `PipelineOutputService`
2. При ошибке — откат к базовой реализации родителя

**Возвращает:** `WriteResult` с информацией о записанных файлах.

## Обогащение данными

Пайплайн обогащает данные target информацией из:

- **UniProt**: идентификаторы и метаданные белков
- **IUPHAR**: классификация и метаданные рецепторов

## Related Components

- **PipelineBase**: базовый класс пайплайнов (см. `docs/02-pipelines/00-pipeline-base.md`)
- **ChemblWriteService**: сервис записи для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/common/04-chembl-write-service.md`)
