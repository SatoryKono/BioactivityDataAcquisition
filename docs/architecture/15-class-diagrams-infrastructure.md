# Class Diagrams - Infrastructure Layer

Диаграммы классов для слоя Infrastructure (bioetl.infrastructure).

## 1. Client Architecture

```mermaid
---
id: 9f5e7de8-3350-47cb-8b63-8ec00ddc9944
---
classDiagram
    class SourceClientABC {
        <<abstract>>
        +fetch_one(id)*
        +fetch_many(ids)*
        +iter_pages(request)*
        +metadata()*
    }

    class ChemblDataClientABC {
        <<abstract>>
        +request_activity(filters)*
        +request_assay(filters)*
        +request_target(filters)*
        +request_document(filters)*
        +request_molecule(filters)*
    }

    class ChemblDataClientHTTPImpl {
        -request_builder: ChemblRequestBuilderImpl
        -response_parser: ChemblResponseParserImpl
        -rate_limiter: RateLimiterABC
        -http: HttpClientMiddleware
        +request_activity(filters)
        +request_assay(filters)
        +iter_pages(request)
        +metadata()
        -_execute_request(url)
    }

    class UnifiedAPIClient {
        -base_client: ClientSession
        -retry_policy: RetryPolicyABC
        -circuit_breaker: CircuitBreakerImpl
        +request(method, url, **kwargs)
        +close()
    }

    SourceClientABC <|-- ChemblDataClientABC
    ChemblDataClientABC <|-- ChemblDataClientHTTPImpl
    ChemblDataClientHTTPImpl --> UnifiedAPIClient : uses
```

## 2. Request/Response Processing

```mermaid
classDiagram
    class RequestBuilderABC {
        <<abstract>>
        +build(params)*
        +with_pagination(offset, limit)* RequestBuilderABC
    }

    class ChemblRequestBuilderImpl {
        -base_url: str
        +for_endpoint(endpoint) RequestBuilderABC
        +build(params) str
        +with_pagination(offset, limit) RequestBuilderABC
    }

    class ResponseParserABC {
        <<abstract>>
        +parse(raw_response)* list[Record]
        +extract_metadata(raw_response)* dict
    }

    class ChemblResponseParserImpl {
        +parse(raw_response) list[Record]
        +extract_metadata(raw_response) dict
    }

    class PaginatorABC {
        <<abstract>>
        +get_items(response)* list[Record]
        +get_next_marker(response)* str | int | None
        +has_more(response)* bool
    }

    class ChemblPaginatorImpl {
        +get_items(response) list[Record]
        +get_next_marker(response) str | None
        +has_more(response) bool
    }

    RequestBuilderABC <|-- ChemblRequestBuilderImpl
    ResponseParserABC <|-- ChemblResponseParserImpl
    PaginatorABC <|-- ChemblPaginatorImpl
```

## 3. Rate Limiting and Retry

```mermaid
classDiagram
    class RateLimiterABC {
        <<abstract>>
        +acquire()*
        +wait_if_needed()*
    }

    class TokenBucketRateLimiterImpl {
        -rate: float
        -capacity: float
        -tokens: float
        -last_update: float
        +acquire()
        +wait_if_needed()
    }

    class RetryPolicyABC {
        <<abstract>>
        +max_attempts: int
        +should_retry(error, attempt)* bool
        +get_delay(attempt)* float
    }

    class ExponentialBackoffRetryImpl {
        -max_attempts: int
        -base_delay: float
        -max_delay: float
        +should_retry(error, attempt) bool
        +get_delay(attempt) float
    }

    class CircuitBreakerImpl {
        -state: CircuitState
        -failure_count: int
        -failure_threshold: int
        -timeout: float
        +call(func)
        +reset()
    }

    class CircuitState {
        <<Enum>>
        +CLOSED
        +OPEN
        +HALF_OPEN
    }

    RateLimiterABC <|-- TokenBucketRateLimiterImpl
    RetryPolicyABC <|-- ExponentialBackoffRetryImpl
    CircuitBreakerImpl --> CircuitState : uses
```

## 4. Output Writers

```mermaid
classDiagram
    class WriterABC {
        <<abstract>>
        +write(df, path, column_order)* WriteResult
    }

    class CsvWriterImpl {
        +write(df, path, column_order) WriteResult
        -_write_csv(df, path)
    }

    class ParquetWriterImpl {
        +write(df, path, column_order) WriteResult
        -_write_parquet(df, path)
    }

    class MetadataWriterABC {
        <<abstract>>
        +write_meta(metadata, path)*
    }

    class MetadataWriterImpl {
        +write_meta(metadata, path)
        -_write_yaml(data, path)
    }

    class UnifiedOutputWriter {
        -_writer: WriterABC
        -_metadata_writer: MetadataWriterABC
        -_config: DeterminismConfig
        -_atomic_op: AtomicFileOperation
        +write_result(df, output_path, entity_name, run_context, column_order) WriteResult
        -_stable_sort(df, context, column_order) DataFrame
        -_apply_column_order(df, column_order) DataFrame
    }

    WriterABC <|-- CsvWriterImpl
    WriterABC <|-- ParquetWriterImpl
    MetadataWriterABC <|-- MetadataWriterImpl
    UnifiedOutputWriter --> WriterABC : uses
    UnifiedOutputWriter --> MetadataWriterABC : uses
```

## 5. File Operations

```mermaid
classDiagram
    class AtomicFileOperation {
        +write_atomic(path, write_func)
        -_create_temp_path(path) Path
    }

    class ChecksumCalculator {
        +compute_file_sha256(path) str
        -_read_file_chunks(path) Iterator[bytes]
    }

    class CsvRecordSourceImpl {
        -_path: Path
        -_chunk_size: int | None
        -_csv_options: dict
        +iter_records() Iterable[RawRecord]
        +get_total_count() int | None
        -_chunk_dataframe(df) Iterator[DataFrame]
    }

    class IdListRecordSourceImpl {
        -_ids: list[str]
        -_extraction_service: ExtractionServiceABC
        +iter_records() Iterable[RawRecord]
        +get_total_count() int
    }

    AtomicFileOperation --> ChecksumCalculator : may use
```

## 6. Logging Infrastructure

```mermaid
classDiagram
    class LoggerAdapterABC {
        <<abstract>>
        +info(msg, **ctx)*
        +error(msg, **ctx)*
        +debug(msg, **ctx)*
        +warning(msg, **ctx)*
        +bind(**ctx)* LoggerAdapterABC
    }

    class UnifiedLoggerImpl {
        -_logger: BoundLogger
        +info(msg, **ctx)
        +error(msg, **ctx)
        +debug(msg, **ctx)
        +warning(msg, **ctx)
        +bind(**ctx) UnifiedLoggerImpl
    }

    class ProgressReporterABC {
        <<abstract>>
        +start(total)*
        +update(n)*
        +finish()*
    }

    class TqdmProgressReporterImpl {
        -_progress_bar: tqdm | None
        +start(total)
        +update(n)
        +finish()
    }

    LoggerAdapterABC <|-- UnifiedLoggerImpl
    ProgressReporterABC <|-- TqdmProgressReporterImpl
```

## 7. Configuration Management

```mermaid
classDiagram
    class PipelineConfig {
        +entity_name: str
        +provider: str
        +output_path: str
        +pagination: PaginationConfig
        +client: ClientConfig
        +storage: StorageConfig
        +logging: LoggingConfig
        +determinism: DeterminismConfig
        +qc: QcConfig
        +canonicalization: CanonicalizationConfig
        +business_key: BusinessKeyConfig
        +hashing: HashingConfig
        +normalization: NormalizationConfig
    }

    class PaginationConfig {
        +page_size: int
        +max_pages: int | None
    }

    class ClientConfig {
        +base_url: str
        +timeout: float
        +retry: RetryConfig
    }

    class DeterminismConfig {
        +stable_sort: bool
        +column_order: list[str] | None
    }

    class ConfigResolver {
        -_base_dir: Path
        -_profiles_dir: Path
        +resolve(pipeline_name, profile, overrides) PipelineConfig
        -_load_base_config(path) dict
        -_apply_profile(base_config, profile) dict
        -_apply_overrides(config, overrides) dict
    }

    PipelineConfig --> PaginationConfig : contains
    PipelineConfig --> ClientConfig : contains
    PipelineConfig --> DeterminismConfig : contains
    ConfigResolver --> PipelineConfig : creates
```

## 8. Cache Implementation

```mermaid
classDiagram
    class CacheABC {
        <<abstract>>
        +get(key)* T | None
        +set(key, value, ttl)*
        +invalidate(key)*
        +clear()*
    }

    class MemoryCacheImpl {
        -_cache: dict[str, tuple[T, float | None]]
        +get(key) T | None
        +set(key, value, ttl)
        +invalidate(key)
        +clear()
        -_is_expired(expiry_timestamp) bool
    }

    class FileCacheImpl {
        -_cache_dir: Path
        -_ttl: int | None
        +get(key) T | None
        +set(key, value, ttl)
        +invalidate(key)
        +clear()
        -_get_cache_path(key) Path
        -_is_expired(path) bool
    }

    CacheABC <|-- MemoryCacheImpl
    CacheABC <|-- FileCacheImpl
```

## 9. HTTP Middleware

```mermaid
classDiagram
    class HttpClientMiddleware {
        -base_client: ClientSession
        -retry_policy: RetryPolicyABC
        -circuit_breaker: CircuitBreakerImpl
        -rate_limiter: RateLimiterABC
        +request(method, url, **kwargs) Response
        -_apply_retry(func)
        -_apply_circuit_breaker(func)
        -_apply_rate_limit()
    }

    class UnifiedAPIClient {
        -base_client: ClientSession
        -middleware: HttpClientMiddleware
        +request(method, url, **kwargs) Response
        +close()
    }

    class ClientSession {
        +get(url, **kwargs) Response
        +post(url, **kwargs) Response
        +close()
    }

    HttpClientMiddleware --> ClientSession : uses
    UnifiedAPIClient --> HttpClientMiddleware : uses
```

## 10. Provider Components

```mermaid
classDiagram
    class ProviderComponents {
        <<Protocol>>
        +create_client(config) DataClientABC
        +create_normalization_service(config) NormalizationService
    }

    class ChemblProviderComponents {
        +create_client(config) ChemblDataClientABC
        +create_normalization_service(config) NormalizationService
    }

    class ProviderDefinition {
        +provider_id: ProviderId
        +config_class: Type[BaseProviderConfig]
        +components: ProviderComponents
    }

    class ChemblSourceConfig {
        +base_url: str
        +timeout: float
        +rate_limit: float
    }

    class BaseProviderConfig {
        +provider: str
    }

    ProviderComponents <|.. ChemblProviderComponents
    ProviderDefinition --> ProviderComponents : contains
    ProviderDefinition --> BaseProviderConfig : uses
    ChemblSourceConfig --|> BaseProviderConfig
```

