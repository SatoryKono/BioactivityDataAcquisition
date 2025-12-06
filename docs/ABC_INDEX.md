# ABC Index
<!-- generated -->

- `SourceClientABC` — `bioetl.domain.clients.base.contracts.SourceClientABC`
  - Основной контракт клиента источника данных. Наследует доменный контракт DataClientABC.

- `RequestBuilderABC` — `bioetl.domain.clients.base.contracts.RequestBuilderABC`
  - Паттерн Builder для создания запросов.

- `ResponseParserABC` — `bioetl.domain.clients.base.contracts.ResponseParserABC`
  - Разбор ответов API.

- `PaginatorABC` — `bioetl.domain.clients.base.contracts.PaginatorABC`
  - Стратегия пагинации.

- `RateLimiterABC` — `bioetl.domain.clients.base.contracts.RateLimiterABC`
  - Ограничение частоты запросов.

- `RetryPolicyABC` — `bioetl.domain.clients.base.contracts.RetryPolicyABC`
  - Политика повторных попыток.

- `CacheABC` — `bioetl.domain.clients.base.contracts.CacheABC`
  - Интерфейс кэширования.

- `SecretProviderABC` — `bioetl.domain.clients.base.contracts.SecretProviderABC`
  - Поставщик секретов (env, vault).

- `SideInputProviderABC` — `bioetl.domain.clients.base.contracts.SideInputProviderABC`
  - Провайдер побочных данных (справочников).

- `ProviderRegistryLoaderABC` — `bioetl.domain.provider_registry.ProviderRegistryLoaderABC`
  - Загрузчик реестра провайдеров из конфигурации. Default factory: ``bioetl.infrastructure.clients.provider_registry_loader.default_provider_registry_loader``. Implementations: ``ProviderRegistryLoader``.

- `PipelineContainerABC` — `bioetl.application.pipelines.contracts.PipelineContainerABC`
  - Контейнер пайплайна.

- `StageABC` — `bioetl.domain.pipelines.contracts.StageABC`
  - Абстракция стадии пайплайна.

- `PipelineHookABC` — `bioetl.domain.pipelines.contracts.PipelineHookABC`
  - Хуки жизненного цикла пайплайна.

- `ErrorPolicyABC` — `bioetl.domain.pipelines.contracts.ErrorPolicyABC`
  - Политика обработки ошибок.

- `CLICommandABC` — `bioetl.interfaces.cli.contracts.CLICommandABC`
  - Интерфейс команды CLI.

- `ProviderRegistryABC` — `bioetl.domain.provider_registry.ProviderRegistryABC`
  - Порт для чтения определений провайдеров.

- `MutableProviderRegistryABC` — `bioetl.domain.provider_registry.MutableProviderRegistryABC`
  - Мутируемый порт для регистрации определений провайдеров.

- `LoggerAdapterABC` — `bioetl.domain.clients.base.logging.contracts.LoggerAdapterABC`
  - Интерфейс структурированного логгера. Default factory: ``bioetl.infrastructure.logging.factories.default_logger``. Implementations: ``UnifiedLoggerImpl``.

- `ProgressReporterABC` — `bioetl.domain.clients.base.logging.contracts.ProgressReporterABC`
  - Интерфейс отчетности о прогрессе. Default factory: ``bioetl.infrastructure.logging.factories.default_progress_reporter``. Implementations: ``TqdmProgressReporterImpl``.

- `TracerABC` — `bioetl.domain.clients.base.logging.contracts.TracerABC`
  - Интерфейс распределенной трассировки. Implementations expected to be provided by infrastructure tracing backends.

- `HasherABC` — `bioetl.domain.transform.contracts.HasherABC`
  - Хеширование строк.

- `HashServiceABC` — `bioetl.domain.transform.contracts.HashServiceABC`
  - Фасад для вычисления hash_row/hash_business_key и служебных колонок. Default factory: `bioetl.infrastructure.transform.factories.default_hash_service`. Implementation: `bioetl.infrastructure.transform.impl.hash_service_impl.HashServiceImpl`.

- `NormalizationServiceABC` — `bioetl.domain.transform.contracts.NormalizationServiceABC`
  - Сервис нормализации данных в DataFrame. Обязательные операции: - normalize: нормализация единичной записи - normalize_fields: пакетная нормализация DataFrame по конфигурации - normalize_dataframe: совместимый алиас для normalize_fields - normalize_batch: пакетная нормализация чанка - normalize_series: нормализация столбца по конфигурации. Default factory: ``bioetl.infrastructure.transform.factories.default_normalization_service``. Implementations: ``NormalizationServiceImpl``, ``ChemblNormalizationService``.

- `ValidatorABC` — `bioetl.domain.validation.contracts.ValidatorABC`
  - Валидация данных.

- `SchemaProviderABC` — `bioetl.domain.validation.contracts.SchemaProviderABC`
  - Провайдер схем данных.

- `WriterABC` — `bioetl.domain.clients.base.output.contracts.WriterABC`
  - Запись данных в файл. Default factory: ``bioetl.infrastructure.output.factories.default_writer``. Implementations: ``CsvWriterImpl``, ``ParquetWriterImpl``.

- `MetadataWriterABC` — `bioetl.domain.clients.base.output.contracts.MetadataWriterABC`
  - Запись метаданных и отчетов. Default factory: ``bioetl.infrastructure.output.factories.default_metadata_writer``. Implementations: ``MetadataWriterImpl``.

- `QualityReportABC` — `bioetl.domain.clients.base.output.contracts.QualityReportABC`
  - Порт генератора QC-отчетов.

- `OutputWriterABC` — `bioetl.domain.clients.base.output.contracts.OutputWriterABC`
  - Фасад записи результатов пайплайна (данные, метаданные, QC).
