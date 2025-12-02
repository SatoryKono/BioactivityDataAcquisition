# 01 Chembl Pipeline Base

## Классы
- **ChemblPipelineBase** — расширяет `PipelineBase` ChEMBL-спецификой: загрузка релиза, конфиг клиента, общие хуки.
- **ChemblCommonPipeline** — типовой шаблон стадий для ChEMBL сущностей, подключает общий клиент и дескрипторы.
- **ChemblDocumentPipeline** — специализация для документных данных с обогащением метаданных.

## Расширение PipelineBase
- Добавляет работу с `ChemblDescriptorFactory`, формируя StageDescriptor для каждой сущности.
- Определяет общие prepare_run/finalize_run шаги (например, запись версии релиза и параметров выборки).
- Позволяет переопределять только специфичные transform/validate/write части, сохраняя общий orchestrator.

## Роль ChemblDescriptorFactory
- Генерирует дескрипторы выборки (фильтры, размер страниц, release) для Activity/Assay/Target/TestItem/Document.
- Обеспечивает единообразие конфигураций и упрощает добавление новых ChEMBL пайплайнов.
