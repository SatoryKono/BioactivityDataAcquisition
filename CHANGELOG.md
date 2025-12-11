# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2025-12-10

### Breaking Changes

- `ChemblResponseParserImpl` now returns `list[dict]` instead of typed models
- `ExtractionServiceABC.iter_extract()` returns `Iterable[list[dict[str, Any]]]`
- `parser_registry.ENTITY_MODEL_REGISTRY` moved to `application.mappers.chembl.model_registry`
- Config loading requires `PipelineContainer.bootstrap()` to be called first

### Added

- `ChemblGenericResponseParser` - generic parser for ChEMBL API responses
- `RecordMapperABC` - application layer contract for record mapping
- `ChemblRecordMapper` - ChEMBL-specific record mapper
- `SchemaBootstrapService` - application service for schema lifecycle
- `SchemaContractProviderABC` - port for schema contract access

### Removed

- `ChemblResponseParserImpl` typed variant (use `ChemblGenericResponseParser`)
- `create_activity_parser()` (use `ChemblGenericResponseParser`)
- `ChemblActivityResponseParser` type alias
- Direct domain schema imports in infrastructure layer
- `parser_registry.__getattr__` deprecated API access handler
- `tests/bioetl/infrastructure/clients/chembl/test_response_parser.py` (deprecated typed parser tests)

### Migration Guide

See docs/migration/2.0-hexagonal-architecture.md

## [Unreleased]

### Removed

- **BREAKING**: `SimplePipelineContainer` class removed from `bioetl.interfaces.simple_container`. Use `ApplicationBootstrap` from `bioetl.application.bootstrap` or `create_default_bootstrap()` from `bioetl.interfaces.bootstrap_factory` instead.

### Changed

- **HTTP Configuration Refactoring**: Consolidated three overlapping HTTP configuration models into a single source of truth:
  - New `HttpClientConfig` class replaces `HttpClientSettings`, `HttpClientDefaults`, and `ClientConfig`
  - New `ProviderHttpConfig` extends `HttpClientConfig` with `base_url` for provider-specific configs
  - Field naming standardized: `timeout` → `timeout_sec`, `retries` → `max_retries`, `rate_limit` → `rate_limit_per_sec`
  - Added `retry_on_status`, `backoff_max`, `circuit_breaker_enabled` fields
  - Backward compatibility maintained via model validators and deprecated property aliases
- Добавлены типизированные поля `input_mode`/`input_path`/`csv_options` для пайплайнов; `cli.input_file` автоматически мигрирует с предупреждением.
- ChEMBL pipeline теперь выбирает источник записей явно (API/CSV/id-only) без колонковой эвристики; CLI умеет переопределять режим и CSV-опции.
- `HashService` больше не содержит собственной реализации `Hasher`: доменный фасад требует инжектируемый `HasherABC`, а фабрика по умолчанию использует `HasherImpl`.
- Документация и диаграммы ChEMBL переименованы (`TestItem` → `Molecule`), добавлены stub-схемы `CellTableSchema`/`TissueTableSchema`.
- Пересчитан `tests/project_rules/class_inventory_baseline.json`: текущее число классов 184 после удаления устаревших реализаций.

### Removed

- Удалена заглушка `assay_enrichment` из `ChemblSourceConfig`.
- Помечены deprecated несуществующие клиенты (PubChem, PubMed, Crossref, UniProt, SemanticScholar) в документации.
- Удалены устаревшие интерфейсы (`default_provider_registry()`, `bioetl.application.services.chembl_extraction`) и middleware-шимы.
- Удалены `src/bioetl/infrastructure/transform/impl/hash_service_impl.py`, `src/bioetl/domain/clients/base/logging/`, `src/bioetl/domain/configs/base.py`, `src/bioetl/domain/contracts.py`.

### Deprecated

- `HttpClientSettings`, `HttpClientDefaults`, `ClientConfig`, `HTTP_CLIENT_DEFAULTS` — use `HttpClientConfig` instead
- `BaseProviderConfig.http_client`, `BaseProviderConfig.client` — use `.http` field instead
- `RuntimeConfig.client` — use `.http` field instead
- `ProviderDefinition.http_client` — use `.http` field instead
- `ProviderRegistryEntryModel.http_client` — use `.http` field instead
- `ClientConfig.from_http_settings()` method removed — use `HttpClientConfig` constructor with field mapping

### Breaking Changes

- HTTP configuration field names changed (backward compatibility maintained via validators):
  - `timeout` → `timeout_sec`
  - `retries` → `max_retries`
  - `rate_limit` → `rate_limit_per_sec`
  - `circuit_breaker_recovery_time` → `circuit_breaker_recovery_sec`
- `BaseProviderConfig` now uses `http: ProviderHttpConfig` instead of `http_client: HttpClientSettings` + `client: ClientConfig`
- Factory functions (`build_http_client`, `build_rate_limiter`) signature simplified to use single `config: HttpClientConfig` parameter
- Поле `assay_enrichment` удалено из конфигурации. Если использовалось в YAML-конфигах — удалить.
- Флаг `features.enable_provider_loader_port` больше не поддерживается: порт загрузчика провайдеров активен всегда, а CLI/REST/MQ требуют валидного `providers.yaml` или явного `ProviderRegistry`.
- `HashService` больше нельзя инстанцировать без `HasherABC`; проекты должны создавать сервис через `bioetl.infrastructure.transform.factories.default_hash_service()` или явно передавать `Hasher`.
- `ProgressReporterABC` теперь экспортируется из `bioetl.domain.observability` (shim `domain.clients.base.logging` удалён).
- `domain.configs.base` (re-export) и `domain.contracts` больше не доступны; импортируйте `PipelineConfig` и extraction-порты напрямую.
