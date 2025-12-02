# 00 Document ChEMBL Overview

## Описание

`ChemblDocumentPipeline` — скелет пайплайна для сущности "document" ChEMBL с дополнительным обогащением из внешних источников. Реализует стандартные стадии ETL и дополняет этап преобразования внешними данными.

## Модуль

`src/bioetl/pipelines/chembl/document/run.py`

## Наследование

Пайплайн наследуется от `PipelineBase` и использует общую инфраструктуру ChEMBL-пайплайнов. Реализует стандартные стадии ETL и дополняет этап преобразования внешними данными.

## Основные методы

### `build_descriptor(self)`

Построить дескриптор извлечения (переопределяет базовый метод).

### `domain_enrich(self, df: pd.DataFrame) -> pd.DataFrame`

Обогащение данных (вызывает цепочку обогащения после базового преобразования). Выполняет обогащение данных document информацией из внешних источников. Добавляет метаданные из PubMed, Crossref и других источников.

### `validate(self, df: pd.DataFrame, options: StageExecutionOptions) -> pd.DataFrame`

Валидация данных с дополнительной проверкой `document_chembl_id`. Переопределяет базовую валидацию для добавления специфичных проверок.

### `save_results(self, df: pd.DataFrame, artifacts: WriteArtifacts, options: StageExecutionOptions) -> WriteResult`

Сохранение результатов с попыткой использования внешнего сервиса вывода, с fallback на базовый метод при ошибках.

## Обогащение данными

Пайплайн обогащает данные document информацией из:
- **PubMed**: метаданные статей
- **Crossref**: DOI и метаданные публикаций
- **Semantic Scholar**: семантические метаданные

## Related Components

- **PipelineBase**: базовый класс пайплайнов (см. `docs/02-pipelines/00-pipeline-base.md`)
- **ChemblWriteService**: сервис записи для ChEMBL-пайплайнов (см. `docs/02-pipelines/chembl/common/04-chembl-write-service.md`)
- **PubMedClient**: клиент для API PubMed (см. `docs/02-pipelines/clients/00-pubmed-client.md`)
- **CrossrefClient**: клиент для API CrossRef (см. `docs/02-pipelines/clients/01-crossref-client.md`)

