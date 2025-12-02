# 00 Assay ChEMBL Overview

## Описание

`ChemblAssayPipeline` — основной класс пайплайна для выгрузки данных об ассаях из ChEMBL. Реализует этапы ETL для сущности assay (использует схему валидации `AssaySchema` и переопределяет stage-хуки для трансформации, валидации и сохранения данных).

## Модуль

`src/bioetl/pipelines/chembl/assay/run.py`

## Наследование

Пайплайн наследуется от `ChemblCommonPipeline` и использует общую инфраструктуру ChEMBL-пайплайнов. Переопределяет точки расширения для специфики assay.

## Основные методы

### `__init__(self, config: Mapping[str, Any], *, run_id: str | None = None)`

Инициализирует пайплайн с конфигурацией и опциональным идентификатором запуска.

**Параметры:**
- `config` — конфигурация пайплайна
- `run_id` — идентификатор запуска (опционально)

### `build_descriptor(self) -> Any`

Построить дескриптор извлечения данных для assay из ChEMBL.

**Возвращает:** дескриптор извлечения данных.

### `pre_transform(self, df: pd.DataFrame) -> pd.DataFrame`

Выполняет предварительную трансформацию данных перед основной стадией transform. Используется для специфичной для assay обработки данных, включая нормализацию вложенных параметров и обеспечение целостности данных.

**Параметры:**
- `df` — DataFrame для предварительной трансформации

**Процесс:**
1. Нормализация вложенных параметров через `_normalize_nested_parameters`
2. Обеспечение соответствия assay class через `_ensure_assay_class_mapping`
3. Проверка целостности target через `_ensure_target_integrity`

**Возвращает:** предварительно трансформированный DataFrame.

### `validate(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Выполняет валидацию данных assay через `AssaySchema`. Переопределяет базовую валидацию для добавления специфичных проверок.

**Параметры:**
- `df` — DataFrame для валидации
- `options` — опции выполнения стадии

**Возвращает:** валидированный DataFrame.

### `save_results(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions) -> WriteResult`

Сохраняет результаты пайплайна assay с учётом специфики сущности.

**Параметры:**
- `df` — DataFrame с результатами
- `artifacts` — артефакты записи
- `options` — опции выполнения стадии

**Возвращает:** результат записи.

## Внутренние методы

### `_normalize_nested_parameters(self, df: pd.DataFrame) -> pd.DataFrame`

Нормализует вложенные параметры assay в DataFrame, приводя их к структурированному виду.

**Параметры:**
- `df` — DataFrame с данными assay

**Возвращает:** DataFrame с нормализованными параметрами.

### `_ensure_assay_class_mapping(self, df: pd.DataFrame) -> pd.DataFrame`

Обеспечивает соответствие assay class в DataFrame, добавляя недостающие маппинги.

**Параметры:**
- `df` — DataFrame с данными assay

**Возвращает:** DataFrame с корректными маппингами assay class.

### `_ensure_target_integrity(self, df: pd.DataFrame) -> pd.DataFrame`

Проверяет и обеспечивает целостность данных target в DataFrame.

**Параметры:**
- `df` — DataFrame с данными assay

**Возвращает:** DataFrame с проверенной целостностью target.

## Related Components

- **ChemblCommonPipeline**: базовый класс для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/common/05-chembl-base-pipeline.md`)
- **AssaySchema**: схема валидации данных assay (см. `docs/02-pipelines/schemas/04-assay-schema.md`)
- **ChemblWriteService**: сервис записи для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/common/04-chembl-write-service.md`)
- **PipelineOutputService**: сервис вывода результатов (см. `docs/02-pipelines/core/00-pipeline-output-service.md`)
