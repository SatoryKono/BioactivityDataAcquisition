# 00 Target ChEMBL Overview

## Описание

`ChemblTargetPipeline` — каркас пайплайна для сущности "target" в ChEMBL с обогащением данными UniProt/IUPHAR. Выполняет стандартный ETL-процесс для target, добавляя проверку на заполненность идентификаторов.

## Модуль

`src/bioetl/pipelines/chembl/target/run.py`

## Наследование

Пайплайн наследуется от `PipelineBase` и использует общую инфраструктуру ChEMBL-пайплайнов.

## Основные методы

### `validate(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Выполняет валидацию данных target с проверкой на заполненность идентификаторов (UniProt, IUPHAR). Переопределяет базовую валидацию для добавления специфичных проверок.

### `save_results(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions) -> WriteResult`

Сохраняет результаты пайплайна target с учётом специфики сущности и обогащения внешними данными.

## Обогащение данными

Пайплайн обогащает данные target информацией из:

- **UniProt**: идентификаторы и метаданные белков
- **IUPHAR**: классификация и метаданные рецепторов

## Related Components

- **PipelineBase**: базовый класс пайплайнов (см. `docs/02-pipelines/00-pipeline-base.md`)
- **ChemblWriteService**: сервис записи для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/17-chembl-write-service.md`)
