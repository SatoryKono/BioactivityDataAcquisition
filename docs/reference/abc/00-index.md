# ABC Interfaces Catalog

Полный каталог абстрактных базовых классов (ABC), определяющих контракты компонентов BioETL.

## Orchestration & Monitoring Layer

| ABC | Модуль | Методы | Описание |
|-----|--------|--------|----------|
| `StageABC` | `core.stage` | `run(context) -> StageResult`, `close() -> None` | Абстракция стадии пайплайна. |
| `PipelineHookABC` | `core.hooks` | `on_stage_start(stage, context)`, `on_stage_end(stage, result)`, `on_error(stage, error)` | Хуки жизненного цикла пайплайна. |
| `ErrorPolicyABC` | `core.errors` | `handle(error, context) -> ErrorAction`, `should_retry(error) -> bool` | Политика обработки ошибок (Retry/Skip/Fail). |
| `CLICommandABC` | `cli.base` | `register(app)`, `run_pipeline(config, options) -> RunResult` | Интеграция с CLI (Typer). |
| `LoggerAdapterABC` | `logging.adapter` | `info(msg, **ctx)`, `error(msg, **ctx)`, `debug(msg, **ctx)`, `bind(**ctx) -> Self` | Интерфейс структурированного логгера. |
| `ProgressReporterABC` | `logging.progress` | `start(total)`, `update(current)`, `finish()`, `report() -> ProgressReport` | Интерфейс отчетности о прогрессе. |
| `TracerABC` | `logging.tracer` | `start_span(name) -> Span`, `end_span(span)`, `inject_context(headers)` | Распределенная трассировка. |

## Data Access Layer (Client)

| ABC | Модуль | Методы | Описание |
|-----|--------|--------|----------|
| `SourceClientABC` | `clients.base.contracts` | `fetch_one(id) -> Record`, `fetch_many(ids) -> list[Record]`, `iter_pages(request) -> Iterator[Page]`, `metadata() -> SourceMetadata`, `close() -> None` | Основной контракт клиента источника данных. |
| `BaseExternalDataClient` | `clients.base.external` | Реализует `SourceClientABC` + `_build_request()`, `_parse_response()` | Базовая реализация для REST API. |
| `RequestBuilderABC` | `clients.base.contracts` | `build(params) -> ClientRequest`, `with_pagination(offset, limit) -> Self` | Паттерн Builder для запросов. |
| `ResponseParserABC` | `clients.base.contracts` | `parse(raw_response) -> list[Record]`, `extract_metadata(raw) -> dict` | Разбор ответов API. |
| `PaginatorABC` | `clients.base.contracts` | `get_items(response) -> list[Record]`, `get_next_marker(response) -> str`, `has_more(response) -> bool` | Стратегия пагинации. |
| `RateLimiterABC` | `clients.base.contracts` | `acquire() -> None`, `release() -> None`, `wait_if_needed() -> None` | Ограничение частоты запросов (QPS). |
| `RetryPolicyABC` | `clients.base.contracts` | `should_retry(error, attempt) -> bool`, `get_delay(attempt) -> float`, `max_attempts -> int` | Политика повторных попыток. |
| `CacheABC` | `clients.base.contracts` | `get(key) -> T`, `set(key, value, ttl) -> None`, `invalidate(key) -> None`, `clear() -> None` | Интерфейс кэширования. |
| `SecretProviderABC` | `clients.base.contracts` | `get_secret(name) -> str`, `refresh() -> None` | Поставщик секретов (env, vault). |
| `SideInputProviderABC` | `clients.base.contracts` | `get_side_input(name) -> DataFrame`, `refresh(name) -> None` | Провайдер побочных данных (справочников). |

## Transformation Layer

| ABC | Модуль | Методы | Описание |
|-----|--------|--------|----------|
| `TransformerABC` | `transform.base` | `transform(df) -> DataFrame`, `validate_input(df) -> None`, `validate_output(df) -> None` | Интерфейс трансформации DataFrame. |
| `LookupEnricherABC` | `transform.enrichers` | `enrich(df, lookup_key) -> DataFrame`, `load_lookup() -> DataFrame`, `get_lookup_columns() -> list[str]` | Обогащение по справочнику. |
| `BusinessKeyDeriverABC` | `transform.keys` | `derive(df) -> DataFrame`, `get_key_columns() -> list[str]`, `validate_uniqueness(df) -> bool` | Вычисление бизнес-ключей. |
| `DeduplicatorABC` | `transform.dedup` | `deduplicate(df) -> DataFrame`, `get_duplicate_count(df) -> int`, `get_strategy() -> MergeStrategyABC` | Устранение дубликатов. |
| `MergeStrategyABC` | `transform.merge` | `merge(records: list[Record]) -> Record`, `priority_key -> str` | Стратегия слияния записей. |
| `HasherABC` | `transform.hash` | `hash_row(row) -> str`, `hash_columns(df, columns) -> Series`, `algorithm -> str` | Хеширование строк. |

## Validation Layer

| ABC | Модуль | Методы | Описание |
|-----|--------|--------|----------|
| `ValidatorABC` | `validation.base` | `validate(df) -> ValidationResult`, `get_errors() -> list[ValidationError]`, `is_valid(df) -> bool` | Валидация данных. |
| `SchemaProviderABC` | `validation.provider` | `get_schema(name) -> pa.DataFrameModel`, `list_schemas() -> list[str]`, `register(name, schema) -> None` | Провайдер схем данных. |

## Output Layer

| ABC | Модуль | Методы | Описание |
|-----|--------|--------|----------|
| `WriterABC` | `output.base` | `write(df, path) -> WriteResult`, `supports_format(fmt) -> bool`, `atomic -> bool` | Запись данных в файл/БД. |
| `MetadataWriterABC` | `output.metadata` | `write_meta(meta, path) -> None`, `write_qc_report(report, path) -> None`, `generate_checksums(paths) -> dict` | Запись метаданных и отчетов. |

