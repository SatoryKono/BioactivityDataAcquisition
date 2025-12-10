# ABC Index
<!-- generated -->

- `DataClientABC` — `bioetl.domain.clients.contracts.DataClientABC`
  - Базовый контракт клиента источника данных.

- `RequestBuilderABC` — `bioetl.domain.clients.base.contracts.RequestBuilderABC`
  - Паттерн Builder для создания запросов.

- `ResponseParserABC` — `bioetl.domain.clients.base.contracts.ResponseParserABC`
  - Разбор ответов API.

- `ResponseParserPortABC` — `bioetl.domain.ports.parsing.ResponseParserPortABC`
  - Порт для парсинга сырых ответов API без знания доменных моделей. Реализации в infrastructure слое парсят provider-specific форматы ответов, в то время как domain слой остается независимым от этих деталей.

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
  - Загрузчик реестра провайдеров из конфигурации. Default factory: ``bioetl.infrastructure.config.provider_registry.default_provider_registry_loader``. Implementations: ``ProviderRegistryLoader``.

- `PipelineContainerABC` — `bioetl.application.pipelines.contracts.PipelineContainerABC`
  - Контейнер пайплайна.

- `PipelineHookABC` — `bioetl.domain.pipelines.contracts.PipelineHookABC`
  - Хуки жизненного цикла пайплайна.

- `ErrorPolicyABC` — `bioetl.domain.pipelines.contracts.ErrorPolicyABC`
  - Политика обработки ошибок.

- `CLICommandABC` — `bioetl.interfaces.cli.contracts.CLICommandABC`
  - Интерфейс команды CLI.

- `ProviderRegistryABC` — `bioetl.domain.provider_registry.ProviderRegistryABC`
  - Порт для чтения и регистрации определений провайдеров (подключается явно без глобального singleton).

- `LoggingPortABC` — `bioetl.domain.observability.contracts.LoggingPortABC`
  - Порт структурированного логгирования. Default factory: ``bioetl.infrastructure.observability.factories.default_logging_port``. Implementations: ``StructuredLoggerImpl``.

- `ProgressReporterABC` — `bioetl.domain.observability.contracts.ProgressReporterABC`
  - Интерфейс отчетности о прогрессе. Default factory: ``bioetl.infrastructure.logging.factories.default_progress_reporter``. Implementations: ``TqdmProgressReporterImpl``.

- `TracingPortABC` — `bioetl.domain.observability.contracts.TracingPortABC`
  - Порт для распределенной трассировки. Default factory: ``bioetl.infrastructure.observability.factories.default_tracing_port``. Implementations: ``TracingAdapterImpl``.

- `HasherABC` — `bioetl.domain.transform.contracts.HasherABC`
  - Хеширование строк.

- `HashServiceABC` — `bioetl.domain.transform.contracts.HashServiceABC`
  - Фасад для вычисления hash_row/hash_business_key и служебных колонок. Default factory: `bioetl.infrastructure.transform.factories.default_hash_service`. Implementation: `bioetl.domain.transform.hash_service.HashService`.

- `TimestampProviderABC` — `bioetl.domain.transform.contracts.TimestampProviderABC`
  - Провайдер временных меток для детерминированных артефактов.

- `IndexGeneratorABC` — `bioetl.domain.transform.contracts.IndexGeneratorABC`
  - Генератор индексов для строк данных.

- `NormalizationServiceABC` — `bioetl.domain.transform.contracts.NormalizationServiceABC`
  - Сервис нормализации данных. Обязательные операции: normalize(df), normalize_record(record), ensure_numeric_columns(df). Default factory: ``bioetl.infrastructure.transform.factories.default_normalization_service``. Implementations: ``DefaultNormalizationTransformerImpl``, ``ChemblNormalizationServiceImpl``.

- `ValidatorABC` — `bioetl.domain.validation.contracts.ValidatorABC`
  - Валидация данных. Default factory: ``bioetl.infrastructure.validation.factories.default_validator_factory``. Implementations: ``PanderaValidatorImpl`` (`bioetl.infrastructure.validation.impl.pandera_validator`).

- `SchemaProviderABC` — `bioetl.domain.validation.contracts.SchemaProviderABC`
  - Провайдер схем данных. Default factory: ``bioetl.infrastructure.validation.factories.default_schema_provider_factory``. Implementations: ``SchemaRegistry`` (`bioetl.domain.schemas.registry.SchemaRegistry`).

- `ValidatorFactoryABC` — `bioetl.domain.validation.contracts.ValidatorFactoryABC`
  - Фабрика валидаторов под конкретную схему. Default factory: ``bioetl.infrastructure.validation.factories.default_validator_factory``. Implementations: ``PanderaValidatorFactory``.

- `SchemaProviderFactoryABC` — `bioetl.domain.validation.contracts.SchemaProviderFactoryABC`
  - Фабрика провайдеров схем. Default factory: ``bioetl.infrastructure.validation.factories.default_schema_provider_factory``. Implementations: ``PanderaSchemaProviderFactory``.

- `QualityReportABC` — `bioetl.domain.clients.base.output.contracts.QualityReportABC`
  - Порт генератора QC-отчетов.

- `OutputFrameConverterABC` — `bioetl.domain.clients.base.output.contracts.OutputFrameConverterABC`
  - DataFrame → DataFrame конвертер для пост-обработки перед записью. Default factory: ``bioetl.infrastructure.output.converters.factories.default_output_frame_converter``. Implementations: ``NoopConverter``, ``RenameColumnsConverter``, ``DropNaRowsConverter``.

- `LoaderABC` — `bioetl.domain.pipelines.contracts.LoaderABC`
  - Компонент записи артефактов пайплайна (данные, метаданные, QC).