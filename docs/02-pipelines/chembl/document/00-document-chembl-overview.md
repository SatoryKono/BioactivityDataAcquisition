# 00 Document ChEMBL Overview

## Описание

`ChemblDocumentPipeline` — скелет пайплайна для сущности "document" ChEMBL с дополнительным обогащением из внешних источников. Реализует стандартные стадии ETL и дополняет этап преобразования внешними данными.

## Модуль

`src/bioetl/pipelines/chembl/document/run.py`

## Наследование

Пайплайн наследуется от `PipelineBase` и использует общую инфраструктуру ChEMBL-пайплайнов.

## Основные методы

### `domain_enrich(self, df: pd.DataFrame) -> pd.DataFrame`

Выполняет обогащение данных document информацией из внешних источников. Добавляет метаданные из PubMed, Crossref и других источников.

### `validate(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Выполняет валидацию данных document. Переопределяет базовую валидацию для добавления специфичных проверок.

### `save_results(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions) -> WriteResult`

Сохраняет результаты пайплайна document с учётом специфики сущности и обогащения внешними данными.

## Обогащение данными

Пайплайн обогащает данные document информацией из:
- **PubMed**: метаданные статей
- **Crossref**: DOI и метаданные публикаций
- **Semantic Scholar**: семантические метаданные

## Related Components

- **PipelineBase**: базовый класс пайплайнов (см. `docs/02-pipelines/00-pipeline-base.md`)
- **ChemblWriteService**: сервис записи для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/17-chembl-write-service.md`)
- **PubMedClient**: клиент для API PubMed (см. `docs/02-pipelines/clients/18-pubmed-client.md`)
- **CrossrefClient**: клиент для API CrossRef (см. `docs/02-pipelines/clients/19-crossref-client.md`)

