# 00 Index

## Orchestration & Monitoring
- **PipelineHookABC** — хуки prepare_run/finalize_run, точка расширения для мониторинга.
- **ErrorPolicyABC** — политика обработки ошибок стадий.
- **LoggerAdapterABC / ProgressReporterABC / TracerABC** — адаптеры логирования, прогресса и трассировки.

## Data Access (Client)
- **BaseClient** — базовый контракт клиентов внешних API.
- **RequestBuilderABC / ResponseParserABC / PaginatorABC** — строитель запросов, парсер ответов и пагинатор.
- **UnifiedAPIClient** — фасад, объединяющий вызовы клиентов и инфраструктуру (ретраи, лимиты).

## Transformation
- **TransformerABC / NormalizerABC** — преобразование сырых записей в нормализованные таблицы.
- **DescriptorFactory** — генератор дескрипторов выборки для пайплайнов.

## Validation
- **ValidatorABC** — применение схем к таблицам.
- **SchemaProviderABC / SchemaRegistry** — регистрация и выдача Pandera-схем.
- **ValidationService** — координация валидации и сбор ValidationResult.

## Output
- **WriterABC / MetadataWriterABC** — запись таблиц и метаданных.
- **UnifiedOutputWriter** — объединённая запись данных, QC и checksum.
