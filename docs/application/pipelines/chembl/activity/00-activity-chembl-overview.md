# 00 Activity Chembl Overview

## Pipeline

**ChemblActivityPipeline** (`src/bioetl/application/pipelines/chembl/activity/run.py`) наследует `ChemblPipelineBase` и реализует поток ETL для сущности Activity.

## Архитектура и Компоненты

Пайплайн следует стандартной архитектуре, где логические роли распределены между методами и миксинами:

- **Extract**: Реализован в функции `extract_activity` (`src/bioetl/application/pipelines/chembl/activity/extract.py`).
  - Поддерживает два режима: чтение полного CSV (из `cli.input_file`) или дозагрузка данных из API по ID из CSV.
  - Использует `ChemblExtractionService` для взаимодействия с API.
  
- **Transform**: 
  - Базовая нормализация выполняется в методе `_do_transform`.
  - Финальная нормализация типов (строки, числа, даты) и очистка обеспечивается миксином `NormalizerMixin` (метод `normalize_fields`), который используется в `ChemblPipelineBase`.
  
- **Hash & Deduplicate**: 
  - Вычисление `hash_business_key` и `hash_row` выполняется сервисом `HashService`, который вызывается в базовом классе `PipelineBase` после стадии трансформации.
  - Поля для бизнес-ключа задаются в конфигурации (`hashing.business_key_fields`).

- **Validate**: 
  - Выполняется `ValidationService` с использованием Pandera-схемы `ActivitySchema` (`src/bioetl/domain/schemas/chembl/activity.py`).
  - Проверяет типы данных, форматы (regex для ChEMBL ID) и допустимые значения.

- **Load (Write)**:
  - `UnifiedOutputWriter` сохраняет данные в CSV/Parquet, обеспечивает атомарную запись и генерирует метаданные (`meta.yaml`) и отчеты качества.

## Особенности

- **Гибридный Extract**: Пайплайн умеет работать как "чистый" ETL из API, так и как обогатитель списка ID из локального файла.
- **Нормализация**: Автоматическое приведение пустых строк к NULL, тримминг пробелов и унификация форматов чисел через `NormalizerMixin`.
- **Контекст**: В метаданные автоматически добавляется версия релиза ChEMBL (`chembl_release`).

## Конфигурация

Файл: `configs/pipelines/chembl/activity.yaml`
Наследует: `configs/profiles/chembl_default.yaml`

## Зависимости

Опирается на базовые компоненты инфраструктуры: `UnifiedAPIClient`, `ConfigResolver`, `UnifiedLogger`.
