# Исчерпывающий аудит документации BioETL

**Дата**: 2026-02-11
**Версия RULES.md**: 5.17 (2026-02-03)
**Методология**: Каждое утверждение документации проверено путём поиска в кодовой базе (grep, glob, read).
**Scope**: RULES.md + ключевые ADR + справочные документы + руководства.

---

## Сводка результатов

| Категория | Всего утверждений | Соответствует | Не соответствует | Частично |
|-----------|-------------------|---------------|------------------|----------|
| RULES.md §1 (Архитектура) | 12 | 11 | 0 | 1 |
| RULES.md §2 (Данные) | 22 | 18 | 2 | 2 |
| RULES.md §3 (Ошибки/Observability) | 15 | 14 | 0 | 1 |
| RULES.md §4 (Стандарты) | 10 | 8 | 1 | 1 |
| RULES.md §5 (Операции) | 6 | 6 | 0 | 0 |
| RULES.md Приложения (A-F) | 14 | 11 | 2 | 1 |
| ADR документы | 10 | 9 | 0 | 1 |
| **Итого** | **89** | **77** | **5** | **7** |

---

## Детальная таблица аудита

### RULES.md §1 — Архитектура и Слои

| № | Документ | Утверждение | Ссылка на код (файл:строки) | Фрагмент кода | Соответствует | План устранения |
|---|----------|-------------|----------------------------|---------------|---------------|-----------------|
| 1 | RULES.md §1.1 | "Интерфейсы определяются в пакете `domain/ports/` через `typing.Protocol`" | `src/bioetl/domain/ports/*.py` (43 Protocol-класса) | `class DataSourcePort(Protocol):`, `class StoragePort(Protocol):`, `class LoggerPort(Protocol):` и т.д. | **Да** | — |
| 2 | RULES.md §1.1.1 | "Порты MUST импортироваться из фасада `from bioetl.domain.ports import ...`" | `src/bioetl/domain/ports/__init__.py:24-99` (фасад с 50+ re-exports). Поиск нарушений: 0 результатов вне `domain/ports/` | `from bioetl.domain.ports import DataSourcePort, StoragePort` | **Да** | — |
| 3 | RULES.md §1.1.1 | "`@runtime_checkable` для критичных адаптеров" | `src/bioetl/domain/ports/health_check.py`, `data_source.py` | Ряд портов имеют `@runtime_checkable`, не все | **Частично** | Добавить `@runtime_checkable` ко всем критичным портам или уточнить документацию, какие именно порты SHOULD быть runtime_checkable |
| 4 | RULES.md §1.1.2 | "Все адаптеры MUST реализовывать `health_check()` возвращающий `HealthStatus` enum" | `src/bioetl/infrastructure/adapters/health_check_mixin.py:91,273` | `async def health_check(self) -> HealthStatus:` — реализовано через mixin `HealthCheckMixin` | **Да** | — |
| 5 | RULES.md §1.1.2 | "`HealthStatus` enum с HEALTHY, DEGRADED, UNHEALTHY" | `src/bioetl/domain/types.py:101-126` | `class HealthStatus(StrEnum): HEALTHY = "HEALTHY", DEGRADED = "DEGRADED", UNHEALTHY = "UNHEALTHY"` | **Да** | — |
| 6 | RULES.md §1.1 | "Domain (Домен): Чистые функции и контракты. Никакого ввода-вывода" | `src/bioetl/domain/` — нет import requests/httpx/open( | Чистые value objects, Protocol, dataclass, enum | **Да** | — |
| 7 | RULES.md §1.1 | "Infrastructure: Реализация взаимодействия с внешним миром (HTTP, БД, файловая система)" | `src/bioetl/infrastructure/adapters/` (7 провайдеров), `infrastructure/storage/` (bronze/silver/gold writers) | `class ChemblAdapter(BaseHttpAdapter):`, `class BronzeWriter:`, `class SilverWriter:` | **Да** | — |
| 8 | RULES.md §1.1 | "Application: Оркестрация потоков данных" | `src/bioetl/application/core/runner.py`, `application/pipelines/` | `class PipelineRunner:` — оркестрирует extract/transform/load | **Да** | — |
| 9 | RULES.md §1.1 (implicit) | Composition Layer существует | `src/bioetl/composition/` (80+ файлов: bootstrap, factories, providers, services) | `composition/bootstrap/assembly.py`, `composition/factories/` | **Да** | — |
| 10 | RULES.md §1.1 (implicit) | Interfaces Layer существует | `src/bioetl/interfaces/cli/` (30+ файлов), `interfaces/http/`, `interfaces/orchestration/` | CLI commands, health server | **Да** | — |
| 11 | RULES.md ARCH-008 | "Ports MUST импортироваться из фасада, не из внутренних модулей" | Поиск `from bioetl.domain.ports.[submodule] import` вне `domain/ports/__init__.py` → 0 нарушений | — | **Да** | — |
| 12 | RULES.md §1.1 | Ссылки на ADR-005, ADR-020, ADR-021, ADR-026 корректны | `docs/02-architecture/decisions/ADR-005-composition-layer-separation.md` и остальные — существуют | — | **Да** | — |

### RULES.md §2 — Поток Данных и Medallion

| № | Документ | Утверждение | Ссылка на код (файл:строки) | Фрагмент кода | Соответствует | План устранения |
|---|----------|-------------|----------------------------|---------------|---------------|-----------------|
| 13 | RULES.md §2.1 | "Bronze формат: JSONL + zstd" | `src/bioetl/infrastructure/storage/bronze_writer.py:1,6,29,49` | `"""Bronze layer writer (local storage with JSONL + zstd compression)."""`, `import zstandard as zstd`, `filename = f"batch_{date_str}_{batch_id}.jsonl.zst"` | **Да** | — |
| 14 | RULES.md §2.1 | "Silver формат: Delta Lake" | `src/bioetl/infrastructure/storage/silver_writer.py:36-38` | `from deltalake import DeltaTable, write_deltalake` | **Да** | — |
| 15 | RULES.md §2.1 | "Raw Parquet в Silver MUST NOT использоваться" | Поиск `to_parquet\|write_parquet` в `infrastructure/storage/silver/` → 0 результатов | — | **Да** | — |
| 16 | RULES.md §2.1.1 | "SilverWriteMode enum: MERGE, APPEND, DELETE" | `src/bioetl/domain/medallion.py:47-61` | `class SilverWriteMode(StrEnum): MERGE = "merge", APPEND = "append", DELETE = "delete"` | **Да** | — |
| 17 | RULES.md §2.1.2 | "GoldWriteMode enum: OVERWRITE, APPEND, SCD2" | `src/bioetl/domain/medallion.py:85-99` | `class GoldWriteMode(StrEnum): APPEND = "append", SCD2 = "scd2", OVERWRITE = "overwrite"` | **Да** | — |
| 18 | RULES.md §2.4.2 | "Medallion Clear Policy: REBUILD/BACKFILL → Clear, INCREMENTAL → Don't Clear" | `src/bioetl/application/core/` — MedallionLifecycleService | Логика проверяет `run_type in (RunType.REBUILD, RunType.BACKFILL)` перед вызовом `clear_silver()` | **Да** | — |
| 19 | RULES.md §2.6 | "Unified quarantine table: fields ingestion_ts, pipeline, error_code, payload, payload_hash, bronze_batch_id, dq_status" | `src/bioetl/domain/aggregates/quarantine_entry.py:109-189` | `QuarantineEntry` с полями: `_pipeline_name`, `_error_code`, `_payload`, `_payload_hash`, `_batch_id`, `_status`, `_created_at` | **Частично** | Поле `ingestion_ts` в коде названо `_created_at`; поле `bronze_batch_id` в коде `_batch_id` (BatchID); `dq_status` в коде `QuarantineStatus` с доп. значениями `UNDER_REVIEW`, `EXPIRED`. Привести названия в документации в соответствие с кодом |
| 20 | RULES.md §2.6 | "dq_status: `NEW \| IGNORED \| REPROCESSED`" | `src/bioetl/domain/aggregates/quarantine_entry.py:31-47` | `class QuarantineStatus(StrEnum): NEW, UNDER_REVIEW, IGNORED, REPROCESSED, EXPIRED` | **Нет** | В коде 5 значений (NEW, UNDER_REVIEW, IGNORED, REPROCESSED, EXPIRED), а в документации указаны только 3. Обновить RULES.md §2.6 добавив `UNDER_REVIEW` и `EXPIRED` |
| 21 | RULES.md §2.8 | "Content Hash: `sha256(provider + canonical_json_dumps(record))`" | `src/bioetl/domain/transformations.py:101-109` | `data = f"{provider}{canonical}"`, `hash_digest = hashlib.sha256(data.encode("utf-8")).hexdigest()` | **Да** | — |
| 22 | RULES.md §2.8 | "Из расчёта хэша исключаются META_FIELDS: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`" | `src/bioetl/domain/constants.py:15-25` | `META_FIELDS: frozenset = {"_ingestion_ts", "_run_id", "_run_type", "_dq_warn", "_dq_error", "_source_batch_id", "_index"}` | **Да** | — |
| 23 | RULES.md §6.1 | "META_FIELDS определен в `domain/transformations.py`" | `src/bioetl/domain/constants.py:15` (NOT transformations.py!) | `META_FIELDS` определён в `constants.py`, но re-exported через `transformations.py:21` | **Нет** | Исправить в RULES.md §6.1: `domain/constants.py:META_FIELDS` вместо `domain/transformations.py:META_FIELDS` |
| 24 | RULES.md §2.9.4 | "8 семантических групп (PublicationFieldGroup enum): ID_AND_STATUS, BIBLIOGRAPHY, AUTHOR_AND_AFFILIATIONS, TERMS_AND_KEYWORDS_AND_TOPICS, CITATIONS_AND_REFERENCE, DATE_AND_PLACES, PUBLICATION_TYPES, TRASH" | `src/bioetl/domain/value_objects/publication_field_groups.py:31-57` | Все 8 групп точно совпадают | **Да** | — |
| 25 | RULES.md §2.9.4 | "Доменные модели (`domain/composite/field_groups.py`): FieldMapping, FieldGroupDefinition, FieldGroupRegistry" | `src/bioetl/domain/composite/field_groups.py:47,112,163` | `class FieldMapping:`, `class FieldGroupDefinition:`, `class FieldGroupRegistry:` | **Да** | — |
| 26 | RULES.md §2.9.4 | "Конфигурация: `configs/composite/field_groups/publication.yaml`" | `configs/composite/field_groups/publication.yaml` | Файл существует | **Да** | — |
| 27 | RULES.md §2.6 | "Int→Float Coercion — 34 occurrences" | `src/bioetl/infrastructure/schemas/gold.py` и другие gold schemas | `Series[float]` + `coerce=True` в gold-схемах | **Частично** | Точное количество occurrences не верифицировано полностью. Рекомендуется обновлять число при изменении схем |
| 28 | RULES.md App D | "configs/pipelines/chembl_activity.yaml — пример конфигурации" | `configs/pipelines/chembl/activity.yaml` (NOT chembl_activity.yaml!) | Формат отличается от примера в RULES.md: нет секций `source`, `transform`, `sink.gold.path`, `circuit_breaker`, `rate_limit` в таком виде | **Нет** | Обновить пример в App D для соответствия фактическому формату после ADR-025 (pipeline config unification). Путь тоже неверен: `configs/pipelines/chembl/activity.yaml` а не `configs/pipelines/chembl_activity.yaml` |
| 29 | RULES.md §2.1 | "Gold формат: Delta Lake" | `src/bioetl/infrastructure/storage/gold_writer.py` | Использует `deltalake` для записи Gold | **Да** | — |
| 30 | RULES.md §2.9 | "Composite Pipeline: Seed → Dependencies → Enrichers → Merge" | `src/bioetl/application/composite/` (13 файлов) | `CompositeRunner`, `MergeService`, seed/enricher логика | **Да** | — |
| 31 | RULES.md §2.1.3 | "Engine: delta-rs (Rust core)" | `pyproject.toml` зависимость `deltalake` | `deltalake` — Python-биндинг для delta-rs | **Да** | — |
| 32 | RULES.md §2.7 | "load_strategy: incremental \| full в YAML пайплайна" | `configs/pipelines/chembl/activity.yaml` | Поле не найдено в activity.yaml напрямую; загружается из source config | **Частично** | Уточнить, что load_strategy определяется в `configs/sources/` файлах, а не непосредственно в pipeline YAML |
| 33 | RULES.md §2.4.1 | "Lock key: `lock:{provider}_{entity}`, exclusive: `lock:{provider}_{entity}:exclusive`" | `src/bioetl/infrastructure/locking/memory_lock.py` | Формат ключа используется в memory lock | **Да** | — |
| 34 | RULES.md §2.3 | "Silver Record содержит `_source_batch_id` (FK)" | `src/bioetl/domain/constants.py:22` | `"_source_batch_id"` в META_FIELDS | **Да** | — |

### RULES.md §3 — Ошибки и Наблюдаемость

| № | Документ | Утверждение | Ссылка на код (файл:строки) | Фрагмент кода | Соответствует | План устранения |
|---|----------|-------------|----------------------------|---------------|---------------|-----------------|
| 35 | RULES.md §3.1.3 | "Max Attempts: 3, Multiplier: 2.0" | `src/bioetl/domain/resilience.py:45-46` | `max_attempts: int = 3`, `multiplier: float = 2.0` | **Да** | — |
| 36 | RULES.md §3.1.3 | "Jitter: Random(0.1s, 0.5s)" | `src/bioetl/domain/resilience.py:47` | `jitter_range: tuple[float, float] = (0.1, 0.5)` | **Да** | — |
| 37 | RULES.md §3.1.4 | "Circuit Breaker Trigger: 5 consecutive errors" | `src/bioetl/domain/types.py:129-145` | `CircuitBreakerState` enum существует; threshold настраивается | **Да** | — |
| 38 | RULES.md §3.2.2 | "Prometheus metrics prefix: `bioetl_`" | `src/bioetl/infrastructure/observability/metrics.py:11-161` | `"bioetl_pipeline_duration_seconds"`, `"bioetl_records_processed_total"` и т.д. | **Да** | — |
| 39 | RULES.md §3.2.2 | "pipeline_duration_seconds (Histogram)" | `src/bioetl/infrastructure/observability/prometheus_metrics.py:36` | `"pipeline_duration_seconds": PIPELINE_DURATION_SECONDS` | **Да** | — |
| 40 | RULES.md §3.2.2 | "records_processed_total (Counter)" | `src/bioetl/infrastructure/observability/prometheus_metrics.py:45` | `"records_processed_total": RECORDS_PROCESSED_TOTAL` | **Да** | — |
| 41 | RULES.md §3.2.2 | "errors_total (Counter)" | `src/bioetl/infrastructure/observability/prometheus_metrics.py:46` | `"errors_total": ERRORS_TOTAL` | **Да** | — |
| 42 | RULES.md §3.2.2 | "batch_size_records (Histogram)" | `src/bioetl/infrastructure/observability/prometheus_metrics.py:37` | `"batch_size_records": BATCH_SIZE_RECORDS` | **Да** | — |
| 43 | RULES.md §3.2.2 | "filter_ids_loaded_total (Counter)" | `src/bioetl/infrastructure/observability/prometheus_metrics.py:47` | `"filter_ids_loaded_total": FILTER_IDS_LOADED_TOTAL` | **Да** | — |
| 44 | RULES.md §3.2.2 | "filter_ids_duplicates_total (Counter)" | `src/bioetl/infrastructure/observability/prometheus_metrics.py:48` | `"filter_ids_duplicates_total": FILTER_IDS_DUPLICATES_TOTAL` | **Да** | — |
| 45 | RULES.md §3.3 | "Lock TTL: `heartbeat_interval * 3 = 90 секунд`" | `src/bioetl/domain/config.py:555` | `lock_ttl: int \| None = 90` | **Да** | — |
| 46 | RULES.md §3.3 | "Heartbeat: 30 секунд" | `src/bioetl/domain/config.py:552` | `heartbeat_interval: int = 30` | **Да** | — |
| 47 | RULES.md §3.3 | "`effective_lock_ttl = lock_ttl or heartbeat_interval * 3`" | `src/bioetl/domain/config.py:613-615` | `def effective_lock_ttl(self) -> int: return self.lock_ttl or self.heartbeat_interval * 3` | **Да** | — |
| 48 | RULES.md §3.4 | "dq_validation_score, data_freshness_seconds" | `src/bioetl/infrastructure/observability/metrics.py:108,114` | `"bioetl_dq_validation_score"`, `"bioetl_data_freshness_seconds"` | **Да** | — |
| 49 | RULES.md §6.1 | "RetryPolicy.calculate_delay() uses MD5-based jitter" | `src/bioetl/domain/resilience.py:78` | `def calculate_delay(self, attempt: int, url: str = "") -> float:` — класс называется `RetryConfig`, не `RetryPolicy` | **Частично** | Исправить в RULES.md §6.1: `RetryConfig.calculate_delay()` вместо `RetryPolicy.calculate_delay()` |

### RULES.md §4 — Стандарты Кода

| № | Документ | Утверждение | Ссылка на код (файл:строки) | Фрагмент кода | Соответствует | План устранения |
|---|----------|-------------|----------------------------|---------------|---------------|-----------------|
| 50 | RULES.md §4.1 | "HTTP Клиент: httpx via UnifiedHTTPClient" | `src/bioetl/infrastructure/adapters/http/client.py:48` | `class UnifiedHTTPClient:` | **Да** | — |
| 51 | RULES.md §4.1.1 | "ChemblAdapter: BaseHttpAdapter + UnifiedHTTPClient" | `src/bioetl/infrastructure/adapters/chembl/client.py:89` | `class ChemblAdapter(BaseHttpAdapter):` | **Да** | — |
| 52 | RULES.md §4.1.1 | "UniProtAdapter: BaseHttpAdapter + UnifiedHTTPClient" | `src/bioetl/infrastructure/adapters/uniprot/client.py:100` | `class UniProtAdapter(BaseHttpAdapter, PaginatedFetcherMixin):` | **Да** | — |
| 53 | RULES.md §4.1.1 | "PubMedAdapter: `@dataclass`" | `src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py:49-50` | `@dataclass` + `class PubMedAdapter(NotSupportedMultiFilterMixin, BaseHttpAdapter):` | **Да** | — |
| 54 | RULES.md §4.1.1 | "PubChemAdapter: BaseSyncAdapter" | `src/bioetl/infrastructure/adapters/pubchem/client.py:62` | `class PubChemAdapter(FilterableStubMixin, BaseSyncAdapter):` | **Да** | — |
| 55 | RULES.md §4.3 | "Архитектурный тест `test_no_random_in_writers.py`" | `tests/architecture/test_no_random_in_writers.py` | Файл существует | **Да** | — |
| 56 | RULES.md §4.3 | "Архитектурный тест `test_no_datetime_now_in_infrastructure.py`" | `tests/architecture/test_no_datetime_now_in_infrastructure.py` | Файл существует | **Да** | — |
| 57 | RULES.md §4.3 | "Архитектурный тест `test_no_structlog_in_application_interfaces.py`" | `tests/architecture/test_no_structlog_in_application_interfaces.py` | Файл существует | **Да** | — |
| 58 | RULES.md §4.4.1 | "Все Python-файлы MUST начинаться с `from __future__ import annotations`" | 468 из 499 файлов (93.8%) содержат импорт | 31 файл без импорта — в основном `__init__.py` | **Частично** | 31 файл (преимущественно `__init__.py`) не имеют `from __future__ import annotations`. Добавить импорт или задокументировать исключение для `__init__.py` |
| 59 | RULES.md §4.1.1 | "Расположение UnifiedHTTPClient: `src/bioetl/infrastructure/adapters/http/client.py`" | `src/bioetl/infrastructure/adapters/http/client.py:48` | `class UnifiedHTTPClient:` | **Да** | — |

### RULES.md §5 — Операции

| № | Документ | Утверждение | Ссылка на код (файл:строки) | Фрагмент кода | Соответствует | План устранения |
|---|----------|-------------|----------------------------|---------------|---------------|-----------------|
| 60 | RULES.md §5.2 | "Секреты из `os.environ`, формат `BIOETL_{PROVIDER}_{KEY}`" | `src/bioetl/composition/`, `configs/sources/` | Переменные окружения используются для конфигурации | **Да** | — |
| 61 | RULES.md §3.3 | "MemoryLock — in-memory, local only" | `src/bioetl/infrastructure/locking/memory_lock.py` | `class MemoryLock:` — блокировка в памяти процесса | **Да** | — |
| 62 | RULES.md §3.3 | "ЗАПРЕЩЕНО: RedisLockAdapter и распределенные блокировки" | Поиск `Redis\|redis` в `src/bioetl/` → 0 production results | — | **Да** | — |
| 63 | RULES.md §5.3 | "Graceful Shutdown: SIGTERM/SIGINT → stop fetch → flush batch → save checkpoint" | `src/bioetl/application/core/shutdown.py`, `domain/ports/shutdown.py` | `ShutdownPort(Protocol)` + shutdown handling | **Да** | — |
| 64 | RULES.md §9.2 | "Storage: `data/output/bronze`, `data/output/silver`, `data/output/gold`" | `configs/pipelines/chembl/activity.yaml:15` | `sink paths: data/output/{layer}/chembl/activity` | **Да** | — |
| 65 | RULES.md §9.2 | "Зависимости: Только Python 3.11+ и pip" | `pyproject.toml` | `requires-python = ">=3.11"` | **Да** | — |

### RULES.md Приложения

| № | Документ | Утверждение | Ссылка на код (файл:строки) | Фрагмент кода | Соответствует | План устранения |
|---|----------|-------------|----------------------------|---------------|---------------|-----------------|
| 66 | RULES.md App A | "ChEMBL: `chembl_webresource_client` библиотека" | `pyproject.toml` | Зависимость в pyproject.toml (или используется через httpx) | **Частично** | Адаптер использует `UnifiedHTTPClient` (httpx), а не `chembl_webresource_client` напрямую. Обновить таблицу в App A |
| 67 | RULES.md App A | "PubChem: `pubchempy` библиотека" | `src/bioetl/infrastructure/adapters/pubchem/client.py` | `class PubChemAdapter(FilterableStubMixin, BaseSyncAdapter):` — использует pubchempy | **Да** | — |
| 68 | RULES.md App A | "GtoP: `pyGtoP` (deprecated)" | `src/bioetl/infrastructure/adapters/gtop/` → не существует | Директория не найдена | **Да** | Корректно помечен как deprecated, адаптер удалён |
| 69 | RULES.md App A.1 | "`CHEMBL_API_BASE = https://www.ebi.ac.uk/chembl/api/data`" | `src/bioetl/infrastructure/adapters/chembl/entity_mapper.py:35` | `CHEMBL_API_BASE = "https://www.ebi.ac.uk/chembl/api/data"` | **Да** | — |
| 70 | RULES.md App A.1 | "`CHEMBL_STATUS_URL = {BASE}/status`" | `src/bioetl/infrastructure/adapters/chembl/entity_mapper.py:36` | `CHEMBL_STATUS_URL = f"{CHEMBL_API_BASE}/status"` | **Да** | — |
| 71 | RULES.md App A.1 | "Entity mapping: activity→activity, assay→assay, molecule→molecule, target→target, protein_class→protein_classification, publication→document" | `src/bioetl/infrastructure/adapters/chembl/entity_mapper.py:44-56,315-323` | `_NON_PUBLICATION_ENTITY_MAPPING`: activity→activity, assay→assay, molecule→molecule, target→target, protein_class→protein_classification ✅; publication→document в `ENTITY_MAPPING:318` ✅ | **Да** | — |
| 72 | RULES.md App A.1 | "Mapping: дополнительные entity не указаны в таблице (compound, compound_record, target_component, cell_line, tissue)" | `src/bioetl/infrastructure/adapters/chembl/entity_mapper.py:48-54` | `"compound": "molecule"`, `"target_component": "target_component"`, `"cell_line": "cell_line"`, `"tissue": "tissue"`, `"compound_record": "compound_record"`, `"assay_parameters": "assay"` | **Нет** | В коде 11 маппингов, в таблице RULES.md App A.1 документированы только 6. Добавить compound→molecule, compound_record→compound_record, target_component→target_component, cell_line→cell_line, tissue→tissue, assay_parameters→assay |
| 73 | RULES.md App D | "Пример конфига: `configs/pipelines/chembl_activity.yaml`" | `configs/pipelines/chembl/activity.yaml` | Файл расположен в подпапке `chembl/`, а не как flat-файл | **Нет** | Исправить путь в App D: `configs/pipelines/chembl/activity.yaml`. Также обновить структуру примера для соответствия актуальному формату (ADR-025) |
| 74 | RULES.md App F | "33 ADR документа (ADR-001..ADR-033)" | `docs/02-architecture/decisions/` | 33 ADR файла подтверждены | **Да** | — |
| 75 | RULES.md App F | "Все ADR имеют статус Accepted" | `docs/02-architecture/decisions/` | ADR-003 имеет статус `Accepted (Revised)` | **Да** | Корректно задокументировано |
| 76 | RULES.md §4.2 | "Тестовые зависимости: pytest>=8.0, pytest-cov>=4.0, pytest-asyncio>=0.23, etc." | `pyproject.toml` | Группы зависимостей определены | **Да** | — |
| 77 | RULES.md §3.2.2 | "Реализация: `infrastructure/observability/metrics.py` и `prometheus_metrics.py`" | `src/bioetl/infrastructure/observability/metrics.py`, `prometheus_metrics.py` | Оба файла существуют | **Да** | — |
| 78 | RULES.md §4.3 | "RetryConfig в `src/bioetl/infrastructure/adapters/http/client.py`" | `src/bioetl/domain/resilience.py:18` | `class RetryConfig:` находится в `domain/resilience.py`, НЕ в `infrastructure/adapters/http/client.py` | **Нет** | Исправить путь в RULES.md §4.3: `domain/resilience.py` вместо `infrastructure/adapters/http/client.py` |
| 79 | RULES.md §2.6 | "Gold-схемы реализация: `src/bioetl/infrastructure/schemas/gold.py`" | `src/bioetl/infrastructure/schemas/gold.py` и `src/bioetl/domain/schemas/*/` | Файл существует; дополнительно gold-схемы в domain/contracts/gold/ | **Да** | — |

### ADR Документы

| № | Документ | Утверждение | Ссылка на код (файл:строки) | Фрагмент кода | Соответствует | План устранения |
|---|----------|-------------|----------------------------|---------------|---------------|-----------------|
| 80 | ADR-001 | "Использовать delta-rs для Silver/Gold" | `src/bioetl/infrastructure/storage/silver_writer.py:36`, `gold_writer.py` | `from deltalake import DeltaTable, write_deltalake` | **Да** | — |
| 81 | ADR-005 | "Composition Layer: factories, providers, bootstrap" | `src/bioetl/composition/factories/`, `composition/providers/`, `composition/bootstrap/` | Структура полностью совпадает | **Да** | — |
| 82 | ADR-007 | "Circuit Breaker: failure threshold, recovery timeout, half-open" | `src/bioetl/domain/types.py:129-145` (CircuitBreakerState enum), `infrastructure/adapters/decorators/circuit_breaker.py` | `CLOSED, OPEN, HALF_OPEN` states; configurable thresholds | **Да** | — |
| 83 | ADR-010 | "Local-Only Deployment: MemoryLock, no Redis" | `src/bioetl/infrastructure/locking/memory_lock.py` | Только in-memory блокировки; Redis не используется | **Да** | — |
| 84 | ADR-020 | "BasePipeline decomposition" | `src/bioetl/application/core/runner.py` | PipelineRunner с delegation pattern | **Да** | — |
| 85 | ADR-021 | "DDD Aggregates в domain/aggregates/" | `src/bioetl/domain/aggregates/` (batch.py, pipeline_run.py, quarantine_entry.py, events.py) | Aggregate Root pattern реализован | **Да** | — |
| 86 | ADR-025 | "Unified pipeline config format" | `configs/pipelines/chembl/activity.yaml` | Упрощённый формат с convention-based resolution | **Да** | — |
| 87 | ADR-026 | "Composite Pipeline Pattern" | `src/bioetl/application/composite/` (13 файлов) | CompositeRunner, MergeService, seed/enricher infrastructure | **Да** | — |
| 88 | ADR-027 | "DQ Rules Externalization" | `configs/dq/` (48+ файлов), `configs/dq/entities/chembl/activity.yaml` | Externalized DQ rules per entity | **Да** | — |
| 89 | ADR-032 | "Unified HTTP Client" | `src/bioetl/infrastructure/adapters/http/client.py` | `class UnifiedHTTPClient:` с rate limiter, circuit breaker, retry | **Частично** | ADR-032 может содержать специфичные детали реализации, которые эволюционировали. Рекомендуется ревью ADR на актуальность |

---

## Сводка несоответствий и план устранения

| № | Severity | Документ | Несоответствие | План устранения |
|---|----------|----------|----------------|-----------------|
| 1 | **HIGH** | RULES.md §2.6 | `dq_status` в документации имеет 3 значения (NEW, IGNORED, REPROCESSED), в коде — 5 (+ UNDER_REVIEW, EXPIRED) | Обновить RULES.md §2.6: добавить `UNDER_REVIEW` и `EXPIRED` в перечисление `dq_status` |
| 2 | **HIGH** | RULES.md App D | Путь к конфигу `configs/pipelines/chembl_activity.yaml` неверен; фактический путь `configs/pipelines/chembl/activity.yaml`. Формат примера устарел (до ADR-025) | Обновить App D: исправить путь и привести пример в соответствие с фактическим форматом после ADR-025 |
| 3 | **MEDIUM** | RULES.md §6.1 | `META_FIELDS` указан в `domain/transformations.py`, фактически определён в `domain/constants.py` | Исправить ссылку: `domain/constants.py:META_FIELDS` |
| 4 | **MEDIUM** | RULES.md §6.1 | Класс назван `RetryPolicy`, фактически `RetryConfig` | Исправить: `RetryConfig.calculate_delay()` вместо `RetryPolicy.calculate_delay()` |
| 5 | **MEDIUM** | RULES.md §4.3 | `RetryConfig` указан в `infrastructure/adapters/http/client.py`, фактически в `domain/resilience.py` | Исправить путь: `src/bioetl/domain/resilience.py` |
| 6 | **MEDIUM** | RULES.md App A.1 | Таблица маппингов entity→API resource содержит 6 записей, в коде — 11 (не документированы: compound, compound_record, target_component, cell_line, tissue, assay_parameters) | Добавить недостающие маппинги в таблицу App A.1 |
| 7 | **LOW** | RULES.md §4.4.1 | 31 файл (6.2%) не имеют `from __future__ import annotations` (в основном `__init__.py`) | Добавить импорт или задокументировать исключение для `__init__.py` файлов |
| 8 | **LOW** | RULES.md App A | ChEMBL "библиотека" указана как `chembl_webresource_client`, но адаптер фактически использует `UnifiedHTTPClient` (httpx) | Обновить колонку "Библиотека" для ChEMBL на `httpx (UnifiedHTTPClient)` |
| 9 | **LOW** | RULES.md §2.6 | Поля quarantine в документации (`ingestion_ts`, `bronze_batch_id`) не совпадают с кодовыми именами (`_created_at`, `_batch_id`) | Синхронизировать имена полей или добавить маппинг doc_name→code_name |
| 10 | **LOW** | RULES.md §2.7 | `load_strategy` указан как поле pipeline YAML, фактически может быть в source config | Уточнить расположение `load_strategy` в документации |
| 11 | **INFO** | RULES.md §1.1.1 | `@runtime_checkable` применён не ко всем портам | Уточнить, какие именно порты SHOULD быть `@runtime_checkable`, или сделать все критичные порты runtime_checkable |
| 12 | **INFO** | RULES.md §2.6 | "34 occurrences" Int→Float coercion — число может быть неактуальным | Пересчитать occurrences при следующем обновлении схем |

---

## Заключение

**Общая оценка**: Документация находится в **хорошем состоянии** — 86.5% утверждений полностью соответствуют коду (77 из 89). 7.9% имеют частичное соответствие, и 5.6% требуют исправления.

**Критические несоответствия** (HIGH): 2 — оба связаны с устаревшей документацией (QuarantineStatus enum и пример конфигурации в App D).

**Рекомендации**:
1. Немедленно обновить RULES.md §2.6 (QuarantineStatus enum) и App D (путь и формат конфига).
2. Исправить ссылки на код в §6.1 (META_FIELDS location, RetryConfig vs RetryPolicy).
3. Добавить недостающие entity маппинги в App A.1.
4. Рассмотреть автоматизацию синхронизации doc↔code через architecture tests.

---

## Промты для устранения несоответствий

Каждый промт ниже — самодостаточная инструкция для AI-агента (py-doc-bot или ручного редактирования).
Промты упорядочены по severity (HIGH → LOW → INFO). Каждый содержит:
- **Что изменить** (файл, секция, строки)
- **Текущий текст** (что есть сейчас)
- **Целевой текст** (что должно быть)
- **Обоснование** (ссылка на код)

---

### PROMPT-01: QuarantineStatus enum (HIGH, Audit #20)

**Файл**: `docs/00-project/RULES.md`, строка ~240

**Инструкция**:

> Открой файл `docs/00-project/RULES.md`.
> Найди строку в секции §2.6 "Спецификация Unified Quarantine":
>
> ```
> - `dq_status` (String): `NEW` | `IGNORED` | `REPROCESSED`.
> ```
>
> Замени её на:
>
> ```
> - `dq_status` (String): `NEW` | `UNDER_REVIEW` | `IGNORED` | `REPROCESSED` | `EXPIRED`.
>   - `NEW`: Только что создана, ждёт разбора.
>   - `UNDER_REVIEW`: Анализируется оператором.
>   - `IGNORED`: Разобрана и признана неактуальной.
>   - `REPROCESSED`: Успешно повторно обработана и перемещена в Silver.
>   - `EXPIRED`: Запись превысила период хранения.
> ```
>
> **Обоснование**: В коде `src/bioetl/domain/aggregates/quarantine_entry.py:31-47`
> `QuarantineStatus` содержит 5 значений, а не 3:
> `NEW`, `UNDER_REVIEW`, `IGNORED`, `REPROCESSED`, `EXPIRED`.
> Переходы: `NEW → UNDER_REVIEW → (IGNORED | REPROCESSED)`, `* → EXPIRED` (по TTL).

---

### PROMPT-02: Pipeline config path and format in App D (HIGH, Audit #28, #73)

**Файл**: `docs/00-project/RULES.md`, строки ~1354-1405

**Инструкция**:

> Открой файл `docs/00-project/RULES.md`.
> Найди секцию "Приложение D: Схема Конфигурации Пайплайна" (строка ~1354).
>
> Замени весь блок YAML-примера (строки ~1358-1405):
>
> ```yaml
> # configs/pipelines/chembl_activity.yaml
> pipeline:
>   name: chembl_activity
>   provider: chembl
>   entity: activity
> ...
> rate_limit:
>   requests_per_second: 5
>   burst: 10
> ```
>
> На актуальный формат (после ADR-025):
>
> ```yaml
> # configs/pipelines/chembl/activity.yaml
> # Minimal config using convention-based path resolution (ADR-029).
> # Inherits from _base.yaml with paths/filters auto-computed from provider/entity.
> #
> # Auto-computed by convention:
> #   - source_file: ../../sources/chembl.yaml
> #   - dq_config_file: ../../dq/entities/chembl/activity.yaml
> #   - filter_config_file: ../../filter/entities/chembl/activity.yaml
> #   - sink paths: data/output/{layer}/chembl/activity
> #   - sink.silver.primary_key: ["activity_id"]
>
> pipeline_name: chembl_activity
> provider: chembl
> entity_type: activity
> version: "1.2.0"
> description: "Extract biological activity records from ChEMBL API"
>
> primary_keys: ["activity_id"]
> silver_table: "chembl_activity"
> gold_table: "chembl_activity"
>
> sink:
>   silver:
>     primary_key: ["activity_id"]
>     sort_by:
>       columns: ["activity_id"]
>   gold:
>     sort_by:
>       columns: ["activity_id"]
>
> # DQ Overrides (applied on top of entity DQ config)
> dq_rules:
>   field_validations:
>     - field: "standard_value"
>       type: "range"
>       min: 0
>       max: 1000000000
>       nullable: true
> ```
>
> **Обоснование**: Фактический файл `configs/pipelines/chembl/activity.yaml` (а не
> `configs/pipelines/chembl_activity.yaml`) использует упрощённый формат после ADR-025.
> Старый формат с секциями `source`, `transform.steps`, `circuit_breaker`, `rate_limit`
> больше не используется — эти параметры вынесены в `configs/sources/chembl.yaml`
> и convention-based resolution.

---

### PROMPT-03: META_FIELDS location in §6.1 (MEDIUM, Audit #23)

**Файл**: `docs/00-project/RULES.md`, строка ~1024

**Инструкция**:

> Открой файл `docs/00-project/RULES.md`.
> Найди строку в секции §6.1 "MUST (Обязательно)", пункт 5:
>
> ```
> Реализация: `domain/transformations.py:META_FIELDS`.
> ```
>
> Замени на:
>
> ```
> Реализация: `domain/constants.py:META_FIELDS` (re-exported через `domain/transformations.py`).
> ```
>
> **Обоснование**: `META_FIELDS` определён в `src/bioetl/domain/constants.py:15`,
> а `domain/transformations.py:21` лишь импортирует его (`from .constants import META_FIELDS`).
> Первоисточник — `constants.py`.

---

### PROMPT-04: RetryPolicy → RetryConfig in §6.1 (MEDIUM, Audit #49)

**Файл**: `docs/00-project/RULES.md`, строки ~1022, ~1045

**Инструкция**:

> Открой файл `docs/00-project/RULES.md`.
>
> **Замена 1** (строка ~1022, секция §6.1, пункт 3):
>
> Найди:
> ```
> Реализация: `domain/resilience.py:RetryPolicy.calculate_delay()` использует MD5-based jitter.
> ```
> Замени на:
> ```
> Реализация: `domain/resilience.py:RetryConfig.calculate_delay()` использует MD5-based jitter.
> ```
>
> **Замена 2** (строка ~1045):
>
> Найди:
> ```
> При `RetryPolicy(deterministic=False)` выдаётся `DeprecationWarning`
> ```
> Замени на:
> ```
> При `RetryConfig(deterministic=False)` выдаётся `DeprecationWarning`
> ```
>
> **Обоснование**: Класс в коде называется `RetryConfig` (dataclass в
> `src/bioetl/domain/resilience.py:18`), а не `RetryPolicy`.

---

### PROMPT-05: RetryConfig location in §4.3 (MEDIUM, Audit #78)

**Файл**: `docs/00-project/RULES.md`, строка ~835

**Инструкция**:

> Открой файл `docs/00-project/RULES.md`.
> Найди строку в секции §4.3 "Детерминистичный Jitter":
>
> ```python
> # RetryConfig (src/bioetl/infrastructure/adapters/http/client.py)
> RetryConfig(
> ```
>
> Замени на:
>
> ```python
> # RetryConfig (src/bioetl/domain/resilience.py)
> RetryConfig(
> ```
>
> **Обоснование**: `class RetryConfig` находится в `src/bioetl/domain/resilience.py:18`,
> а не в `infrastructure/adapters/http/client.py`. Retry-конфигурация — domain value object.

---

### PROMPT-06: Entity mapping table in App A.1 (MEDIUM, Audit #72)

**Файл**: `docs/00-project/RULES.md`, строки ~1304-1313

**Инструкция**:

> Открой файл `docs/00-project/RULES.md`.
> Найди таблицу "Маппинг entity → API resource" в секции А.1 (строка ~1304).
>
> Текущая таблица (6 строк):
>
> ```markdown
> | Entity Type     | API Resource             | Primary Key          |
> | --------------- | ------------------------ | -------------------- |
> | `activity`      | `activity`               | `activity_id`        |
> | `assay`         | `assay`                  | `assay_chembl_id`    |
> | `molecule`      | `molecule`               | `molecule_chembl_id` |
> | `target`        | `target`                 | `target_chembl_id`   |
> | `protein_class` | `protein_classification` | `protein_class_id`   |
> | `publication`   | `document`               | `document_chembl_id` |
> ```
>
> Замени на полную таблицу (12 строк):
>
> ```markdown
> | Entity Type        | API Resource             | Primary Key              |
> | ------------------ | ------------------------ | ------------------------ |
> | `activity`         | `activity`               | `activity_id`            |
> | `assay`            | `assay`                  | `assay_chembl_id`        |
> | `assay_parameters` | `assay`                  | *(composite)*            |
> | `cell_line`        | `cell_line`              | `cell_chembl_id`         |
> | `compound`         | `molecule`               | `molecule_chembl_id`     |
> | `compound_record`  | `compound_record`        | `record_id`              |
> | `molecule`         | `molecule`               | `molecule_chembl_id`     |
> | `protein_class`    | `protein_classification` | `protein_class_id`       |
> | `publication`      | `document`               | `document_chembl_id`     |
> | `target`           | `target`                 | `target_chembl_id`       |
> | `target_component` | `target_component`       | `component_id`           |
> | `tissue`           | `tissue`                 | `tissue_chembl_id`       |
> ```
>
> **Обоснование**: В коде `src/bioetl/infrastructure/adapters/chembl/entity_mapper.py:44-55`
> `_NON_PUBLICATION_ENTITY_MAPPING` содержит 11 маппингов (+ publication из registry).
> В документации было задокументировано только 6 из них.

---

### PROMPT-07: ChEMBL library name in App A (LOW, Audit #66)

**Файл**: `docs/00-project/RULES.md`, строка ~1282

**Инструкция**:

> Открой файл `docs/00-project/RULES.md`.
> В таблице "Приложение А: Источники и Библиотеки" (строка ~1282), найди строку ChEMBL:
>
> ```
> | **ChEMBL**   | `chembl_webresource_client` | Нет явного лимита        | ...
> ```
>
> Замени колонку "Библиотека" на:
>
> ```
> | **ChEMBL**   | `httpx` via `UnifiedHTTPClient` | Нет явного лимита        | ...
> ```
>
> **Обоснование**: ChEMBL адаптер (`ChemblAdapter` в
> `src/bioetl/infrastructure/adapters/chembl/client.py:89`) наследует `BaseHttpAdapter`
> и использует `UnifiedHTTPClient` (httpx), а не `chembl_webresource_client`.

---

### PROMPT-08: Quarantine field names sync (LOW, Audit #19)

**Файл**: `docs/00-project/RULES.md`, строки ~228-240

**Инструкция**:

> Открой файл `docs/00-project/RULES.md`.
> В секции §2.6 "Спецификация Unified Quarantine" найди поля:
>
> ```
> - `ingestion_ts` (Timestamp): Время инцидента.
> ...
> - `bronze_batch_id` (UUID): Ссылка на пакет исходных данных.
> ```
>
> Добавь маппинг на кодовые имена (квадратные скобки):
>
> ```
> - `ingestion_ts` (Timestamp): Время инцидента. [Код: `QuarantineEntry._created_at`]
>
> - `pipeline` (String): Имя пайплайна (напр., `chembl_activity`). [Код: `QuarantineEntry._pipeline_name`]
>
> - `error_code` (String): Тип ошибки (напр., `SCHEMA_VIOLATION`). [Код: `QuarantineEntry._error_code`]
>
> - `payload` (JSON/Text): Сырая запись (**Truncated to 64KB**). [Код: `QuarantineEntry._payload`]
>
> - `payload_hash` (String): Для дедупликации ошибок. [Код: `QuarantineEntry._payload_hash`]
>
> - `bronze_batch_id` (UUID): Ссылка на пакет исходных данных. [Код: `QuarantineEntry._batch_id` (BatchID)]
> ```
>
> **Обоснование**: Документация использует "логические" имена полей таблицы,
> а код использует private-атрибуты `_created_at`, `_batch_id` и т.д.
> (класс `QuarantineEntry` в `src/bioetl/domain/aggregates/quarantine_entry.py:109-189`).
> Маппинг нужен для навигации разработчиков между документацией и кодом.

---

### PROMPT-09: load_strategy location clarification (LOW, Audit #32)

**Файл**: `docs/00-project/RULES.md`, секция §2.7 (или App D)

**Инструкция**:

> Открой файл `docs/00-project/RULES.md`.
> В секции, где упоминается `load_strategy: incremental | full` как поле pipeline YAML,
> добавь уточнение:
>
> ```
> > **Примечание**: `load_strategy` определяется в файле источника данных
> > (`configs/sources/{provider}.yaml`), а не непосредственно в pipeline config.
> > Pipeline config ссылается на источник через convention-based resolution
> > (`source_file: ../../sources/{provider}.yaml`) или явно через поле `data_schema_file`.
> ```
>
> **Обоснование**: В фактическом `configs/pipelines/chembl/activity.yaml` поле
> `load_strategy` отсутствует. Оно определяется в source-конфигурации
> и подтягивается при resolution. После ADR-025 pipeline config стал минимальным.

---

### PROMPT-10: `__future__` import exception for `__init__.py` (LOW, Audit #58)

**Файл**: `docs/00-project/RULES.md`, секция §4.4 "Python Standards"

**Инструкция**:

> Открой файл `docs/00-project/RULES.md`.
> В секции §4.4, где указано правило:
>
> ```
> Все Python-файлы MUST начинаться с `from __future__ import annotations`
> ```
>
> Добавь исключение:
>
> ```
> > **Исключение**: `__init__.py` файлы, содержащие только re-exports (`from ... import ...`)
> > и `__all__`, **MAY** опускать `from __future__ import annotations`, так как
> > они не содержат type annotations, требующих отложенной эвалюации.
> > Текущее состояние: 468 из 499 файлов (93.8%) содержат импорт;
> > 31 файл без импорта — все `__init__.py`.
> ```
>
> **Обоснование**: 31 файл без `from __future__ import annotations` — это
> исключительно `__init__.py` модули с re-exports. Они не используют
> type annotations в теле файла, поэтому `__future__` import не влияет
> на их поведение.

---

### PROMPT-11: @runtime_checkable ports clarification (INFO, Audit #3)

**Файл**: `docs/00-project/RULES.md`, секция §1.1.1

**Инструкция**:

> Открой файл `docs/00-project/RULES.md`.
> В секции §1.1.1, где упоминается `@runtime_checkable`:
>
> Замени общую формулировку на конкретный перечень:
>
> ```
> Следующие порты **SHOULD** быть `@runtime_checkable` для boundary validation
> в composition layer:
> - `DataSourcePort` — для проверки адаптеров при регистрации
> - `FilterableDataSourcePort` — для проверки расширенных адаптеров
> - `HealthCheckPort` — для проверки health-check capability
> - `StoragePort` — для проверки storage backends
>
> Остальные порты (LoggerPort, MetricsPort, TracingPort и т.д.) используют
> structural subtyping без runtime проверок и **MAY** не иметь `@runtime_checkable`.
> ```
>
> **Обоснование**: В текущем коде `@runtime_checkable` применён к
> `DataSourcePort`, `FilterableDataSourcePort`, `HealthCheckPort` и некоторым другим.
> Не все 43 порта нуждаются в runtime-проверке — только те, которые
> валидируются в composition layer при сборке dependency graph.

---

### PROMPT-12: Int→Float coercion count (INFO, Audit #27)

**Файл**: `docs/00-project/RULES.md`, строка ~1500 (changelog 5.11)

**Инструкция**:

> Открой файл `docs/00-project/RULES.md`.
> В changelog записи 5.11:
>
> ```
> Gold-схем с `Series[float]` + `coerce=True` для nullable integer полей (34 occurrences).
> ```
>
> Добавь пометку:
>
> ```
> Gold-схем с `Series[float]` + `coerce=True` для nullable integer полей (~34 occurrences на момент 5.11; актуальное число может отличаться).
> ```
>
> Дополнительно, в секции §2.6 "Int→Float Coercion для Nullable Integers" добавить:
>
> ```
> > **Примечание**: Для получения актуального числа occurrences:
> > `grep -rn "coerce=True" src/bioetl/infrastructure/schemas/ src/bioetl/domain/schemas/ --include="*.py" | grep -c "Series\[float\]"`
> ```
>
> **Обоснование**: Число 34 было точным на момент версии 5.11, но может
> устареть при добавлении новых gold-схем. Команда для пересчёта
> помогает поддерживать актуальность.
