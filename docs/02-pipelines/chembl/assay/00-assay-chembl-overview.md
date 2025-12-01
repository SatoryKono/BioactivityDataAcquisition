# 00 Assay ChEMBL Overview

## Описание

`ChemblAssayPipeline` — каркас пайплайна для выгрузки данных об биоактивности типа "assay" из ChEMBL. Наследует общий функционал ChEMBL-пайплайнов и переопределяет точки расширения для специфики assay.

## Модуль

`src/bioetl/pipelines/chembl/assay/run.py`

## Наследование

Пайплайн наследуется от `PipelineBase` и использует общую инфраструктуру ChEMBL-пайплайнов.

## Основные методы

### `pre_transform(self, df: pd.DataFrame) -> pd.DataFrame`

Выполняет предварительную трансформацию данных перед основной стадией transform. Используется для специфичной для assay обработки данных.

### `validate(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Выполняет валидацию данных assay. Переопределяет базовую валидацию для добавления специфичных проверок.

### `save_results(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions) -> WriteResult`

Сохраняет результаты пайплайна assay с учётом специфики сущности.

## Related Components

- **PipelineBase**: базовый класс пайплайнов (см. `docs/02-pipelines/00-pipeline-base.md`)
- **ChemblWriteService**: сервис записи для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/17-chembl-write-service.md`)
