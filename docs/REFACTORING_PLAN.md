# План Рефакторинга BioETL

*Версия: 5.7 | Дата: 2026-03-20*

> **⚠️ ПРОТОКОЛ ДВОЙНОЙ ВЕРИФИКАЦИИ (REQ-ARCH-040)**
>
> Все утверждения в этом документе проходят **двойную верификацию** согласно `RULES.md` §7:
> 1. **Первая проверка** — при обнаружении проблемы (размер, структура, делегирование)
> 2. **Вторая проверка** — при документировании (точные ссылки `файл:строка`, дата)
>
> Невыполнение протокола привело к ~50% ложных утверждений в предыдущих планах.

---

## ⚠️ ВЕРИФИЦИРОВАННЫЙ СТАТУС РЕАЛИЗАЦИИ

> **ВАЖНО**: Перед постановкой задач сверьтесь с этой секцией!
> Последняя верификация: 2026-03-20

### ✅ УЖЕ РЕАЛИЗОВАНО (не требует работы)

| Компонент | Файл | Доказательство |
|-----------|------|----------------|
| **PubMedAdapter.health_check()** | `pubmed_client.py:193-273` | Реализованы `health_check()`, `_probe_health()`, `_fallback_health_status()` |
| **VCR кассеты UniProt** | `tests/fixtures/vcr/` | 15+ кассет: `test_uniprot_protein_*.yaml`, `TestUniProtAdapterIntegration.*.yaml` |
| **VCR кассеты PubChem** | `tests/fixtures/vcr/` | `test_pubchem_compound_full_cycle.yaml` |
| **CLI тесты** | `tests/integration/interfaces/` | 7+ тестов: `test_cli_shutdown_integration.py`, `test_cli_run_*.py` и др. |
| **Обработка ошибок ChEMBL** | `client.py:223-267` | `_handle_error()` ВСЕГДА кидает исключения (CriticalError/ChemblApiError) |
| **UnifiedHTTPClient lifecycle** | `client.py:138-162` | Корректный async context manager (`__aenter__`/`__aexit__`) |
| **D1: Детерминистичный HTTP jitter** | `domain/resilience.py:45-84` | MD5-based jitter в `RetryPolicy.calculate_delay()`, 11 тестов в `test_http_client.py` |
| **PipelineRunner DI** | `runner.py:43-88`, `runner_services.py` | RunnerServices bundle инжектируется через конструктор; `build_runner_services()` создаёт сервисы в composition |
| **CLI → Entrypoints** | `cli.py:17-27`, `entrypoints.py` | CLI импортирует только из `composition/entrypoints.py`, не из `bootstrap_*` |
| **D2: Gold Writer детерминизм** | `gold_writer.py:286,359` | Фиксированный backoff `0.5 * (2**attempt) + 0.05` вместо `random.uniform()` |
| **D3: Arch test random** | `tests/architecture/test_no_random_in_writers.py` | 3 теста: import, uniform, choice |
| **M1: SilverWriteMode Enum** | `delta_writer.py:53-64` | `MERGE`, `APPEND`, `DELETE` + валидация в `_validate_write_mode()` |
| **M2: GoldWriteMode Enum** | `gold_writer.py:42-54` | `OVERWRITE`, `APPEND`, `SCD2` + валидация |
| **M4: Schema drift** | `delta_writer.py:303-349` | `_check_schema_drift()` с параметром `on_schema_mismatch: Literal["error", "evolve", "ignore"]` |
| **T1: PipelineContext.started_at** | `domain/context.py:102` | Поле `started_at` добавлено в `PipelineContext`, используется `datetime.now(UTC)` по умолчанию. |
| **T2: RecordProcessor time** | `record_processor.py:88` | Использует `self._context.started_at` для консистентного времени батча. |
| **T3: BronzeWriter time** | `bronze_writer.py:135` | Принимает `ingestion_ts` аргументом, не использует `datetime.now()`. |
| **T5: Arch test datetime.now** | `tests/architecture/test_no_datetime_now_in_infrastructure.py` | 2 теста + список разрешённых исключений |
| **O1: BaseTransformer tracing** | `base_transformer.py:125-187` | Tracing spans, duration histogram, error counters |
| **C1: Config Mapping Refactor** | `mappers/config_mapper.py` | Вынесен маппинг конфигурации в Composition Layer. |

### ❌ ЛОЖНЫЕ УТВЕРЖДЕНИЯ (НЕ ПОВТОРЯТЬ)

| Ложное утверждение | Почему ложно | Верификация |
|--------------------|--------------|-------------|
| "PubMedAdapter не реализует health_check" | Полностью реализован | `pubmed_client.py:193-273` |
| "Нет VCR для PubChem/UniProt integration" | Кассеты существуют | `tests/fixtures/vcr/` |
| "0 тестов interfaces/оркестрации" | 7+ интеграционных CLI тестов | `tests/integration/interfaces/` |
| "ChemblAdapter._fetch_page глушит ошибки" | `_handle_error()` всегда raises; `return [], False` — мёртвый код | `client.py:145-147, 261-267` |
| "UnifiedHTTPClient нарушает DI" | Создание в `__aenter__` — корректный async pattern | `client.py:138-152` |
| "D1: HTTP jitter не реализован" | MD5-based jitter в `RetryPolicy` с 2025-12-26 | `domain/resilience.py:45-84`, 11 тестов |
| "PipelineRunner — god object" | **173 строки**, делегирует через RunnerServices bundle | `runner.py:53,84-88` |
| "bootstrap_pipeline смешивает ответственности" | Правильно делегирует фабрикам через `factory.create_runner()` | `bootstrap.py:159-166` |
| "ChEMBL адаптер — размытые границы" | Когезивная ответственность: health-aware fetching | `client.py` ~350 строк, использует ErrorClassifier |
| "CLI содержит бизнес-логику подтверждений" | Подтверждения — **законная** ответственность interfaces слоя | По design |
| "DeltaWriter нарушает DI (создаёт WriteModePolicy)" | Опциональный параметр с default — валидный паттерн | `delta_writer.py:98` |
| "BaseTransformer без DQ-валидации" | By design: Template Method, DQ — ответственность конкретных трансформеров | `base_transformer.py` |
| "MedallionLifecycleService без политик" | Использует `MedallionPolicy.should_clear_*` | `medallion_lifecycle.py:71-112` |
| "BronzeWriter без observability" | Имеет структурированное логирование | `bronze_writer.py:197-205` |
| "CLI плотно связан с composition" | CLI использует `entrypoints.py` — это фасад, правильный паттерн | `cli.py:17-24`, `entrypoints.py:7-8` |
| "bootstrap_pipeline агрегирует слишком много" | ~100 строк, делегирует специализированным функциям | `bootstrap.py:68-167` |
| "PipelineRunner.run() концентрирует этапы" | Делегирует: `preflight_service`, `lifecycle_orchestrator`, `postrun_service` | `runner.py:126-142` |
| "D2: gold_writer.py:21,219,279 использует random" | random удалён, фиксированный backoff `0.5 * (2**attempt) + 0.05` | `gold_writer.py:286,359` |
| "GenericPipelineFactory — god object" | 397 строк, 6 методов, делегирует `BaseServicesFactory`, `ServicesBuilder`, `build_runner_services()` | `generic_factory.py:190,299,332` |
| "yaml_config_to_domain нарушает архитектуру" | Матрица импортов разрешает infrastructure → domain. PipelineConfig — value object | `config.py:185-228`, CLAUDE.md §2.1 |
| "PubChemAdapter без observability" | Использует `BaseSyncAdapter` с metrics, CircuitBreaker, health_check() | `sync_base.py:130-134`, `pubchem/client.py:255-313` |
| "ChEMBL adapter — монолит 517 строк" | **Делегирует** через `EntityMapper` (112 LOC), `ErrorClassifier`, `AdapterMetrics`, `BaseHttpAdapter`. Когезивная ответственность. | `client.py:30,76-84,90` |
| "GoldWriter — монолит 593 строки, требует декомпозиции на стратегии" | **Делегирует** CSV в `CsvExporter`, audit в `AuditPort`. Режимы OVERWRITE/APPEND/SCD2 когезивны. | `gold_writer.py:70-71,87-88,351-355` |
| "Нет автоматизации DQ/Medallion политик" | Реализовано: `MedallionPolicy` в `domain/medallion.py`, `DQConfig` в `domain/config.py:25-63`, `SilverWriteMode` / `GoldWriteMode` enums | `medallion.py`, `config.py:36-37` |
| "medallion_policy.py дублирует domain" | Это **shim для backward-compat** (19 строк re-export), НЕ дублирование | `application/core/medallion_policy.py` |
| "Domain использует Pydantic-модели" | Используются **dataclass Value Objects** (`@dataclass(frozen=True)`), не Pydantic | `domain/config.py:25,66,94,176` |
| "bootstrap_pipeline 140+ строк" | **113 строк** (`bootstrap.py:68-180`), делегирует через 4 функции: `register_all_providers()`, `register_all_pipelines()`, `bootstrap_observability()`, `factory.create_runner()` | `bootstrap.py:113-114,122,173` |
| "RecordProcessor совмещает метрики/карантин/запись" | **Делегирует** в `BatchMetricsRecorder`, `BatchTransformer`, `BatchWriter`, `QuarantineManager`. Сам класс — тонкий оркестратор. | `record_processor.py:59-85` |
| "PipelineRunner не выпускает метрики по стадиям" | Использует `PipelineObserver` через `RunnerServices.observer` как context manager | `runner.py:89,117` |
| "Нет валидации write mode через Enum" | **Реализовано**: `SilverWriteMode` enum (`delta_writer.py:53-64`), `GoldWriteMode` enum (`gold_writer.py:42-54`) с валидацией | M1, M2 в этом документе |
| "Архитектурные тесты не связаны с метриками" | 187 архитектурных тестов в `tests/architecture/`, `make arch-test` в CI | `Makefile:arch-test` |

### 🔴 ПОДТВЕРЖДЁННЫЕ ПРОБЛЕМЫ (актуальные задачи)

| Проблема | Файл:строки | Описание |
|----------|-------------|----------|
| **Mapping Logic in Infrastructure** | `src/bioetl/infrastructure/config.py:185` | `yaml_config_to_domain` function belongs in Composition layer (Mappers). |

---

## Обзор

Этот документ описывает план рефакторинга с фокусом на **устранение технического долга** в конфигурации и **улучшение архитектурной чистоты**.

### Приоритеты

| Уровень | Фаза | Цель |
|---------|------|------|
| 🟡 **Средний** | T6 | Обновление списка исключений в архитектурных тестах |
| 🟢 **Желательно** | O5 | Расширение метрик для Schema Drift |

### Порядок выполнения

```
┌─────────────────────────────────────────────────────────────────┐
│                     🟡 СРЕДНИЙ (Фаза 5)                         │
├─────────────────────────────────────────────────────────────────┤
│  T6: Arch Test Update ────────────────────────┐                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Фаза 5: Чистота Конфигурации и Маппинга 🔴

### Цель
Разделить ответственность загрузки настроек (Infrastructure) и преобразования их в доменные объекты (Composition).

### C1: Вынос маппинга конфигурации ✅ ВЫПОЛНЕНО

**Файл:** `src/bioetl/infrastructure/config.py` -> `src/bioetl/composition/mappers/config_mapper.py`

#### Проблема
`src/bioetl/infrastructure/config.py` содержит функцию `yaml_config_to_domain`, которая преобразует Pydantic-схему (Infrastructure) в Domain Value Object. Хотя это допустимо с точки зрения зависимостей (Infra -> Domain), семантически это задача Composition слоя (сборка приложения).

#### Решение
1. Создать `src/bioetl/composition/mappers/config_mapper.py`.
2. Перенести туда:
   - `yaml_config_to_domain`
   - `_extract_source_fields`
   - `_extract_write_modes`
   - `_build_gold_filters`
3. В `src/bioetl/infrastructure/config.py` оставить только загрузку YAML и Pydantic модели.
4. Экспортировать `yaml_config_to_domain` из нового места.

#### Критерии приёмки
- [x] `yaml_config_to_domain` отсутствует в `infrastructure/config.py` (кроме deprecated алиаса)
- [x] Все тесты проходят
- [x] Импорты в `bootstrap.py` обновлены

---

## Чек-лист перед началом

- [ ] `make lint && make test` проходят на текущем коде
- [ ] Git branch создан для работы
- [ ] Прочитаны `docs/RULES.md` и `.claude/PROJECT_CONTEXT.md`
- [ ] Понятны критерии приёмки каждой задачи

---

*Строй надёжно. Верифицируй перед предложением. Документируй с доказательствами.*
