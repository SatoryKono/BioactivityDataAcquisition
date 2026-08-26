______________________________________________________________________

Version: 6.1.11
Last verified: 2026-08-25
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team

______________________________________________________________________

# BioETL: Правила Проекта

## Введение (Quick Reference)

| Задача                                 | Раздел       | Инструмент                               |
| -------------------------------------- | ------------ | ---------------------------------------- |
| Создать новый пайплайн                 | App D        | YAML config                              |
| Добавить поле в схему                  | 2.2, App E   | Pydantic model                           |
| Ошибка в проде (Alert)                 | App C        | Runbook                                  |
| Удалить битые данные                   | 2.6          | `bioetl quarantine purge --pipeline ...` |
| Подготовить staging-like local profile | 5.6.1        | Environment isolation                    |
| Восстановление при аварии              | 5.5          | DR Runbook                               |
| Откат релиза                           | 7.2          | Rollback Strategy                        |
| Безопасность                           | 5.4          | Security Policy                          |
| Forensic retention для таблицы         | 2.1.1, App D | Config `forensic-retention`              |
| Backfill с эксклюзивной блокировкой    | 2.4          | Lock Mechanism                           |
| Deprecation поля                       | 7.1, App E   | Schema Evolution                         |

### Уровни Требований (Governance)

В документе используются ключевые слова согласно RFC 2119:

- **MUST** (Обязательно): Абсолютное требование. Нарушение рассматривается как дефект или блокер релиза.
- **SHOULD** (Рекомендуется): Сильная рекомендация. Отклонение требует явного обоснования (комментарий в PR).
- **MAY** (Опционально): Разрешено, на усмотрение разработчика.

## Глоссарий

- **Bronze/Silver/Gold**: уровни качества данных (Medallion Architecture).
- **Port**: интерфейс (Protocol) для инверсии зависимостей.
- **Adapter**: реализация Port для конкретного провайдера.
- **DAG**: Directed Acyclic Graph — модель зависимостей этапов пайплайна.
- **Quarantine**: Изолированное хранилище для данных, не прошедших валидацию (Dead Letter Queue).
- **Entity ID (Business Key)**: Идентификатор объекта в реальном мире (напр., `chembl-id`). Стабилен во времени.
- **Content Hash (Version ID)**: Идентификатор конкретного состояния объекта (`sha256`). Изменяется при обновлении атрибутов. Используется для дедупликации и SCD Type 2.
- **Time Travel**: Возможность запроса данных на определенный момент времени (Delta Lake Feature).
- **Circuit Breaker**: Паттерн защиты от каскадных сбоев, временно отключающий вызовы к сбойному сервису.
- **RPO (Recovery Point Objective)**: Максимально допустимый период потери данных при аварии.
- **RTO (Recovery Time Objective)**: Максимально допустимое время простоя системы.
- **SCD Type 2**: Slowly Changing Dimension — сохранение истории изменений записи (новые строки для изменений).
- **Heartbeat**: Периодическое обновление TTL блокировки для подтверждения liveness воркера.
- **Fencing Token**: Идентификатор владельца блокировки (`owner-id`) для предотвращения split-brain.
- **Game Day**: Плановые учения по проверке DR процедур.

## 1. Архитектура и Слои

**Философия**: "Прагматичная инженерия". Избегаем избыточной сложности (Over-engineering), архитектура должна ускорять вывод продукта на рынок (time-to-market).
**Паттерн**: Слоистая архитектура с инверсией зависимостей (Ports & Adapters).

### 1.1. Слои и Контракты

См. также [ADR-005](../02-architecture/decisions/ADR-005-composition-layer-separation.md) для Composition Layer, [ADR-020](../02-architecture/decisions/ADR-020-basepipeline-decomposition.md) для BasePipeline, [ADR-021](../02-architecture/decisions/ADR-021-ddd-aggregates-adoption.md) для DDD Aggregates, [ADR-026](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md) для Composite Pipeline и [ADR-045](../02-architecture/decisions/ADR-045-dq-contract-system.md) для DQ Contract System.

- **Infrastructure (Инфраструктура/Адаптеры)**: Реализация взаимодействия с внешним миром (HTTP, БД, файловая система).
- **Application (Приложение/Пайплайны)**: Оркестрация потоков данных. Определяет *когда* и *в каком порядке* вызываются порты.
- **Domain (Домен/Чистая логика)**: Чистые функции и контракты (Protocols). Никакого ввода-вывода (I/O). Pandera/Pandas imports are allowed only as schema-contract representation under `src/bioetl/domain/schemas/` and `src/bioetl/domain/contracts/`; runtime Pandera support MUST NOT use package import side effects, and the retained `apply_runtime_compatibility_patches` seam is a no-op after removal of the Pandera-specific compatibility shim. См. [ADR-048](../02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md).

### 1.1.1. Обеспечение Контрактов (Enforcement)

Интерфейсы определяются в пакете `domain/ports/` через `typing.Protocol`:

- **Design-time**: `mypy --strict` проверяет соответствие типов во время сборки. Основной механизм контроля.

- **Runtime Boundary**: Следующие критические порты **SHOULD** быть `@runtime-checkable` для boundary validation в composition layer:

  - `DataSourcePort` — для проверки адаптеров при регистрации
  - `FilterableDataSourcePort` — для проверки расширенных адаптеров
  - `HealthCheckPort` — для проверки health_check capability
  - `BronzeStoragePort`, `SilverStoragePort`, `GoldStoragePort`, `MergedStoragePort` — для проверки storage backends

  Остальные порты (`LoggerPort`, `MetricsPort`, `TracingPort` и т.д.) **MAY** не иметь `@runtime-checkable`.

  > **Текущее состояние (live inventory, 2026-08-05):** see generator
  > `python -m scripts.engineering.qa report-domain-ports-inventory`
  > → `reports/quality/domain-ports-inventory.{json,md}`.
  > Definitions: **port_protocol_classes** = Protocol classes named `*Port`
  > under `src/bioetl/domain/ports/**`; **port_module_files** = `*.py` excluding
  > `__init__.py`; **runtime_checkable_port_count** = those classes with
  > `@runtime_checkable`. Live snapshot at last inventory refresh:
  > **89** `port_protocol_classes`, **89** `runtime_checkable_port_count`
  > (100% of `*Port` Protocols), **73** `port_module_files`, **82** scanned
  > Python files including `__init__.py`. Raw `@runtime_checkable` decorator
  > tokens may exceed the port class count when non-`*Port` Protocols in the
  > same tree are also decorated. Minimum requirement remains the critical
  > ports listed above; remaining ports are decorated for uniformity.
  > Architecture gate: `tests/architecture/test_domain_ports_inventory_gate.py`.

- **Импорт**: Порты **MUST** импортироваться из фасада (`from bioetl.domain.ports import ...`), а не из внутренних модулей. Это правило относится и к runtime-oriented контрактам (`LoggerPort`, `RunnerFactoryPort`, `RunnablePort`, `RateLimiterPort`, `CircuitBreakerPort`): они по проектной политике остаются в `domain.ports` как чистые cross-layer abstractions, а не считаются infrastructure leakage. Проверяется архитектурным тестом.

- **Dependency direction**: `domain` **MUST NOT** зависеть от `application` или
  `infrastructure`; `application` и `interfaces` **MUST NOT** импортировать
  concrete infrastructure implementations. Infrastructure adapters **MUST**
  ограничиваться mapping, технической оркестрацией и delegation в domain /
  application services; бизнес-правила и state transitions внутри adapters
  запрещены.
- **Dependency injection**: зависимости **MUST** передаваться через
  конструкторы или явные параметры. Создание concrete dependencies и
  service-locator/global-registry lookup вне `composition/` **MUST NOT**
  использоваться. Factories и wiring принадлежат только composition root.
- **Naming**: cross-layer ports, application services, factories и adapters
  **MUST** использовать проектные суффиксы `*Port`, `*Service`, `*Factory` и
  `*Adapter`, если тип выполняет соответствующую роль.

- **Суффикс `*Protocol` вне `domain/ports/`**: Классы с суффиксом `*Protocol` **MAY** определяться в любом слое для layer-internal structural typing (mixin contracts, local interface shapes). Они **НЕ являются** нарушением ARCH-003. Разграничение: `*Port` — cross-layer контракт в `domain/ports/`, `*Protocol` — layer-internal контракт, не экспортируемый за пределы модуля/слоя.

```python
class DataSourcePort(Protocol):
    # Async generator, yields dict records per API page.
    def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]: ...
    async def health_check(self) -> HealthStatus: ...
```

Documentation anchor: `datasource_port_fetch_includes_offset` confirms that the
canonical `DataSourcePort.fetch(...)` contract includes the optional
`offset: int | None = None` parameter and that docs must stay aligned with the
live port signature.

### 1.1.2. Health Check Protocol

Все адаптеры **MUST** реализовывать асинхронный метод `health_check()` возвращающий `HealthStatus` enum:

```python
from bioetl.domain.types import HealthStatus


class MyAdapter:
    async def health_check(self) -> HealthStatus:
        """Проверка доступности внешнего сервиса.

        Returns:
            HealthStatus.HEALTHY — сервис доступен и отвечает < 5 сек
            HealthStatus.DEGRADED — медленный отклик (> 5 сек)
            HealthStatus.UNHEALTHY — ошибка или timeout
        """
```

**Контракт:**

- **MUST** быть `async def` (асинхронный)
- **MUST** возвращать `HealthStatus` enum, не `bool`
- **MUST** использовать lightweight probe (не тяжёлые запросы)
- **SHOULD** кэшировать результат на 30 секунд для избежания лишних вызовов
- **MUST NOT** выбрасывать исключения — ловить и возвращать `UNHEALTHY`

**Проверка:** Архитектурный тест `tests/architecture/` валидирует сигнатуры.

### 1.1.3. Tracking Technical Debt During File Changes

Любое изменение файлов **MUST** сопровождаться быстрой оценкой влияния на
параметры технического долга для затронутых путей.

- При изменениях в `src/`, `tests/`, `configs/` или `docs/` исполнитель
  **MUST** определить, делает ли изменение debt-сигналы лучше, хуже или
  оставляет их без изменений.
- Debt-сигналы **MUST** интерпретироваться в двух разных плоскостях:
  - **Exemption debt**: enforceable debt из
    `configs/quality/architecture_metric_exemptions.yaml`, управляемый через
    `configs/quality/debt_scorecard.yaml`.
  - **Hotspot inventory**: raw evidence по size/LOC/duplication/fan-in из
    `scripts/engineering/README.md` и related reports. Этот сигнал **MUST NOT**
    трактоваться как enforceable debt, пока он явно не закреплён в scorecard
    или named hotspot budget.
- Для затронутого кода **MUST** быть проверены релевантные scorecard
  registries: `file_size_limits`, `function_complexity`, `function_length`,
  `class_size`, `class_method_count`, `god_object`, `domain_complexity`.
- Если изменённый путь попадает в `hotspot_budgets` или
  `hotspot_family_ratchets` из `configs/quality/debt_scorecard.yaml`,
  исполнитель **SHOULD** дополнительно отслеживать family-level параметры,
  включая `duplication_clusters`, `files_ge_250_loc`,
  `max_internal_fan_in` и другие bounded-growth поля для этой family.
- Изменения **MUST NOT** неявно создавать новый debt exemption. Если exemption
  действительно необходим, его **MUST** оформить в
  `configs/quality/architecture_metric_exemptions.yaml` со всеми required
  metadata: `value`, `owner`, `reason`, `classification`, `linked_rf`,
  `expires_on`, `removal_step`, а scorecard sync **MUST** остаться валидным.
- Если правка затрагивает quality gates, исполнитель **SHOULD** проверить, что
  coarse budgets `ruff_error_count`, `mypy_error_count` и
  `architecture_skip_count` не ухудшились относительно текущего scorecard.
- Завершение задачи **SHOULD** явно фиксировать debt outcome для затронутых
  файлов: `improved`, `unchanged` или `worsened`, с краткой пометкой, какие
  параметры были проверены.

### 1.1.4. Критические Ограничения на Technical Debt

- **УВЕЛИЧИВАТЬ бюджеты тех. долга ЗАПРЕЩЕНО** — технический долг может только
  уменьшаться или оставаться неизменным. Любое изменение, которое увеличивает
  бюджеты тех. долга (scorecard budgets, exemption limits, hotspot thresholds),
  **MUST** быть отклонено. Изменение самого запрета является отдельной
  governance-программой с обновлением higher-precedence runtime contract и
  нормативного стека; оно не может использоваться как разрешение увеличить
  бюджет в обычной engineering task.

Рекомендуемые проверки:

```bash
uv run python -m scripts.engineering.qa check-exemptions
uv run python -m pytest tests/architecture/test_quality_debt_scorecard.py -q
uv run python -m pytest tests/architecture/test_regression_metrics.py -q
```

## 2. Поток Данных и Стратегия Medallion

Пайплайны реализуются как направленные ациклические графы (**DAG**).

См. [ADR-002](../02-architecture/decisions/ADR-002-medallion-architecture.md).

### 2.1. Архитектура Medallion

| Уровень            | Формат           | Валидация                  | Хранение (Retention)                          | Идемпотентность                                                                                                        |
| ------------------ | ---------------- | -------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Bronze** (Сырые) | **JSONL + zstd** | Мин./Нет                   | 90 дней hot -> Archive (local archive policy) | Path: `bronze/{provider}/{entity}/{date}/`. Append-only.                                                               |
| **Silver** (Норм.) | **Delta Lake**   | Мягкая (учет дрейфа схемы) | Постоянно                                     | **Merge/Upsert**. Raw Parquet в Silver **MUST NOT** использоваться. Обязателен ACID. Time Travel — для Ops, не для DR. |
| **Gold** (Витрины) | Delta Lake       | Строгая (`strict=True`)    | Постоянно                                     | Версионированные снимки (SCD Type 2) или партиционирование по дате.                                                    |

Для всех write paths Silver и Gold действуют дополнительные инварианты:

- Silver и Gold **MUST** записываться как Delta Lake tables; raw Parquet для
  этих medallion layers **MUST NOT** использоваться.
- Точный итоговый DataFrame, передаваемый writer-у, **MUST** пройти Pandera
  validation после последней трансформации и непосредственно перед write.
  Любая трансформация после validation требует повторной validation.
- Silver validation **MUST** проверять schema, nullability, types и применимые
  DQ/business constraints. Невалидные строки должны остановить write или быть
  явно перенаправлены в quarantine; результат validation нельзя игнорировать.
- Gold validation **MUST** быть fail-closed и использовать strict schema
  (`strict=True`, с явной coercion policy). `SchemaError` / `SchemaErrors`
  **MUST NOT** перехватываться с последующим выполнением write.
- Merge/upsert **MUST** сопоставлять записи по declared primary key или
  документированному стабильному business key. Mutable/non-unique fields и
  timestamps **MUST NOT** входить в match predicate; повтор того же input не
  должен создавать дополнительные logical rows.

#### 2.1.1. Silver Write Modes (Режимы Записи)

Режимы записи для Silver слоя строго типизированы (`SilverWriteMode` enum):

> **Canonical owner note:** эта секция является нормативным owner-doc для
> Medallion write-mode policy. `glossary.md` и
> `03-guides/pipeline-configuration.md` должны ссылаться на эти определения и
> не должны вводить альтернативные enum-наборы. Runtime source of truth:
> `src/bioetl/domain/medallion.py`.

- **MERGE**: Upsert по первичным ключам. Стратегия по умолчанию для incremental updates.
- **APPEND**: Вставка новых записей без проверки дубликатов.
- **DELETE**: Полная перезапись таблицы (удаление и вставка).

**Валидация**:

- Попытка использовать режим `OVERWRITE` (не `DELETE`) вызовет ошибку.
- Нарушение инвариантов Medallion (например, Append для данных требующих идемпотентности) логируется как `PolicyViolation`.

#### 2.1.2. Gold Write Modes (Режимы Записи)

Режимы записи для Gold слоя строго типизированы (`GoldWriteMode` enum):

- **OVERWRITE**: Полная перезапись витрины. Допустимо для полностью пересчитываемых производных таблиц.
- **APPEND**: Добавление новых партиций/батчей (фактовые потоки без требований к ретро-исправлению).
- **SCD2**: Slowly Changing Dimensions Type 2 (историчность).

Если для Silver/Gold явно задаётся `mode: append`, pipeline config **MUST**
также явно задавать `idempotency_contract`. Допустимые machine-readable
значения:

- `merge_upsert`
- `scd2`
- `overwrite_rebuild`
- `append_log`
- `partition_append_with_stable_partition_key`
- `occurrence_only`
- `disallowed`

Append без `idempotency_contract` считается invalid config. Для semantic
Silver/Gold outputs append допускается только с явным append-safe contract и
не считается strict replay-safe по умолчанию.

**Классификация сущностей для историчности (MUST):**

- **Reference dictionaries** -> `mode: scd2`
- **Slowly evolving records** -> `mode: scd2`
- **Publication metadata** -> `mode: scd2`
- **Recomputed aggregates** -> `mode: overwrite`

Для SCD2-кандидатов Gold mode **MUST** быть задан явно в каждом `configs/entities/{provider}/{entity}.yaml` (секция `pipeline:`).
Не допускается опора на implicit baseline из `-base.yaml`.

`scd_config` для `mode: scd2` **MUST** содержать все обязательные поля:

```yaml
sink:
  gold:
    mode: scd2
    scd_config:
      valid_from_col: _valid_from
      valid_to_col: _valid_to
      current_flag_col: _is_current
      version_col: _version
```

**Migration matrix (обязательно для планирования изменений):**

| Entity                                                                                                                                | Current Mode         | Recommended Mode     | Breaking | Migration                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | -------------------- | -------- | ----------------------------------------------------------------------------------------------- |
| publication (chembl/pubmed/crossref/openalex/semanticscholar)                                                                         | implicit `overwrite` | `scd2`               | Yes      | Bootstrap snapshot, затем включить `mode: scd2` + `scd_config` и backfill интервалов валидности |
| reference dictionaries (chembl: assay, assay-parameters, cell-line, tissue, protein-class, subcellular-fraction)                      | implicit `overwrite` | `scd2`               | Yes      | Единоразовый rebuild + переход на versioned upsert                                              |
| slowly evolving records (chembl: target, target-component, molecule, compound-record; uniprot: protein, idmapping; pubchem: compound) | implicit `overwrite` | `scd2`               | Yes      | Инициализировать current как version=1, дальнейшие изменения писать как новые версии            |
| high-volume facts (chembl: activity)                                                                                                  | implicit `overwrite` | `merge`              | No       | Явно зафиксировать merge/upsert в pipeline YAML со стабильными business keys                    |
| recomputed derived outputs (chembl: publication-similarity, publication-term)                                                         | implicit `overwrite` | explicit `overwrite` | No       | Оставить overwrite, но задать явно в pipeline YAML                                              |

### 2.1.3. Инфраструктура Delta Lake

См. [ADR-001](../02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md).

- **Engine**: Использовать `delta-rs` (Rust core) для Python-воркеров для производительности.
- **Protocol**: Writer Version 2 (поддержка Column Mapping), Reader Version 1.
- **Maintenance**: Обязательный запуск `VACUUM` с `retention-period=7 days` еженедельно для очистки старых файлов и уменьшения стоимости хранения. **VACUUM MUST** запускаться еженедельно.
- **Forensic Retention**: По умолчанию 7 дней. Для таблиц класса critical (Core Data) допустимо увеличение до 30 дней через конфиг (`forensic-retention: true`), если позволяет бюджет.

### 2.2. Политика Дрейфа Схемы (Schema Drift)

| Уровень  | Условие                                  |
| -------- | ---------------------------------------- |
| Info     | Новые поля (любое количество)            |
| Critical | Пропавшее обязательное поле / смена типа |

- **Drift SLA**: Для событий Critical (дрейф схемы) назначается Owner. SLA на реакцию — 48 часов. Нерешенный дрейф блокирует следующий релиз.

### 2.3. Data Lineage (Происхождение Данных)

Оптимизированная схема lineage:

- **Silver / Gold Persisted Rows**: Не содержат occurrence-scoped provenance (`_run_id`, `_run_type`, `_source_batch_id`, `_ingestion_ts`).
- **Lineage Metadata**: Sidecar-файлы `*_metadata.yaml` и модели metadata хранят canonical Bronze lineage anchor (`_source_batch_id` или formal Bronze artifact ref), маппинг на Bronze artifacts, версию трансформации и параметры запуска.
  Полные пути к файлам в каждой строке данных хранить запрещено (избыточность).

### 2.4. Политика Backfill / Replay

- **Metadata / Control Plane**: Обязательные runtime anchors `_run_id` (UUID), `_run_type` (`incremental` | `backfill` | `rebuild`) публикуются через manifest / ledger / sidecar / audit artifacts, а не через persisted Silver/Gold rows.
- **Merge Semantics**: Persisted Silver/Gold row updates остаются `content_hash`-based и не используют `_run_type` в physical Delta merge predicate. Семантика `backfill` / `rebuild` обеспечивается execution-level cleanup и exclusive locks, а не row-level precedence в persisted rows.
- **Concurrency Constraint**: В один момент времени для одной сущности допустим только один процесс записи типа `rebuild` или `backfill`. Параллельный запуск запрещен (Lock должен это гарантировать).

#### 2.4.1. Backfill Lock Enforcement

Lock key включает тип запуска:

- `incremental`: `lock:{provider}-{entity}`
- `backfill`/`rebuild`: `lock:{provider}-{entity}:exclusive`

При наличии активного `incremental` lock попытка взять `:exclusive`:

- **Default**: Fail immediately (configurable).
- **Wait mode**: `--wait-for-lock TIMEOUT-SEC`. Timeout по умолчанию: 300 секунд.

#### 2.4.2. Medallion Clear Policy by Run Type

См. [ADR-012](../02-architecture/decisions/ADR-012-storage-clear-contract-and-run-id.md) и [ADR-013](../02-architecture/decisions/ADR-013-async-storage-cleanup.md).

| Run Type      | Clear Silver | Clear Gold  | Rationale                       |
| ------------- | ------------ | ----------- | ------------------------------- |
| `REBUILD`     | ✅ MUST      | ✅ MUST     | Полная перестройка данных       |
| `BACKFILL`    | ✅ MUST      | ✅ MUST     | Историческая загрузка заново    |
| `INCREMENTAL` | ❌ MUST NOT  | ❌ MUST NOT | Merge/Upsert, сохранение данных |

**Инвариант Medallion**: Incremental runs **MUST NOT** вызывать `clear-silver()` или `clear-gold()`. Нарушение этого правила приводит к потере данных.

#### 2.4.3. Pipeline ID Governance

Публичный pipeline ID для CLI, config, metrics, locks и published run artifacts
остается в формате `<provider>_<entity>`.

- **Canonical runtime policy**: текущий repo-wide runtime/config corpus использует
  `chembl_activity`, `pubchem_compound`, `uniprot_protein` и аналогичные
  underscore IDs как стабильные внешние идентификаторы.
- **Conflict guardrail**: legacy/external wording `<entity>_<source>` не
  считается санкционированной альтернативой для текущего runtime. Массовое
  переименование, ввод третьего варианта или смешивание схем именования
  запрещены без отдельного ADR и migration plan.
- **Controlled resolution scope**: любой approved rename **MUST** покрывать
  configs, CLI, metrics, locks, paths, docs и migration aliases в одном
  change set.

**Реализация:**

```python
# В MedallionLifecycleService.clear()
if self.runtime.run_type in (RunType.REBUILD, RunType.BACKFILL):
    await self.services.storage.clear_silver(self.config.silver_table)
    if self.config.gold_table:
        await self.services.storage.clear_gold(self.config.gold_table)
```

**Проверка:** Интеграционный тест `tests/integration/test_runner_lifecycle.py::test-incremental-skips-clear`.

### 2.5. Стратегия Партиционирования

| Уровень    | Стратегия партиционирования                   | Пример                                         |
| ---------- | --------------------------------------------- | ---------------------------------------------- |
| **Bronze** | По `ingestion-date` (YYYY-MM-DD)              | `bronze/chembl/activity/2025-05-20/`           |
| **Silver** | По `source-date` или `entity-type`            | `silver/chembl/activity/year=2025/month=05/`   |
| **Gold**   | По use-case (часто по `target-id` или `date`) | `gold/activity-by-target/target-id=CHEMBL123/` |

- **Soft Limits**: Warning при >10,000 партиций или >100 файлов в партиции.
- **Hard Limits**: 50,000 партиций -> Pipeline Fail. Запрещены ключи партиционирования: UUID, Hash, Free-text (высокая кардинальность убивает Delta Log).
- **Z-ORDER**: Рекомендуется для полей с высокой кардинальностью в Gold слое (вместо глубокого партиционирования).

### 2.6. Политика NULL и Пропущенных Значений

| Состояние                        | Действие                       | Куда попадает                             |
| -------------------------------- | ------------------------------ | ----------------------------------------- |
| Значение отсутствует в источнике | Замена на NULL                 | Таблица Silver                            |
| Некритичная ошибка DQ (warning)  | Замена на NULL                 | Таблица Silver (с флагом `-dq-warn=true`) |
| Критичная ошибка DQ (error)      | Исключение из основного потока | **Таблица Quarantine (Unified)**          |

#### Спецификация Unified Quarantine

Единая таблица `common.quarantine` для всех сущностей.

- `ingestion-ts` (Timestamp): Время инцидента. \[Код: `QuarantineEntry.-created-at`\]

- `pipeline` (String): Имя пайплайна (напр., `chembl_activity`). \[Код: `QuarantineEntry.-pipeline-name`\]

- `error-code` (String): Тип ошибки (напр., `SCHEMA-VIOLATION`). \[Код: `QuarantineEntry.-error-code`\]

- `payload` (JSON/Text): Сырая запись (**Truncated to 64KB**). \[Код: `QuarantineEntry.-payload`\]

- `payload-hash` (String): Для дедупликации ошибок. \[Код: `QuarantineEntry.-payload-hash`\]

- `bronze-batch-id` (UUID): Ссылка на пакет исходных данных. \[Код: `QuarantineEntry.-batch-id` (BatchID)\]

- `dq-status` (String): `NEW` | `UNDER-REVIEW` | `IGNORED` | `REPROCESSED` | `EXPIRED`.

  - `NEW`: Только что создана, ждёт разбора.
  - `UNDER-REVIEW`: Анализируется оператором.
  - `IGNORED`: Разобрана и признана неактуальной.
  - `REPROCESSED`: Успешно повторно обработана и перемещена в Silver.
  - `EXPIRED`: Запись превысила период хранения.

- **Запрещено**: Sentinel values (-1, "N/A", 9999) **MUST NOT** использоваться.

- **Pandera**: Поля, допускающие NULL, явно маркируются `nullable=True`.

#### Int→Float Coercion для Nullable Integers

**Контекст**: Gold-схемы используют `Series[float]` с `coerce=True` для полей, которые в Silver-схемах определены как `pa.int64()`. Это **осознанное архитектурное решение**, а не ошибка.

**Причина**: Pandas/Polars исторически не поддерживали nullable integers без специального типа `Int64` (с заглавной I). Float — единственный способ представить `int + NULL` без потери данных для больших значений. `NaN` используется для отсутствующих значений.

<!-- Updated: was ~34→~88→~104 (audit 2026-02-27) -->

**Затронутые поля (~104 occurrences)**:

> **Примечание**: Для получения актуального числа occurrences:
> `grep -rn "coerce=True" src/bioetl/infrastructure/schemas/ src/bioetl/domain/schemas/ --include="*.py" | grep -c "Series\[float\]"`

| Сущность        | Поля                                                                                   |
| --------------- | -------------------------------------------------------------------------------------- |
| ChEMBL Activity | `record-id`, `src-id`, `standard-flag`, `potential-duplicate`, `toid`, `document-year` |
| ChEMBL Molecule | `first-approval`, `black-box-warning`, `max-phase`, `chirality`, `usan-year` и др.     |
| ChEMBL Assay    | `src-id`, `assay-taxonomy-id`, `confidence-score`, `dap-id`                            |
| ChEMBL Target   | `taxonomy-id`                                                                          |
| UniProt Protein | `organism-id`, `sequence-length`                                                       |
| Publications    | `year`, `publication-year`                                                             |

**Слои типизации**:

| Слой   | Тип                                     | Пример                   |
| ------ | --------------------------------------- | ------------------------ |
| Domain | `Series[int]` или `Series[int] \| None` | Строгая типизация        |
| Silver | `pa.int64()`                            | Реальный формат хранения |
| Gold   | `Series[float]` + `coerce=True`         | Nullable через NaN       |

**Требования к downstream-потребителям**:

- **SHOULD** обрабатывать `NaN` как отсутствующее значение
- **MAY** конвертировать `float → int` после проверки на `NaN` (если бизнес-логика требует)
- **MUST NOT** предполагать, что все значения — целые числа

**Реализация**: `src/bioetl/domain/contracts/gold/` (`chembl.py`, `composite.py`, `publications.py`, `pubchem.py`, `uniprot.py`)

#### Schema Typing Policy (JSON-like поля)

Для Silver и Gold слоёв JSON-подобные поля (массивы/объекты) **MUST** храниться как **canonical JSON string** (`UTF-8`, `sort-keys=True`, compact separators).

**MUST:**

- Pandera-контракты типизируют JSON-like поля как `Series[str]` (не `Series[object]`).
- Трансформеры сериализуют list/dict через каноническую сериализацию до записи в Silver/Gold.
- **Serialization**: canonical JSON helper with stable key ordering, compact separators, and ASCII-safe deterministic output (`serialize_to_canonical_json(...)` / `serialize_json_canonical(...)`).
- **Null semantics**: отсутствие данных хранится как `NULL` (`None`), а не `'[]'`, `'{}'` или sentinel.
- Пустые коллекции нормализуются в `NULL` (`None`), а не `[]`/`{}` строками.

**MUST NOT:**

- Использовать `Series[object]` для JSON-like полей в Silver/Gold контрактах.
- Смешивать нативные list/dict и JSON string для одного и того же поля между пайплайнами.
- Вводить новые поля как native list/object.

**Совместимость и миграция:**

- **MAY (временно)**: legacy native list/object в существующих таблицах до завершения миграции по [ADR-035](../02-architecture/decisions/ADR-035-json-field-typing-policy.md).
- Для breaking-изменений типов применяется окно совместимости 14 дней с dual-read (старый + новый формат).
- После окна совместимости выполняется Delta backfill и удаление legacy-формата из контрактов.
- Полный реестр JSON-like полей и расхождений типов: [ADR-035](../02-architecture/decisions/ADR-035-json-field-typing-policy.md) (Appendix A).
- Согласование strict validation: [ADR-018](../02-architecture/decisions/ADR-018-gold-strict-validation.md).

#### Жизненный цикл Карантина

- **Retention**: 30 дней. Старые записи удаляются автоматически (local archive policy).
- **Triage**: Еженедельный пересмотр (Triage) ошибок аналитиками. Если ошибка системная — правим адаптер, если разовая — игнорируем.
- **Source of Truth**: Карантин — это инструмент триажа, а не источник истины. Данные в карантине считаются "отсутствующими" в аналитическом слое.
- **Linkage**: Обязательна ссылка на Bronze-файл (`bronze-file-uri` или `batch-id`) для возможности перепарсить исходник, если payload был обрезан.

#### Операции с карантином

Канонический интерфейс управления карантином — подкоманды `bioetl quarantine`:

- `bioetl quarantine inspect --pipeline ...`: Выгрузка сэмпла ошибок для анализа.
- `bioetl quarantine replay --pipeline ...`: Повторная отправка исправленных записей в пайплайн.
- `bioetl quarantine purge --pipeline ...`: Принудительная очистка карантина.

### 2.7. Стратегия Загрузки (Load Strategy)

| Критерий                                  | `loading_strategy: full_scan_only` |
| ----------------------------------------- | ---------------------------------- |
| Источник с нестабильной offset-пагинацией | ✅ Обязательно                     |
| Checkpoint resume                         | ❌ Запрещён                        |
| Дедупликация                              | ✅ Через content-hash в Silver     |
| Типичные сущности                         | Publication family, derived sets   |

- **Watermark**: Механизм удалён согласно [ADR-011](../02-architecture/decisions/ADR-011-remove-watermark-mechanism.md).
- **Конфигурация**: `loading_strategy: full_scan_only` задаётся в `configs/entities/{provider}/{entity}.yaml` секция `pipeline:` (см. [ADR-031](../02-architecture/decisions/ADR-031-loading-strategy-formalization.md)).
- **Default behavior**: При `loading_strategy: null` разрешён checkpoint-based resume (стандартный incremental-поток).
- **Checkpoint policy**: Для `full_scan_only` возобновление через checkpoint **MUST NOT** использоваться.

### 2.8. DQ Contract System

Система контрактов качества данных обеспечивает сквозную валидацию, аудит и управляемость качеством данных. См. [ADR-045](../02-architecture/decisions/ADR-045-dq-contract-system.md).

#### 2.8.1. Типы контрактов

- **SCHEMA**: Структурная runtime-валидация DataFrame contracts через
  Pandera. JSON/YAML contract artifacts являются derived projection/catalog
  surfaces, если конкретный runtime path не документирует другое.
- **CONTENT**: Бизнес-правила качества (диапазоны, паттерны).
- **CONSISTENCY**: Проверка согласованности между разными источниками.
- **PROVENANCE**: Отслеживание происхождения и цепочки изменений (Git commit, config hash).

#### 2.8.2. Обработка нарушений (Disposition)

| Режим          | Описание                                                                     |
| -------------- | ---------------------------------------------------------------------------- |
| **FAIL**       | Остановка пайплайна при первом нарушении. Используется для критических схем. |
| **WARN**       | Логирование предупреждения, данные проходят дальше.                          |
| **QUARANTINE** | Отправка битых записей в Quarantine, продолжение обработки валидных данных.  |

#### 2.8.3. Разрешение политик (Policy Resolution)

При поиске активного контракта используется приоритетность:

1. Точное совпадение (`contract_id` + `version`).
1. Последняя (Latest) версия контракта.
1. Контракт по умолчанию для типа сущности.
1. Глобальная политика (Fallback).

### 2.9. Генерация ID Сущности (Entity ID)

См. [ADR-023](../02-architecture/decisions/ADR-023-entity-type-patterns.md) и [ADR-024](../02-architecture/decisions/ADR-024-entity-naming-unification.md) для паттернов типов и именования сущностей.

| Сценарий                             | Стратегия ID                                                                              |
| ------------------------------------ | ----------------------------------------------------------------------------------------- |
| Источник предоставляет стабильный ID | Использовать как есть (`chembl-id`, `pubchem-cid`)                                        |
| ID отсутствует                       | **Content Hash**: lowercase SHA-256 hex от `provider + canonical_json(normalized_record)` |

- **Алгоритм**: `sha256(provider + canonical_json(normalized_record)).hexdigest()`
- **Canonical JSON**: строится только через canonical serialization helper, а не через ad-hoc `json.dumps(...)` call-site.
  - **Float Precision**: Все значения типа float принудительно округляются: `round(val, 10)` для нивелирования различий архитектур процессоров.

### 2.9.1. Robust Content Hash

Для обеспечения стабильности хэша перед генерацией ID данные должны быть нормализованы:

- **NaN/Inf**: Заменяются на `null` (None).
- **Floats**: Округляются до 10 знаков после запятой.
- **Dates**: Приводятся к единому ISO-формату `YYYY-MM-DD`.
- **Strings**: Удаление пробелов по краям (`strip()`).

**Исключения**: Из расчета хэша исключаются технические мета-поля, включая поля с префиксом `_` (например: `_ingestion_ts`, `_run_id`, `_run_type`, `_dq_*`, `_source_batch_id`, `_index`, `_lookup_method`, `_original_id`, `_source`).

- **Детекция Коллизий**: При upsert проверять `source_record_id`; если отличается — конфликт, логировать обе записи.

### 2.9. Composite Pipelines

См. [ADR-026](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md) для архитектуры композитных пайплайнов.

Composite Pipeline объединяет данные из нескольких источников в единую обогащённую сущность:

1. **Seed Pipeline** — извлекает первичные сущности (напр., публикации из ChEMBL)
1. **Dependency Pipelines** — заполняют Silver-таблицы перед обогащением (опционально)
1. **Enricher Pipelines** — обогащают данными из других источников (CrossRef, OpenAlex, PubMed)
1. **Merge Step** — объединяет все обогащения в единую Gold-сущность

#### 2.9.1. Dependency Pipelines (Chained Dependencies)

Dependencies — пайплайны, которые запускаются **после seed, но до enrichers**. В отличие от enrichers (читают из Silver), dependencies выполняют полный цикл API→Bronze→Silver.

**Конфигурация dependency:**

```yaml
dependencies:
  - pipeline: chembl_target_component
    join_keys: [primary_component_id]  # Ключ из seed
    filter_field: component_id
    silver_table: silver/chembl/target_component
```

**Chained Dependencies (цепочечные зависимости):**

Когда один dependency предоставляет ключи для другого:

```yaml
dependencies:
  # 1. Стандартный: ключи из seed
  - pipeline: chembl_target_component
    join_keys: [primary_component_id]
    filter_field: component_id
    silver_table: silver/chembl/target_component

  # 2. Цепочечный: ключи из предыдущего dependency
  - pipeline: chembl_protein_class
    join_keys: [protein_classification_id]  # Колонка в source таблице
    filter_field: protein_class_id          # Поле API (если отличается)
    key_source: chembl_target_component     # Читать ключи отсюда
    silver_table: silver/chembl/protein_class
```

**Поля DependencyConfig:**

| Поле              | Тип     | Описание                                     |
| ----------------- | ------- | -------------------------------------------- |
| `pipeline`        | string  | Имя пайплайна                                |
| `join_keys`       | list    | Колонки для извлечения ключей                |
| `key_source`      | string? | `null`/`"seed"` = seed, иначе имя dependency |
| `filter_field`    | string? | Поле API для фильтрации (если ≠ join key)    |
| `required`        | bool    | При `true` — ошибка останавливает composite  |
| `timeout_seconds` | int     | Таймаут выполнения                           |
| `silver_table`    | string? | Путь к Silver-таблице                        |

#### 2.9.2. Merge Configuration

| Параметр               | Описание                            | Значения                                                           |
| ---------------------- | ----------------------------------- | ------------------------------------------------------------------ |
| `strategy`             | Стратегия объединения               | `left_outer`, `inner`, `union`                                     |
| `conflict_resolution`  | Разрешение конфликтов полей         | `seed_priority`, `enricher_priority`, `coalesce`, `explicit_rules` |
| `preserve_all_sources` | Сохранение всех колонок провайдеров | `true` / `false` (default)                                         |

#### 2.9.3. preserve_all_sources Feature

Опция `preserve_all_sources` в `MergeConfig` контролирует обработку колонок при слиянии:

| Режим                                   | Поведение                                                                            | Используется когда                          |
| --------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------- |
| `preserve_all_sources: false` (default) | Колонки из разных источников **сливаются** (coalesce) в единую колонку по приоритету | Нужна единая "лучшая" версия поля           |
| `preserve_all_sources: true`            | **Все** квалифицированные колонки сохраняются                                        | Нужны данные из всех источников для анализа |

**Формат колонок при `preserve_all_sources: true`:**

```
{provider}.{entity}.{field}
```

**Пример:**

```yaml
# configs/composites/publication.yaml
merge:
  strategy: left_outer
  conflict_resolution: seed_priority
  preserve_all_sources: true  # Сохранить все колонки провайдеров
```

**Результирующие колонки:**

```
# При preserve_all_sources: false (coalesce)
title                           # Единственная колонка title

# При preserve_all_sources: true (все источники)
chembl.publication.title        # Значение из ChEMBL
crossref.publication.title      # Значение из CrossRef
openalex.publication.title      # Значение из OpenAlex
pubmed.publication.title        # Значение из PubMed
```

**Когда использовать:**

- **`preserve_all_sources: true`**: Анализ качества данных, сравнение источников, ML-фичи из нескольких провайдеров
- **`preserve_all_sources: false`**: Продакшн-витрины с единственной "лучшей" версией каждого поля

#### 2.9.4. Column Groups

Для контроля порядка колонок в output используется конфигурация `column_groups`:

```yaml
merge:
  column_groups:
    - name: identifiers
      fields: [publication_id, doi, pmid]
      provider_order: [chembl, crossref, openalex, pubmed]
    - name: title
      fields: [title]
      provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]
```

#### 2.9.5. Field Group Registry

`FieldGroupRegistry` обеспечивает семантическую группировку полей для:

- **Упорядочивание колонок** в merged output (группы отсортированы по приоритету enum)
- **Фильтрация Gold-слоя** — группа `TRASH` автоматически исключается из Gold output
- **Валидация** — отслеживание mapped/unmapped/system колонок

**8 семантических групп** (`PublicationFieldGroup` enum):

| Группа                          | Описание                                | Включается в Gold |
| ------------------------------- | --------------------------------------- | ----------------- |
| `ID-AND-STATUS`                 | Идентификаторы, DOI, PMID, статусы      | Да                |
| `BIBLIOGRAPHY`                  | Title, abstract, journal, volume, pages | Да                |
| `AUTHOR-AND-AFFILIATIONS`       | Авторы, аффилиации, ORCID               | Да                |
| `TERMS-AND-KEYWORDS-AND-TOPICS` | Keywords, MeSH, topics                  | Да                |
| `CITATIONS-AND-REFERENCE`       | Счётчики цитирований, ссылки            | Да                |
| `DATE-AND-PLACES`               | Даты публикации, страны                 | Да                |
| `PUBLICATION-TYPES`             | Типы документов                         | Да                |
| `TRASH`                         | Внутренние, избыточные, low-value       | **Нет**           |

<!-- Updated: was 94, now 106 (audit 2026-02-14) -->

**Конфигурация:** `configs/composites/field_groups/publication.yaml` — 106 базовых полей, маппинг на провайдерские колонки.

**Доменные модели** (`domain/composite/field_groups.py`):

- `FieldMapping` — маппинг `base-name → provider-columns + group`
- `FieldGroupDefinition` — определение группы с её полями
- `FieldGroupRegistry` — центральный реестр для lookup, фильтрации, сортировки

**Интеграция:** Bootstrap загружает реестр из YAML и инжектит в `MergeService`. При записи Gold trash-колонки фильтруются автоматически. При отсутствии конфигурации — graceful degradation (фильтрация не применяется).

#### 2.9.6. Column Renames (Layer-Specific)

`rename-fields` в `data-schema` конфигурации позволяет переименовывать колонки на уровне Silver и Gold слоёв.

**ВАЖНО**: `gold.rename-fields` **MUST** использовать имена колонок **ПОСЛЕ** `silver.rename-fields`.
Gold читает из Silver (Medallion flow), поэтому видит Silver output schema, а не оригинальные имена.

**Формат конфигурации:**

```yaml
# configs/entities/{provider}/{entity}.yaml
column-groups: [...]  # Shared groups

silver:
  include-groups: [system, identifiers, title]
  rename-fields:
    entity-id: document-id         # Rename in Silver
    content-hash: content-version

gold:
  include-groups: [system, identifiers, title]
  exclude-fields: [_dq_*, _index]
  rename-fields:
    # Use Silver output names (not original!)
    document-id: publication-id         # Silver renamed entity-id → document-id
    content-version: version-hash       # Silver renamed content-hash → content-version
    pmid: pubmed-id
```

**Rename Chain:**

```
Original → Silver → Gold
---------------------------------
entity-id → document-id → publication-id
content-hash → content-version → version-hash
pmid → pmid → pubmed-id
```

**Когда использовать:**

- **Silver**: Редко. Только для стандартизации внутренних имён между провайдерами
- **Gold**: Часто. Для user-friendly имён в аналитических витринах

**Best Practice:**

- Сохранять оригинальные имена в Silver (упрощает отладку)
- Применять бизнес-имена только в Gold (`pmid` → `pubmed-id`)

## 3. Обработка Ошибок и Наблюдаемость

### 3.1. Стратегия Обработки Ошибок

См. [ADR-016](../02-architecture/decisions/ADR-016-error-handling-strategy.md).

Вместо тотального подхода "Fail Fast" используем дифференцированный подход.

### 3.1.1. Классификация Ошибок

| Тип Ошибки                         | Поведение              | Пример                                                              |
| ---------------------------------- | ---------------------- | ------------------------------------------------------------------- |
| **Критическая** (Critical)         | Падение пайплайна      | Ошибка авторизации, несовпадение схемы в Gold, БД недоступна.       |
| **Восстановимая** (Recoverable)    | Повтор N раз (Backoff) | 429 Rate Limit, 502/504 Timeout, сетевой сбой.                      |
| **Качество данных** (Data Quality) | Лог + Пропуск записи   | Невалидный SMILES, отсутствует необязательное поле. Не роняет батч. |

### 3.1.2. Пороги Ошибок Батча (Thresholds)

- **Soft Threshold**: по умолчанию `>5%` ошибок качества данных -> Warning.
- **Hard Threshold**: default `hard_fail=0.50` (50%) for hierarchical `quality:`
  config (`configs/base/quality.yaml`), domain/contract fallbacks, and standard
  entity contracts. Some surfaces keep specialized overrides (e.g. stricter or
  looser entity/provider values). Monitoring alert
  `BioETLDQQuarantineRateCritical` uses the same 50% hard band. Matrix:
  `docs/04-reference/contracts/dq-contracts.md`.
- **Metric Scope**: Отслеживать как `record-error-rate` (доля битых строк), так и `entity-error-rate` (доля битых уникальных сущностей).

### 3.1.3. Параметры Retry (Backoff)

Для типа ошибок **Recoverable** применять стратегию Exponential Backoff:

- **Max Attempts**: 3
- **Multiplier**: 2.0 (wait 1s, 2s, 4s...)
- **Jitter**: Random(0.1s, 0.5s). Jitter **SHOULD** применяться для избежания thundering herd.
- **Deterministic Mode**: При `RetryConfig(deterministic=True)` jitter **MUST** вычисляться через hash вместо random для воспроизводимости. См. [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md).

### 3.1.4. Circuit Breaker (Размыкатель цепи)

Паттерн защиты от каскадных сбоев. См. [ADR-007](../02-architecture/decisions/ADR-007-circuit-breaker-implementation.md).

- **Trigger**: 5 последовательных ошибок соединения/таймаута.
- **Open Duration**: 5 минут (configurable: `circuit-breaker.recovery-timeout`).
- **Recovery**: Half-Open → 1 пробный запрос. Success → Closed, Failure → Open +5 мин.
- **Observability**: Метрики `bioetl_circuit_breaker_state` (0=Closed, 1=Half-Open, 2=Open), `bioetl_circuit_breaker_trips_total`. Алерт при зависании в Open > 10 мин.

### 3.2. Наблюдаемость (Observability)

См. [ADR-017](../02-architecture/decisions/ADR-017-observability-architecture.md) и [ADR-022](../02-architecture/decisions/ADR-022-tracing-noop.md) для NoOp Tracing.

- **TracingPort = OTel facade**: `TracingPort` сознательно моделирует OpenTelemetry Tracing API (`get-tracer → start-as-current-span → Span`). Это обеспечивает единый calling convention для NoOp и реального OTel бэкенда. См. ADR-022.
- **Correlation ID**: `run_id` обязателен во всех логах и блокировках.
- **Prometheus guardrail**: `run_id`, `manifest_id`, `record_id`,
  `lineage_fragment_id`, hashes и filesystem paths **MUST NOT** публиковаться
  как labels; per-run forensic correlation идёт через logs, RunManifest,
  RunLedger и inspection CLI.
- **Retention**: Логи хранятся 30 дней, метрики — 90 дней.
- **Логи**: Структурированный JSON.
- **Dataset ID**: В логи и метрики добавляется лейбл `dataset` (логическое имя таблицы, напр. `chembl/activity`), так как pipeline может писать в несколько таблиц.

### 3.2.1. Log Schema

| Поле         | Обязательность | Пример                         |
| ------------ | -------------- | ------------------------------ |
| timestamp    | MUST        | `2025-12-15T10:00:00Z`                |
| level        | MUST        | `INFO`, `ERROR`                       |
| run_id       | MUST        | UUID                                  |
| pipeline     | MUST        | `chembl_activity`                     |
| stage        | SHOULD      | `preflight`, `execution`, `postrun`   |
| dataset      | SHOULD      | `chembl/activity`                     |
| record_count | SHOULD      | 1000                                  |
| error_type   | При ошибках | `SCHEMA_VIOLATION`, `timeout`, `other` |

### 3.2.2. Prometheus Metrics

**Endpoint:** `http://localhost:{BIOETL_METRICS_PORT}/metrics` (default port: 8000)

**Запуск метрик:**

- Автоматически через composition runtime observability bootstrap during
  normal `bioetl run`, `bioetl run-all` и `bioetl run-composite` execution
- Идемпотентный: повторный вызов безопасен (Double-Check Locking)
- Graceful degradation: ошибки метрик не блокируют пайплайн

**Pipeline Metrics (prefix: `bioetl_`):**

| Метрика                       | Тип       | Labels                            | Описание                        |
| ----------------------------- | --------- | --------------------------------- | ------------------------------- |
| `bioetl_pipeline_duration_seconds` | Histogram | pipeline, stage, status, run_type | Длительность выполнения этапов  |
| `bioetl_records_processed_total`   | Counter   | pipeline, stage, run_type         | Количество обработанных записей |
| `bioetl_errors_total`              | Counter   | pipeline, stage, error_code       | Количество ошибок по типам      |
| `bioetl_batch_size_records`        | Histogram | pipeline, stage                   | Распределение размеров батчей   |
| `bioetl_filter_ids_loaded_total`   | Counter   | pipeline, source_kind             | Загружено ID для фильтрации     |
| `bioetl_filter_ids_duplicates_total` | Counter | pipeline, source_kind             | Дубликаты в файле фильтрации    |

Для runtime `stage`/`phase` labels используйте только bounded vocabulary:

- ordinary lifecycle: `startup`, `preflight`, `lifecycle_clear`, `execution`,
  `postrun`, `cleanup`
- record-flow stages: `bronze`, `silver`, `gold`, `filtered_out`,
  `quarantined`, `validation`, `transform`
- composite phases: `preflight_validation`, `seed`, `dependencies`,
  `enrichment`, `merge`, `cross_validation`, `gold_write`

Для adapter labels:

- `endpoint` MUST быть нормализован к bounded route-template виду
  (`/works/{id}`, а не `/works/123456789`)
- `source_kind` MUST публиковаться как bounded source vocabulary; raw file/path
  identity MUST NOT appear in Prometheus labels
- `operation` MUST использовать reviewable bounded vocabulary; неизвестные
  значения схлопываются в `other`

**Реализация:** См. `src/bioetl/infrastructure/observability/metrics.py` и `prometheus_metrics.py`.

### 3.2.3. Dashboard Presentation Contract

Подробный проверяемый контракт для семи shipped Grafana dashboards закреплён в
[`DASHBOARD_REQUIREMENTS.md`](../01-requirements/DASHBOARD_REQUIREMENTS.md) и
остаётся подчинён ADR-010/ADR-053 и правилам observability этого раздела.

- `REQ-DASH-001`: дополнительные `row`-группы **MUST** иметь area-weighted
  data density не ниже `0.60` и count density не ниже `0.50` по формуле из
  dashboard requirements.
- `REQ-DASH-002`: operator-visible текст **MUST** быть не меньше `12pt`
  (`16px`), а заголовки панелей — не меньше `14pt` (`18.6667px`).
- `REQ-DASH-003`: area fills **MUST** использоваться только в первом окне
  (`gridPos.y < FIRST_WINDOW_Y` = `18`,
  `docs/03-guides/dashboards/contracts/layout-budgets.yaml`);
  дополнительные группы и панели ниже первого окна
  **MUST** использовать только text/line color encoding. Окно отбора
  first-load PromQL/HTTP (`FIRST_LOAD_Y_MAX` = `28` =
  `performance-budgets.yaml:first_screen_y_max`) — отдельная константа и
  **MUST NOT** подменять visual fold.

Static JSON checks не заменяют computed-style проверку в reproducible render.
Monitoring остаётся opt-in и не становится обязательной local runtime
зависимостью.

### 3.3. Конкурентность и Блокировки

> **CRITICAL: Local-Only Deployment & Redis Lock REJECTION**
> См. [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)

#### Strict Single Instance Policy (Local-Only)

**ЗАПРЕЩЕНО** запускать несколько экземпляров одного пайплайна. Система разработана как **Single Instance Application**.

- **Constraint**: `MemoryLock` работает только внутри одного процесса. Межпроцессные блокировки отсутствуют.
- **Риск**: Параллельный запуск приведет к повреждению данных (Data Corruption) в Delta Lake/JSONL.
- **Horizontal Scaling**: **FORBIDDEN**. Масштабирование только вертикальное.

#### Текущая реализация

- **Механизм**: In-memory блокировки (`MemoryLock`)
- **Scope**: Один процесс Python
- **Pipeline Lock**: Один активный инстанс `{provider}-{entity}`
- **Lock TTL**: `heartbeat-interval * 3` = **90 секунд** по умолчанию
- **Heartbeat**: **30 секунд** (настраивается в `RuntimeConfig`)
- **Lock Max Duration**: **4 часа**. Принудительное снятие по истечении.

#### Распределённое развёртывание (REJECTED)

> **Status: REJECTED** — см. [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)

**ОТКАЗ ОТ REDIS LOCK**: Использование `RedisLockAdapter` и межпроцессной lock-координации через Redis **ЗАПРЕЩЕНО**.
Архитектура проекта строго ограничена Local-Only Deployment. Любые попытки внедрить межпроцессные блокировки
будут отклонены как нарушение архитектурного стандарта (ADR-010).

**Invariant** (применимо ко всем вариантам развёртывания):

- Потеря блокировки = Потеря права на запись.
- Если Heartbeat не прошел, воркер **MUST** аварийно завершиться до попытки коммита данных.
- **Safety Guard**: Адаптер **MUST** валидировать наличие блокировки перед записью данных.

### 3.4. Метрики Качества Данных (DQ Metrics)

Метрики экспортируются в формате Prometheus с использованием bounded labels для агрегации. `bioetl_dq_validation_score` использует `pipeline`, `entity`; column/check-level breakdowns должны публиковаться отдельными метриками или reports, а не через этот label contract:

- `bioetl_dq_validation_score{pipeline="...", entity="..."}`: текущая DQ validation score (0.0-1.0, где 1.0 означает, что все записи валидны) для pipeline/entity.
- `bioetl_data_freshness_seconds`: разница между `now()` и `max(updated-at)`.

### 3.4.1. Детекция Аномалий DQ

- **Baseline (Базовая линия)**: Скользящее среднее за последние 30 дней.
- **Пороги Алертинга**:
  | Метрика                | Warning        | Critical       |
  | ---------------------- | -------------- | -------------- |
  | Рост `null-rate`       | >2x baseline   | >5x baseline   |
  | Падение `record-count` | \<70% baseline | \<50% baseline |
  | `freshness-lag-hours`  | >24h           | >72h           |
- **Автоматизация**: CI-джоб `dq-check` сравнивает текущий запуск с базовой линией.
- **Cold Start**:
  - Days 1-7: Silence (обучение).
  - Days 8-30: Warning only.
  - Days 30+: Full Alerting.

### 3.5. Provider Health Monitoring

| Status    | Условие                         | Действие                  |
| --------- | ------------------------------- | ------------------------- |
| Healthy   | 0 errors за 5 мин               | Normal operation          |
| Degraded  | 1-2 consecutive errors          | Timeout ×2, batch-size ÷2 |
| Unhealthy | ≥3 errors или health_check fail | Pause pipeline, Alert P2  |

**Recovery**: Unhealthy → Degraded после 1 успешного health_check.
**Metric**: `bioetl_provider_health_status{provider}` (0=Unhealthy, 1=Degraded, 2=Healthy).

## 4. Стандарты Кода и Тестирование

### 4.1. Стек и Матрица Решений

См. также [ADR-004](../02-architecture/decisions/ADR-004-pydantic-vs-dataclasses.md) для решения Pydantic vs Dataclasses.

| Задача          | Инструмент                        | Альтернатива       | Критерий выбора                                                                                                                                                                                        |
| --------------- | --------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Оркестрация** | **PipelineRunner**                | Prefect/Airflow    | Используем собственный легковесный Runner. Внешние фреймворки при >5 DAG-ов.                                                                                                                           |
| **Валидация**   | **Pandera**                       | Great Expectations | Pandera нативна для DataFrames, легче интегрируется в CI.                                                                                                                                              |
| **HTTP Клиент** | **httpx** via `UnifiedHTTPClient` | requests           | Поддержка `async`. Все адаптеры **MUST** использовать `UnifiedHTTPClient` (см. §4.1.1). **Legacy Wrappers**: Для библиотек без async поддержки (pubchempy) — `BaseSyncAdapter` с `ThreadPoolExecutor`. |
| **Линтер**      | **Ruff**                          | Flake8/Black       | Скорость и решение "все-в-одном".                                                                                                                                                                      |

### 4.1.1. Унифицированный HTTP-клиент (UnifiedHTTPClient)

**Все HTTP-адаптеры используют единую инфраструктуру для HTTP-запросов.**

`UnifiedHTTPClient` является каноническим runtime именем. Формулировка
`UnifiedAPIClient` из legacy/helper surfaces не даёт права создавать второй
клиент того же смысла. Разрешены только:

1. использование текущего `UnifiedHTTPClient`;
1. controlled rename через ADR с migration plan и удалением superseded
   implementation.

| Адаптер                  | Базовый класс     | HTTP-клиент              | Статус            |
| ------------------------ | ----------------- | ------------------------ | ----------------- |
| `ChemblAdapter`          | `BaseHttpAdapter` | `UnifiedHTTPClient`      | ✅ Унифицирован   |
| `UniProtAdapter`         | `BaseHttpAdapter` | `UnifiedHTTPClient`      | ✅ Унифицирован   |
| `PubMedAdapter`          | Mixin-based       | `UnifiedHTTPClient`      | ✅ Унифицирован   |
| `PubChemAdapter`         | `BaseSyncAdapter` | `pubchempy` + ThreadPool | ✅ Legacy-обёртка |
| `CrossRefAdapter`        | `BaseHttpAdapter` | `UnifiedHTTPClient`      | ✅ Унифицирован   |
| `OpenAlexAdapter`        | `BaseHttpAdapter` | `UnifiedHTTPClient`      | ✅ Унифицирован   |
| `SemanticScholarAdapter` | `BaseHttpAdapter` | `UnifiedHTTPClient`      | ✅ Унифицирован   |

**Компоненты `UnifiedHTTPClient`:**

- **Rate Limiter** (`TokenBucket`): Ограничение частоты запросов по провайдеру
- **Circuit Breaker**: Защита от каскадных отказов (см. [ADR-007](../02-architecture/decisions/ADR-007-circuit-breaker-implementation.md))
- **Retry Logic**: Exponential backoff с configurable jitter
- **Metrics Integration**: Автоматический сбор метрик через `MetricsPort`

**Расположение:** `src/bioetl/infrastructure/adapters/http/client.py`

**Создание нового адаптера:**

```python
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class NewProviderAdapter(BaseHttpAdapter):
    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        logger: LoggerPort,
    ):
        super().__init__(http_client, logger)
        self.provider_name = "new-provider"
```

**Для sync-библиотек** используйте `BaseSyncAdapter` с DI:

```python
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter

class LegacyAdapter(BaseSyncAdapter):
    provider_name = "legacy"

    def __init__(
        self,
        logger: LoggerPort,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        thread_pool: ThreadPoolExecutor,
    ):
        # Все зависимости инжектируются из Composition Root
        super().__init__(logger, rate_limiter, circuit_breaker, thread_pool)

    async def fetch(self, ...):
        # Sync call wrapped in executor
        result = await self._run_in_executor(sync_library.fetch, query)
```

### 4.2. Политика Тестирования

**Цель покрытия:** ≥85% line coverage (проверяется в CI через `--cov-fail-under=85`).

- **Unit**: Только доменная логика. In-memory fakes предпочтительны, MagicMock допустим.
- **Integration**:
  - **VCR.py**: Запись ответов API в кассеты (`tests/fixtures/vcr/`).
  - **Санитизация**: Обязательная очистка секретов (`Authorization`, `X-API-Key`) и PII в хуке `before-record`.
  - **CI**: Падать, если кассета отсутствует (`pytest --vcr-record=none`), чтобы гарантировать отсутствие сетевых вызовов в CI.
- **E2E (End-to-End)**: Полный цикл пайплайна от fetch до Gold (`tests/e2e/`).
  - **Архитектура**: Local-Only (файловая система, MemoryLock, LocalCheckpoint).
  - **Helpers**: `create-test-context()`, `assert-bronze-files-exist()`, `assert-silver-table-has-records()`.
  - **Маркер**: `@pytest.mark.e2e` для селективного запуска.
  - **Запуск**: `pytest tests/e2e/ -v -m e2e`.
- **Contract Tests**: Ежемесячный запуск против *реальных* API (Live) в отдельном CI workflow для обнаружения нарушения контрактов.
- **Behavior changes**: любое изменение наблюдаемого поведения **MUST**
  сопровождаться новым или обновлённым regression test. Для bug fix тест
  **MUST** воспроизводить прежний дефект и проходить после исправления.
- **Assertion integrity**: assertions **MUST NOT** ослабляться или удаляться
  только ради прохождения suite. Переход от exact equality к permissive
  contains/range check требует явного contract-based обоснования.
- **Deterministic tests**: unit/integration tests **MUST NOT** зависеть от
  uncontrolled wall-clock time, unseeded randomness или live network.
  Используются fixed/frozen time, seeded inputs, mocks, fixtures или VCR
  cassettes. Live contract tests остаются отдельным явно маркированным workflow.

#### 4.2.1. Тестовые Зависимости и Установка

Проект использует optional dependency группы в `pyproject.toml`:

| Группа    | Установка                | Назначение                                                        |
| --------- | ------------------------ | ----------------------------------------------------------------- |
| `tests`   | `pip install .[tests]`   | Минимальный набор для запуска тестов                              |
| `dev`     | `pip install .[dev]`     | Полный набор для разработки (включает tests + linting + security) |
| `tracing` | `pip install .[tracing]` | OpenTelemetry для production tracing                              |
| `docs`    | `pip install .[docs]`    | MkDocs для генерации документации                                 |

**Группа `tests` включает:**

- `pytest>=8.0`, `pytest-cov>=4.0`, `pytest-asyncio>=0.23`, `pytest-xdist>=3.5` — основа тестирования
- `respx>=0.21` — HTTP-мокирование для тестов адаптеров
- `hypothesis>=6.100` — property-based тестирование
- `vcrpy>=6.0`, `pytest-recording>=0.13` — VCR-кассеты для integration-тестов
- `syrupy>=4.0` — snapshot-тестирование

**Рекомендуемый способ установки:**

```bash
# Для разработки (полный набор)
uv sync --extra dev --extra tests --extra tracing
uv run python -m scripts.ops setup-plugins

# Только для запуска тестов (CI/lightweight)
pip install -e ".[tests]"
```

**ВАЖНО**: При использовании `pip install .[tests]` убедитесь, что все тестовые зависимости доступны. Если тесты падают с `ModuleNotFoundError`, проверьте версию `pyproject.toml` и выполните `pip install -e ".[tests]"` заново.

### 4.3. Детерминизм и Воспроизводимость

См. [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md).

#### MUST (Обязательно)

1. Storage writers **MUST NOT** использовать модуль `random`
1. Timestamps **MUST** передаваться из application слоя, не создаваться в infrastructure
1. Retry jitter **MUST** быть детерминистичным при `deterministic=True`
1. `PipelineContext.started-at` — единственный источник времени для batch
1. Application и Interfaces слои **MUST NOT** импортировать `structlog` напрямую — использовать `LoggerPort` из `domain.ports`
1. Output artifacts **MUST** использовать stable ordering, canonical
   serialization и UTC timestamps. Locale-dependent formatting и iteration по
   unsorted sets/maps в persisted output запрещены.
1. Artifact files **MUST** записываться атомарно: temporary file в том же
   filesystem, flush/close, затем `os.replace()` в final path. Прямая запись в
   final artifact path запрещена, если partial file может быть прочитан другим
   процессом или последующим run.

#### Архитектурные Тесты (REQ-ARCH-030)

| Тест                                          | Цель                                 | Проверки                                                                     |
| --------------------------------------------- | ------------------------------------ | ---------------------------------------------------------------------------- |
| `test-no-random-in-writers`                   | Блокирует `random` в storage writers | `import random`, `from random import`, `random.uniform()`, `random.choice()` |
| `test-no-datetime-now-in-infrastructure`      | Блокирует `datetime.now()` в infra   | `datetime.now()`, `datetime.datetime.now()`                                  |
| `test-no-structlog-in-application-interfaces` | Блокирует прямой импорт `structlog`  | `import structlog`, `from structlog import`                                  |

**Путь:** `tests/architecture/test_no_random_in_writers.py`, `tests/architecture/test_no_datetime_now_in_infrastructure.py`, `tests/architecture/test_no_structlog_in_application_interfaces.py`

#### Детерминистичный Jitter

```python
# RetryConfig (src/bioetl/domain/resilience.py)
RetryConfig(
    deterministic=True,  # Hash-based jitter
    jitter - seed=42,  # Reproducible seed
)
```

При `deterministic=True` jitter вычисляется как:

```python
hash_input = f"{attempt}:{url}:{seed}"
jitter_digest = md5(hash_input.encode("utf-8")).hexdigest()
jitter_factor = (int(jitter_digest[:8], 16) % 1000) / 1000.0
```

#### Единый Источник Времени

```python
# Application layer создаёт timestamp
context = PipelineContext.create(run_id, run_type, logger)
# context.started_at используется во всех компонентах

# Infrastructure получает timestamp как параметр
await bronze_writer.write_bronze(..., ingestion_ts=context.started_at)
await quarantine.write(..., ingestion_ts=context.started_at)
```

`PipelineContext` остаётся нормативным execution context, а не "ошибочно размещённым infra object". Его `logger`
поле и `bind_logger()` нужны для детерминированной и переносимой передачи run metadata через `LoggerPort`; concrete
logging framework по-прежнему создаётся вне domain и не пробивает layer boundary.

### 4.4. Python Standards

#### 4.4.1. Future Annotations (PEP 563)

Все Python-файлы **MUST** начинаться с:

```python
from __future__ import annotations
```

**Причины:**

- Отложенная evaluation типов (производительность)
- Поддержка forward references без кавычек
- Совместимость с Python 3.10+ стилем типизации

**Проверка:** `ruff check --select FA` и
`pytest tests/architecture/test_future_annotations_policy.py`.

**Расположение в файле:**

1. Shebang (если есть): `#!/usr/bin/env python`
1. Encoding declaration (если есть): `# -*- coding: utf-8 -*-`
1. Module docstring
1. `from __future__ import annotations` ← сразу после docstring
1. Другие импорты

> **Исключение**: минимальные package-facade `__init__.py`, содержащие только
> re-exports (`from ... import ...`) и `__all__`, **MAY** опускать
> `from __future__ import annotations`.
>
> Исключение намеренно узкое и machine-checked:
> `tests/architecture/test_future_annotations_policy.py` не допускает
> расширения исключения на обычные модули, compatibility facades и `__init__.py`
> с любой runtime-логикой.

#### 4.4.2. Type Hints

- **MUST** использовать новый стиль типов: `list[str]` вместо `List[str]`
- **MUST** использовать `X | None` вместо `Optional[X]`
- **SHOULD** использовать `X | Y` вместо `Union[X, Y]`
- Все новые или изменённые public functions, methods и externally visible
  attributes **MUST** иметь явные parameter/attribute и return annotations и
  проходить `mypy --strict`.
- `Any` **MUST NOT** использоваться как способ скрыть type-checking defect или
  заменить выводимый конкретный тип. Допустим только минимальный boundary для
  действительно dynamic/untyped integration; он **MUST** быть локализован,
  сразу преобразован в конкретный type/Protocol/TypedDict/model и снабжён
  кратким обоснованием.

### 4.5. Change-set Governance Gates (Qodo Reconciliation)

Эта секция нормализует Qodo extraction от 2026-07-16 для repository scope
`/SatoryKono/BioactivityDataAcquisition/`. Исходный endpoint — semantic
`POST /rules/search`, а не list/export API; `top_k` ограничен 20, поэтому набор
из 66 unique Qodo rule IDs является broad best-effort union, а не доказанно
полным organization-wide export. Qodo response не содержал `severity`; значение
`UNSPECIFIED` сохраняется и **MUST NOT** заменяться догадкой.

RFC 2119 levels ниже определяются канонической BioETL policy, а не Qodo
severity. Duplicate-looking Qodo records с разными IDs сохраняются в
traceability mapping, но сводятся к одному project gate.

| Gate | Project rule | Qodo rule IDs |
| ---- | ------------ | ------------- |
| `QG-SEC-001` | Tracked code, docs, configs, YAML, tests, fixtures, logs и examples **MUST NOT** содержать live secrets, credentials, private keys или production-looking tokens; logging/serialization **MUST NOT** раскрывать sensitive configuration. | `717996`, `717895`, `717966`, `718010`, `717976`, `718034`, `717812` |
| `QG-SEC-002` | `.env` protections, ignore patterns, packaging exclusions и restrictive access **MUST NOT** ослабляться; любая операция над `.env`/`.env.*` требует explicit per-task user approval. | `1433724`, `717904`, `717802` |
| `QG-CFG-001` | Critical config modes **MUST** быть required, иметь documented allowed values и fail on unknown values; tracked YAML **MUST** сохранять canonical deterministic key order. | `718012`, `718032`, `718013`, `718011`, `718031` |
| `QG-TYPE-001` | Public interfaces **MUST** иметь полные type annotations; `Any` **MUST NOT** маскировать type errors и допустим только как documented narrow boundary. | `718001`, `717987`, `717867`, `717880`, `717968` |
| `QG-DET-001` | Persisted outputs **MUST** использовать stable ordering, canonical serialization и UTC timestamps. | `718014`, `717993` |
| `QG-DATA-001` | Merge/upsert **MUST** быть idempotent и keyed only by declared primary/documented stable business key. | `1433434` |
| `QG-COV-001` | При изменении `src/bioetl/**/*.py` тот же changeset **MUST** обновить `reports/quality/module-coverage-inventory.json:source_tree_sha256` и пройти architecture hash guard. | `837441` |
| `QG-DEBT-001` | Technical-debt budgets, quality thresholds и exclusions **MUST NOT** ослабляться или расширяться; лимиты могут только сохраняться или ужесточаться. | `883024` |
| `QG-DOC-001` | Contributor-facing scripts/commands и schema/column/CLI changes **MUST** синхронно обновлять active contributor docs; breaking CLI/API/schema/config changes требуют migration notes и changelog/version impact в том же changeset. | `1433447`, `717893`, `718030`, `718009`, `718035`, `718017`, `717995` |
| `QG-TEST-001` | Behavior/public-contract changes **MUST** иметь regression tests; assertions **MUST NOT** ослабляться ради green suite. | `717831`, `717936`, `718008`, `718007`, `718028` |
| `QG-PORT-001` | Ports **MUST** импортироваться только через facade `bioetl.domain.ports`. | `717998` |
| `QG-HTTP-001` | Provider/runtime outbound HTTP **MUST** идти через `UnifiedHTTPClient` или thin delegating wrapper; новые direct low-level clients запрещены. | `1433318` |
| `QG-ART-001` | Artifact writes **MUST** использовать temporary file и atomic `os.replace()` в final path. | `717994` |
| `QG-TSTDET-001` | Tests **MUST** контролировать time/random/network; external APIs используют fixtures/VCR, кроме explicit live-contract workflow. | `718005`, `718026`, `718006` |
| `QG-GOV-001` | Documentation **MUST NOT** противоречить `.importlinter`, CI, `AGENTS.md` или normative stack; Qodo config **MUST NOT** вводить undocumented keys или unsupported schema/version values. | `1433681`, `1433499` |
| `QG-LOG-001` | Runtime/application logging **MUST** использовать structured logging ports/framework; `print()`/`pprint()` запрещены вне sanctioned one-off scripts, REPL/examples и user-facing CLI output. | `718004`, `717896` |
| `QG-ARCH-001` | Constructor DI, composition-owned wiring, inward dependency direction, pure domain, adapter delegation и suffix naming **MUST** соблюдаться; service locator запрещён. | `718021`, `1433571`, `718000`, `1433310`, `718020`, `717830`, `717999`, `717997`, `717826`, `717965`, `718002`, `718023`, `717897` |
| `QG-MED-001` | Silver/Gold writes **MUST** использовать Delta Lake и exact-final-DataFrame Pandera validation; Gold strict validation fail-closed, Silver invalid data fails or quarantines before write. | `1559442`, `1433655`, `718003`, `1433643`, `1433385`, `1433400` |

## 5. Операции (Лимиты, Секреты, Shutdown)

### 5.1. Ограничение скорости (Rate Limiting)

Каждый адаптер обязан реализовать `TokenBucket` или аналог, соблюдающий лимиты провайдера.
**Обратное давление (Backpressure)**: Если внутренняя очередь заполнена >80%, адаптер должен замедлить чтение (дросселировать источник).

### 5.2. Управление Секретами

- **Источник**: Переменные окружения (`os.environ`).
- **Формат**: `BIOETL_{PROVIDER}_{KEY}` (например, `BIOETL_PUBCHEM_API_KEY`).
- **Запрещено**: Хардкод секретов **MUST NOT** встречаться в source, tracked
  YAML/config, docs, tests, fixtures, examples, CI, Dockerfiles или log samples.
  Inline credentials в URLs/connection strings, PEM blocks, JWT-like values и
  production-looking token prefixes считаются violations, если это не явно
  безопасные placeholders.
- **Logging**: environment maps, full configuration objects, authorization
  headers, tokens, passwords и secret-bearing connection strings **MUST NOT**
  логироваться или сериализоваться в published artifacts.
- **Tracked YAML**: secret-bearing keys допускают только placeholder или
  external reference (`${ENV_VAR}`, secret manager reference); live values
  запрещены.
- **`.env`**: файлы `.env`/`.env.*` в git **MUST NOT** попадать. Ignore,
  packaging/COPY exclusions и file access protections для secret sources
  **MUST NOT** ослабляться. Создание, изменение, rename, move, overwrite или
  delete любого `.env` требует explicit per-task user approval.

### 5.3. Graceful Shutdown (Штатное завершение)

См. [ADR-008](../02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md) *(Superseded — shutdown реализован в CLI и `application/core/lifecycle/shutdown.py`)*.
При получении SIGTERM/SIGINT:

1. Прекратить извлечение (fetch) новых записей.
1. Дождаться завершения записи текущего батча.
1. Сохранить чекпоинт в **local storage** с использованием атомарной записи файла (`*.tmp` -> rename) для предотвращения частичных обновлений.
1. Выйти с кодом 0.

- **Guarantees**: Система гарантирует At-Least-Once доставку + Дедупликацию в Silver (через Content Hash). Гарантия Exactly-Once на уровне транспорта не требуется.

### 5.3.1. Восстановление из Чекпоинта (Checkpoint Recovery)

При запуске пайплайн:

1. Проверяет наличие чекпоинта в локальном хранилище (`data/output/checkpoints`).
1. Если найден и передан флаг `--resume`:
   - Начинает с `last-processed-id + 1`.
   - Логирует: `Resuming from checkpoint: {id}`.
1. Если найден без флага:
   - Warning: "Stale checkpoint detected. Use --resume to continue or delete the checkpoint file to restart."
1. После успешного завершения: удалить локальный файл чекпоинта.

### 5.3.2. Async Resource Cleanup

См. [ADR-013](../02-architecture/decisions/ADR-013-async-storage-cleanup.md) и [ADR-015](../02-architecture/decisions/ADR-015-pipeline-services-lifecycle.md).

**Контракт `aclose()`:**
Все адаптеры и сервисы **MUST** реализовывать асинхронный метод `aclose()` для освобождения ресурсов:

```python
class MyAdapter:
    async def aclose(self) -> None:
        """Освобождение ресурсов.

        Идемпотентный — безопасен для повторных вызовов.
        """
        if self.-client:
            await self.-client.aclose()
            self.-client = None
```

**Требования:**

- **MUST** быть `async def` (асинхронный)
- **MUST** быть идемпотентным (безопасен для повторных вызовов)
- **MUST NOT** выбрасывать исключения
- **SHOULD** обнулять ссылки после закрытия (`self.-client = None`)

**PipelineService Lifecycle:**

```python
async with services:  # --aenter-- инициализирует ресурсы
    await runner.run()
# --aexit-- вызывает aclose() для всех компонентов
```

### 5.4. Политика Чувствительных Данных (Sensitive Data)

- **Classification**: Public / Internal / Restricted.
- **Access Control**: Следовать least-privilege для текущего runtime: секреты и
  write-доступ к локальным данным выдаются только оператору/процессу,
  запускающему пайплайн.
- **Bronze**: Хранить как есть (Internal).
- **Silver**: Хэшировать PII поля: `sha256(lowercase(value) + SALT)` (Restricted). **PII fields MUST be salted.**
- **Gold**: PII исключается или агрегируется (Public/Internal).

**Threat Model Scope**:

- В фокусе: Утечка PII через логи, SQL-инъекции, несанкционированный доступ к локальным данным.
- Out of Scope: Компрометация хоста/рабочей станции вне границ приложения,
  физический доступ к устройству, атаки на внешнюю инфраструктуру,
  не управляемую самим BioETL.

### 5.5. Disaster Recovery (DR)

- **RPO**: 24 часа.
- **RTO**: 4 часа.
- **Game Days**: Game Days **SHOULD** проводиться ежегодно. Обязательные учения по восстановлению. Success criteria: данные идентичны, время < RTO.

#### 5.5.1. Detailed DR Procedures (Runbook)

| Сценарий                         | Действие                                                                                                                                                                              |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Повреждение Bronze/Silver**    | 1. Остановить пайплайны. 2. Восстановить локальное хранилище из backup (point-in-time restore). 3. Перезапустить пайплайны с флагом `--run-type rebuild` (если затронут Silver).      |
| **Потеря чекпоинта**             | Удалить файл чекпоинта: `data/output/checkpoints/{pipeline-name}.json`, затем запустить `--run-type rebuild` (приведет к дубликатам в Bronze, но дедупликация в Silver исправит это). |
| **Потеря локального хоста/тома** | 1. Поднять новый локальный runtime/рабочую директорию. 2. Восстановить backup данных и конфигов. 3. Запустить `--run-type rebuild` или targeted restore по runbook.                   |

### 5.6. Среды (Environments)

- **Dev**: Локальная разработка (Local-Only, см. [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)). Данные: фикстуры или sample Bronze.
- **Staging-like local profile**: Локальный или single-host профиль для rehearsal/verification с prod-like обфусцированными данными и отдельным data root.
- **Prod-like local profile**: Операторский single-host профиль для долгоживущих данных и контролируемых запусков. Это не отдельный distributed deployment tier.

### 5.6.1. Environment Isolation

Изоляция ресурсов для предотвращения "Cross-Env Pollution".

> **Note**: Текущая архитектура — Local-Only (см. [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)).
> Изоляция ниже относится к локальным/single-host профилям, а не к
> распределённому runtime.

- **Storage**: Разные локальные директории данных (`data/dev`, `data/staging`, `data/prod` или явные override-paths вне репозитория).
- **Configs**: Строгое разделение переменных окружения и секретов между профилями. Live credentials не хранятся в репозитории.

## 6. Документация (Автоматизация — приоритет)

- **Source of Truth**: Для текущего project guidance нормативными остаются активные docs в `docs/00-05`.
- **Archive Boundary**: Материалы в `docs/99-archive/` сохраняются для traceability и historical context, но не являются нормативными для текущего поведения проекта.
- **Guardrails**: Активная документация и generated docs **MUST** проходить
  автоматические docs-проверки (`python -m scripts.docs check-links` и
  выделенные generated-doc checks в CI).
- **Карта и Схемы**: Генерируются скриптами в CI (pydantic-to-json-schema, eralchemy2, mkdocs).
- **Именование**: Зеркальное (`src/bioetl/.../{provider}/` \<-> `docs/04-reference/providers/{provider}/`).
- **Contributor sync**: изменения contributor-facing commands, scripts,
  flags, paths, bootstrap/test flow или required checks **MUST** обновлять
  соответствующие active contributor/governance docs в том же changeset.
- **Governance consistency**: docs о layer boundaries, imports, required
  checks и sanctioned tooling **MUST** соответствовать `.importlinter`, CI,
  `AGENTS.md`, этому документу и accepted ADRs; docs mirrors не могут вводить
  исключения самостоятельно.

## 6.1. Детерминизм и Воспроизводимость

> См. [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md) для полного обоснования.

**Детерминизм** — это гарантия того, что при одинаковых входных данных (source data, config) пайплайн всегда произведет идентичные выходные данные и побочные эффекты.

#### MUST (Обязательно)

1. **Randomness**: Модуль `random` **MUST NOT** использоваться в `infrastructure/storage` и других критических узлах записи. Используйте хэш-функции от входных данных или фиксированные константы.
1. **Time Source**: `datetime.now()` **MUST NOT** вызываться в `domain` business-path и `infrastructure` слое по умолчанию. Канонический source-of-time seam для pipeline runtime — `domain/context.py` (`PipelineContext.started_at` / `_now_utc`). Все runtime timestamps (`_ingestion_ts`, `_processing_ts`, lifecycle timestamps aggregate'ов) **MUST** генерироваться в sanctioned seam/Application слое и передаваться вниз явными параметрами. Read-model вычисления длительности/возраста **MUST** использовать сохранённый terminal timestamp или explicit reference time, а не скрытый `now`. Реальные monitoring/audit exceptions допускаются только через явный allowlist в architecture tests.
1. **Retry Jitter**: При `deterministic=True`, jitter **MUST** вычисляться детерминистично (на основе хэша попытки и URL). Реализация: `domain/resilience.py:RetryConfig.calculate-delay()` использует MD5-based jitter.
1. **Ordering**: Запись в Delta Lake **MUST** происходить после сортировки данных по Primary Keys (Silver) или Business Keys (Gold).
1. **Content Hash**: Исключать из расчёта хэша технические мета-поля. Canonical policy: см. `docs/02-architecture/policies/content-hash-identity-policy.md`; поля с префиксом `_` исключаются из identity/hash (включая `_ingestion_ts`, `_run_id`, `_run_type`, `_source_batch_id`, `_index`, `_dq_*`, `_lookup_method`, `_original_id`, `_source`). Реализация: `domain/constants.py:META_FIELDS` + `domain/transformations.py:_should_include_field()`. Для общей программы нормализации RunManifest / RunLedger / runtime anchors / ChemBL Activity см. `docs/05-engineering/normalization_plan_P0_P6.md`.

#### Архитектурные Тесты Детерминизма

| Тест                                       | REQ          | Проверка                                                              | Файл                                        |
| ------------------------------------------ | ------------ | --------------------------------------------------------------------- | ------------------------------------------- |
| `test-no-random-import-in-storage-writers` | REQ-ARCH-030 | Запрет `import random`                                                | `test_no_random_in_writers.py`              |
| `test-no-random-uniform-calls-in-storage`  | REQ-ARCH-030 | Запрет `random.uniform()`                                             | `test_no_random_in_writers.py`              |
| `test-no-random-choice-calls-in-storage`   | REQ-ARCH-030 | Запрет `random.choice()`                                              | `test_no_random_in_writers.py`              |
| `test-no-datetime-now-in-infrastructure`   | REQ-ARCH-031 | Запрет `datetime.now()`                                               | `test_no_datetime_now_in_infrastructure.py` |
| `test-no-datetime-now-in-domain`           | REQ-ARCH-031 | Запрет `datetime.now()` вне sanctioned seam                           | `test_no_datetime_now_in_domain.py`         |
| `test-replay-critical-time-seams`          | REQ-ARCH-031 | Запрет скрытого wall-clock в replay-critical runtime/checkpoint paths | `test_replay_critical_time_seams.py`        |
| `test-allowed-files-still-exist`           | REQ-ARCH-031 | Валидация исключений                                                  | `test_no_datetime_now_in_infrastructure.py` |

#### Детерминистичный Retry Jitter

```python
# domain/resilience.py — MD5-based jitter для кросс-процессной стабильности
hash_input = f"{attempt}:{url}:{seed}"
digest = hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()
jitter_factor = int(digest[:8], 16) / 0xFFFFFFFF
```

При `RetryConfig(deterministic=False)` выдаётся `DeprecationWarning` — рекомендуется переход на детерминистичный режим.

## 7. Протокол Архитектурных Обзоров

### 7.1. Обязательная Двойная Верификация (REQ-ARCH-040)

> **Причина введения**: Анализ 2025-12-27 выявил ~50% ложных утверждений в планах рефакторинга.
> Утверждения делались без проверки фактического состояния кода.

> **⚠️ ОБЯЗАТЕЛЬНО**: Перед предложением рефакторинга **MUST** выполнить верификацию согласно
> протоколу из `CLAUDE.md` §0, опираясь на код и активные docs в `docs/00-05`.
> `docs/99-archive/refactoring-plan.md` допускается только как historical context,
> но не как нормативный источник текущего состояния.

При проведении архитектурных обзоров **MUST** выполнять двойную верификацию каждой найденной проблемы:

#### 7.1.1. Первая верификация (при обнаружении)

**Немедленно после обнаружения потенциальной проблемы:**

```bash
# 1. Проверить размер и структуру компонента
wc -l <path-to-python-file>
grep -c "def \|async def " <path-to-python-file>

# 2. Проверить делегирование (признак когезии vs god object)
grep -n "self\.-.*\." <path-to-python-file> | head -20

# 3. При необходимости сверить активные docs и текущие task/report artifacts
rg -n "ClassName|method-name|RF-|AUD-" docs/00-project docs/02-architecture reports docs/reports

# 4. Найти существующие реализации
grep -r "class ClassName\|def method-name" src/bioetl/
```

**Критерии подтверждения проблемы:**

- [ ] Файл прочитан полностью (не только упоминания)
- [ ] Размер компонента измерен (LOC, количество методов)
- [ ] Делегирование проанализировано
- [ ] При необходимости проверены активные docs / текущие task artifacts
- [ ] Проверено, что не реализовано ранее

#### 7.1.2. Вторая верификация (при документировании)

**При подготовке итогового документа обзора:**

Каждое утверждение о проблеме **MUST** содержать:

| Поле                 | Требование                                    |
| -------------------- | --------------------------------------------- |
| **Файл:строки**      | Точная ссылка на код (`runner.py:116-123`)    |
| **Размер**           | LOC и количество методов                      |
| **Структура**        | Описание публичных методов и делегирования    |
| **Дата верификации** | Дата проверки кода                            |
| **Проверено**        | "Проверено кодом и активной документацией ✅" |

**Пример верифицированного утверждения:**

```markdown
## Проблема: PipelineObserver создаётся в runner

### Верификация
- **Файл**: `runner.py:116-123` (175 строк, 9 методов)
- **Код**: `observer = PipelineObserver(...)`
- **Дата**: 2025-12-27
- **Проверено**: Проверено кодом и активной документацией ✅

### Текущее состояние
PipelineRunner.run() создаёт PipelineObserver напрямую вместо получения через DI.

### Влияние
Усложняет мокирование Observer в unit-тестах.
```

#### 7.1.3. Запрещённые Паттерны

**MUST NOT** делать утверждения без верификации:

<!-- Updated: was 527 LOC / 8 методов, now 818 LOC / 21 метод (audit 2026-02-14) -->

| ❌ Неверно                      | ✅ Верно                                                                                                                    |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| "PreflightService — god object" | "PreflightService (`preflight/service.py`, 221 LOC, 8 методов, 2 публичных) имеет узкую ответственность pre-run validation" |
| "Компонент перегружен"          | "Компонент (`file.py`, N строк) содержит M методов, делегирует K сервисам"                                                  |
| "Нет валидации X"               | "Валидация X отсутствует в `file.py` (проверено grep по 'X')"                                                               |

#### 7.1.4. Типичные Ложные Выводы

<!-- Updated: ChemblAdapter 975→992; GoldWriter 946→960 (audit 2026-02-27) -->

| Паттерн                             | Почему ошибочен                                                         | Пример из кодовой базы                                                                         |
| ----------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| "500+ LOC = god object"             | Размер ≠ сложность. Когезивный сервис с единой ответственностью валиден | `ChemblAdapter` (992 LOC) делегирует через `EntityMapper`, `ErrorClassifier`, `AdapterMetrics` |
| "Монолит требует декомпозиции"      | Файл с делегированием — НЕ монолит                                      | `GoldWriter` (960 LOC) делегирует `CsvExporter`, `AuditPort`, режимы записи когезивны          |
| "NoOp default = нарушение DI"       | Null Object Pattern валиден для опциональных зависимостей               | `NoOpMetrics`, `NoOpTracing`                                                                   |
| "Optional parameter = нарушение DI" | \`policy: Policy                                                        | None = None\` — допустимый паттерн для value objects                                           |
| "click.echo в CLI = нарушение"      | User-facing output — законная ответственность interfaces слоя           | `interfaces/cli/main.py` confirmation prompts                                                  |
| "Shim file = дублирование"          | Re-export для backward compatibility валиден                            | `medallion_lifecycle.py`                                                                       |
| "Нет автоматизации X"               | Часто уже реализовано, но не проверено                                  | `MedallionPolicy`, `DQConfig` существуют                                                       |

#### 7.1.5. Причины Ложных Утверждений (REQ-ARCH-041)

> **Статистика**: Анализ 2025-12-27 выявил ~50% ложных утверждений в планах рефакторинга.

| Причина                                  | Описание                                        | Митигация                                                  |
| ---------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------- |
| **Отсутствие верификации кодом**         | Утверждения без проверки фактического состояния | `grep`, `wc -l`, чтение файла                              |
| **Ложная корреляция размер → сложность** | 500+ LOC автоматически считается "монолитом"    | Анализ делегирования (см. 7.1.6)                           |
| **Неверная интерпретация паттернов**     | NoOp как нарушение DI, shim как дублирование    | Знание Null Object Pattern, backward-compat                |
| **Устаревшие знания**                    | Задача уже реализована, но это не проверено     | Сверка с кодом, активными docs и текущими review artifacts |

#### 7.1.6. Анализ Делегирования (MUST перед "god object")

**ПЕРЕД** утверждением "god object" или "монолит" **MUST** выполнить:

```bash
# 1. Измерить размер (порог: 500 LOC)
wc -l <path-to-python-file>

# 2. Найти делегирование (> 3 компонентов = НЕ монолит)
grep -o "self\.-[a-z-]*" <path-to-python-file> | sort -u | wc -l

# 3. Проверить публичные методы
grep -c "^    def \|^    async def " <path-to-python-file>

# 4. При необходимости сверить активные review/task artifacts
rg -n "ChemblAdapter|GoldWriter|PreflightService" reports docs/00-project docs/02-architecture
```

**Критерии "монолита" (ВСЕ должны выполняться):**

- [ ] 500+ строк кода
- [ ] Мало делегирования (< 3 уникальных `self.-component`)
- [ ] Много публичных методов с разной ответственностью
- [ ] Отсутствие injection через конструктор

**Контрпримеры (НЕ монолиты, несмотря на размер):**

<!-- Updated: ChemblAdapter 975→992; GoldWriter 946→960; PreflightService 818→841 (audit 2026-02-27) -->

- `ChemblAdapter` (992 LOC): Делегирует 4 компонентам, когезивная ответственность
- `GoldWriter` (960 LOC): Делегирует `CsvExporter`, `AuditPort`, режимы записи когезивны
- `PreflightService` (841 LOC): 21 метод с единой ответственностью (preflight validation)

#### 7.1.7. Evidence Loop Для Рефакторинга и Debt-Roadmap

Любой PR или task closeout, который меняет архитектурные границы, public seams,
quality gates, scorecard budgets, DI wiring или topology-рефакторинг, **MUST**
оставлять воспроизводимый evidence block.

Это требование распространяется на roadmap changesets уровня `RF-*`, hotspot
cleanup, compatibility-facade refactors, import-boundary changes и budget
ratchets.

**Минимальный evidence block MUST содержать:**

| Поле                    | Требование                                                                                                             |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Before metrics**      | Конкретные значения до изменения (`cross_layer_group_edges_total=...`, `ruff_error_count=...`, `files_ge_250_loc=...`) |
| **After metrics**       | Те же метрики после изменения                                                                                          |
| **Gate / verification** | Список фактически запущенных quality gates, test files или команд                                                      |
| **Outcome**             | Один из статусов: `improved`, `unchanged`, `worsened`                                                                  |
| **Justification**       | Обязателен для `unchanged` и `worsened`; должен объяснять, почему changeset принят                                     |

**Формат фиксации evidence SHOULD быть таким:**

```markdown
## Architecture verification evidence

- Before metrics: `cross_layer_group_edges_total=267`, `composition -> application=174`
- After metrics: `cross_layer_group_edges_total=287`, `composition -> application=149`
- Gates:
  - `pytest tests/architecture/test_regression_metrics.py -q`
  - `python scripts/engineering/qa/generate_architecture_dependency_map.py --update`
- Outcome: `improved`
```

**Дополнительные правила:**

- `Outcome` **MUST** классифицироваться явно; нельзя оставлять его неявным в тексте summary.
- Если изменение не улучшает целевую метрику, автор **MUST** указать, какая
  вторичная метрика улучшилась или какой риск был снят.
- Если изменение ухудшает метрику, PR **MUST** содержать follow-up issue или
  ratchet-plan до merge.
- Для scorecard/budget changes evidence **MUST** ссылаться на конкретный gate,
  который теперь закрепляет новый baseline.
- Для architecture-refactor PR evidence **SHOULD** опираться на active docs и
  не использовать `docs/99-archive/` как нормативный источник текущего
  состояния.

## Evidence Matrix

Нормативные evidence-поверхности для воспроизводимости и control-plane
diagnostics **MUST** отслеживаться явно, а не оставаться только в narrative
описаниях.

Минимум для reproducibility/doc audits:

- scoring rubric: `docs/04-reference/contracts/reproducibility-scoring-rubric.md`
- operator lifecycle/runbook: `docs/05-operations/control-plane-lifecycle.md`
- architecture policy: текущий `RULES.md`

## Criterion Evidence Index

Каждый criterion-level verdict или score выше нуля **MUST** иметь явную
evidence-ссылку на code/doc/config/test surface. Для control-plane и replay
readiness это включает run-manifest, run-ledger, reproducibility rubric и
операционный lifecycle runbook в `docs/05-operations/control-plane-lifecycle.md`.

### 7.2. Обновление Документации

При обнаружении ложного утверждения **MUST**:

1. Зафиксировать его в текущем review artifact, task report или issue/PR discussion
1. Указать причину, почему утверждение ложно
1. Добавить ссылку на код (`файл:строка`)
1. При необходимости сослаться на `docs/99-archive/refactoring-plan.md` только как на historical context

При реализации задачи **MUST**:

1. Обновить текущий task/report artifact или активную документацию, где утверждение было исправлено
1. Добавить ссылку на коммит или файл
1. Указать дату реализации

### 7.3. Команды Быстрой Верификации

```bash
# Структура компонента
wc -l <path-to-python-file>
grep -c "def \|async def " <path-to-python-file>

# Делегирование (ищем вызовы сервисов)
grep -o "self\.-[a-z-]*\." <path-to-python-file> | sort -u

# Импорты в модуле
grep "^from\|^import" <path-to-python-file> | head -20

# Тесты для компонента
find tests -name "*.py" -exec grep -l "ClassName" {} \;

# Проверка в списке ложных утверждений
grep -B2 -A2 "ComponentName" docs/99-archive/refactoring-plan.md
```

______________________________________________________________________

## 8. Управление Изменениями

Любое backward-incompatible изменение public CLI/API, schema/column или
critical config contract **MUST** включать в том же changeset:

1. явно помеченные migration/breaking-change notes с old -> new behavior;
1. affected consumers и пошаговый adaptation path;
1. version/changelog impact;
1. обновлённые regression tests и active documentation.

Silent breaking changes запрещены. Qodo repository configuration также
**MUST NOT** содержать undocumented keys или unsupported schema/version values;
ключи проверяются по актуальной authoritative Qodo schema/reference.

### 8.1. Контракты Данных (Data Contracts)

- **Реестр Схем**: Gold-схемы публикуются в `docs/04-reference/contracts/gold/{provider}_{entity}_v{major}.{minor}.json` (JSON Schema).
- **Версионирование**: Семантическое версионирование схем: `{provider}_{entity}_v{major}.{minor}`.
  - Minor: добавление nullable полей.
  - Major: удаление/переименование полей, изменение типов.
- **Уведомление о Breaking Change**:
  1. PR с изменением Gold-схемы **MUST** содержать явную impact note и migration strategy в PR/changelog/ADR-контексте.
  1. Generated contract artifacts и parity-check **MUST** быть обновлены вместе с кодом.
  1. Период депрекации: 2 недели до удаления поля.
- **Consumer Tests**: Потребители могут подписаться на `contracts/` и запускать свои тесты при изменениях.

#### 8.1.1. Contract Governance: Canonical Naming Policy (PK Strategy)

Для **публичных Gold контрактов** и соответствующих Pandera схем используются только канонические PK-поля:

- `publication-id` (вместо legacy `document-chembl-id`)
- `target-id` (вместо legacy `target-chembl-id`)
- `molecule-id` (вместо legacy `molecule-chembl-id`)
- `parent-molecule-id` (вместо legacy `parent-molecule-chembl-id`)
- `assay-id` (вместо legacy `assay-chembl-id`)
- `cell-id` (вместо legacy `cell-chembl-id`)

Правила управления:

1. Public contract **MUST** публиковать только canonical field names.
1. Legacy-имена **MAY** поддерживаться только как migration alias на переходный период.
1. Alias-период **MUST** быть ограничен (минимум 1 minor release, удаление в следующем major).
1. Любой PR с изменением PK-имён **MUST** содержать migration strategy и impact assessment в changelog/ADR.

#### 8.1.2. Delta PK Migration Plan (обязательный порядок)

Для Delta-таблиц при переименовании PK применяется фиксированная последовательность:

1. **add new column** — добавить canonical PK-колонку;
1. **backfill from old** — заполнить canonical-колонку из legacy;
1. **dual-write window** — временно писать оба поля (canonical + alias);
1. **drop old in major release** — удалить legacy-поле только в major релизе.

Нарушение порядка рассматривается как contract governance violation (MUST-level).

### 8.2. Rollback Strategy

- **Scope**:
  - **Infrastructure/Code**: Автоматический rollback не входит в текущий Local-Only runtime. Откат выполняется вручную по platform/deployment procedure.
  - **Data DQ**: Ручной анализ и replay. Ошибки качества данных не должны триггерить rollback версии приложения.
- **Manual Rollback**: В текущем Local-Only runtime отдельной команды `bioetl rollback` нет; rollback выполняется через platform-specific deployment procedure или восстановление предыдущего артефакта по runbook.

## 9. Опыт Разработчика (Developer Experience)

### 9.1. Локальная настройка

```bash
uv sync --extra dev --extra tests --extra tracing
uv run python -m scripts.ops setup-plugins
uv run python -m scripts.engineering.dev run-tests cov
uv run ruff check .
uv run ruff format --check .
uv run mypy --config-file pyproject.toml --strict --no-incremental src/bioetl
uv run python -m bioetl run --pipeline chembl_activity --limit 10 --no-cached-bronze
```

### 9.2. Окружение

> **Note: Local-Only Deployment** (см. [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md))

**Текущая реализация (Local-Only):**

- **Storage**: Локальная файловая система (`data/output/bronze`, `data/output/silver`, `data/output/gold`)
- **Locking**: In-memory (`MemoryLock`)
- **Checkpoints**: Локальные файлы (`data/output/checkpoints`)
- **Зависимости**: Python 3.12 baseline; Python 3.12 and 3.13 are the supported runtime versions. `uv` является preferred package/environment manager, `pip` допустим как manual fallback

**Optional local helper tooling (не canonical runtime):**

- reviewed `docker-compose*.yml` surfaces MAY оставаться в репозитории только
  как добровольные локальные helper stacks для Neo4j, monitoring, MCP и
  точечных adjunct tools;
- такие compose файлы MUST NOT трактоваться как supported runtime orchestration
  path для базового development/test execution;
- helper surfaces for Redis, MinIO, Alertmanager и SonarQube считаются
  local-only adjunct tooling/diagnostics, а не обязательной частью ADR-010
  runtime;
- `.env.example` остаётся только шаблоном без секретов для ручного local setup.

______________________________________________________________________

## Приложение А: Источники и Библиотеки

**Структура папок:** `src/bioetl/infrastructure/adapters/{provider}/`

| Источник     | Библиотека                        | Rate Limit                     | Retry Strategy          | Auth Type           | Health Check                                                                  |
| ------------ | --------------------------------- | ------------------------------ | ----------------------- | ------------------- | ----------------------------------------------------------------------------- |
| **ChEMBL**   | `httpx` via `UnifiedHTTPClient`   | 0.1 req/sec (`chembl.yaml`, burst 1) | Exponential backoff     | Public              | `GET /chembl/api/data/status`                                                 |
| **PubChem**  | `pubchempy` via `BaseSyncAdapter` | 5 req/sec                      | 429 -> wait Retry-After | Public              | Lightweight: `GET /rest/pug/compound/cid/2244/property/MolecularFormula/JSON` |
| **UniProt**  | `httpx` via `UnifiedHTTPClient`   | 10 req/sec (100 with API key)  | Exponential backoff     | API Key (optional)  | Search probe query                                                            |
| **OpenAlex** | `httpx` via `UnifiedHTTPClient`   | 10 req/sec                     | 429 -> backoff          | API Key (`BIOETL_OPENALEX_API_KEY`; email is attribution only) | Generic Probe\*                                                               |
| **Semantic** | `httpx` via `UnifiedHTTPClient`   | 0.1 req/sec (1.0 with API key) | Sliding window          | API Key             | Generic Probe\*                                                               |
| **PubMed**   | `httpx` via `UnifiedHTTPClient`   | 3 req/sec (10 with API key)    | 429 -> backoff          | API Key             | Generic Probe\*                                                               |
| **Crossref** | `httpx` via `UnifiedHTTPClient`   | 50 req/sec (polite pool)       | Exponential backoff     | Email               | Generic Probe\*                                                               |

\* **Generic Probe**: Lightweight GET-запрос к базовому endpoint API (e.g., root или `/status`). Если API не предоставляет dedicated health endpoint, использовать минимальный запрос данных с timeout 5 секунд.

> **Каноническая конфигурация rate limits** (burst, batch-size, конкретные числа) находится в
> `configs/providers/{provider}.yaml`. Подробная таблица: [pipeline-configuration.md](../03-guides/pipeline-configuration.md).

### А.1. Формирование URL для ChEMBL API

URL-адреса для ChEMBL формируются в `infrastructure/adapters/chembl/entity_mapper.py`:

| Компонент         | Константа/Метод                              | Значение                                |
| ----------------- | -------------------------------------------- | --------------------------------------- |
| **Base URL**      | `CHEMBL-API-BASE`                            | `https://www.ebi.ac.uk/chembl/api/data` |
| **Status URL**    | `CHEMBL-STATUS-URL`                          | `{BASE}/status`                         |
| **Resource URL**  | `ChemblEntityMapper.get-resource-url()`      | `{BASE}/{resource}`                     |
| **Direct record** | `ChemblEntityMapper.get-direct-record-url()` | `{BASE}/{resource}/{id}`                |

**Маппинг entity → API resource** (`-NON-PUBLICATION-ENTITY-MAPPING`):

| Entity Type        | API Resource             | Primary Key          |
| ------------------ | ------------------------ | -------------------- |
| `activity`         | `activity`               | `activity-id`        |
| `assay`            | `assay`                  | `assay-chembl-id`    |
| `assay-parameters` | `assay`                  | *(composite)*        |
| `cell-line`        | `cell-line`              | `cell-chembl-id`     |
| `compound`         | `molecule`               | `molecule-chembl-id` |
| `compound-record`  | `compound-record`        | `record-id`          |
| `molecule`         | `molecule`               | `molecule-chembl-id` |
| `protein-class`    | `protein-classification` | `protein-class-id`   |
| `publication`      | `document`               | `document-chembl-id` |
| `target`           | `target`                 | `target-chembl-id`   |
| `target-component` | `target-component`       | `component-id`       |
| `tissue`           | `tissue`                 | `tissue-chembl-id`   |

**Query parameters** (формируются в `ChemblAdapter.-build-params()`):

- `format=json` — обязательный (ChEMBL не поддерживает `.json` extension)
- `limit`, `offset` — пагинация (health-aware: уменьшается при деградации)
- `{field}--in=ID1,ID2,...` — фильтрация по списку ID

**Конфигурация**: `configs/providers/chembl.yaml`

**Health Check Endpoints**:

- `GET /health` (Liveness)
- `GET /health/ready` (Readiness: local storage/lock health)

## Приложение B: Политика Зависимостей

- **Pinning**: Базовые зависимости задаются в `pyproject.toml` диапазонами (`>=`, при необходимости с верхней границей), воспроизводимость обеспечивается зафиксированным `uv.lock`.
- **Exact pins**: Допускаются точечные `==` для критичных инструментов при обосновании (например, нестабильные/ломающие релизы).
- **Обновления**: Ежемесячные PR от Dependabot + ручное ревью.
- **Безопасность**: `pip-audit` в CI. Блокировка мержа при CVE severity >= HIGH.

## Приложение C: Error Recovery Playbook (Runbook)

### Уровни Серьезности (Severity Levels)

| Level  | Описание                                         | SLA реакции | SLA восстановления |
| ------ | ------------------------------------------------ | ----------- | ------------------ |
| **P0** | Система недоступна или критичные данные потеряны | 15 мин      | 1 час              |
| **P1** | Падение критичного пайплайна (Core Data)         | 1 час       | 4 часа             |
| **P2** | Падение второстепенного пайплайна                | 8 часов     | 24 часа            |
| **P3** | Warning / DQ аномалии                            | 24 часа     | Next Sprint        |

| Ошибка                 | Симптом                                        | Действие                                                                                                                                               |
| ---------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Auth failure           | `401 Unauthorized` в логах                     | Проверить/обновить `BIOETL-{PROVIDER}-API-KEY`                                                                                                         |
| Rate limit exhausted   | `429` + пик `errors-total{type="recoverable"}` | Уменьшить `requests-per-second` в конфиге                                                                                                              |
| Schema mismatch (Gold) | Pipeline fail + `schema-violations` > 0        | Проверить изменения API; обновить Gold-схему через ADR                                                                                                 |
| Stale checkpoint       | Warning при старте                             | `--resume` для продолжения или удалить файл `data/output/checkpoints/{pipeline-name}.json` для рестарта                                                |
| DQ errors exceed active `hard_fail` | Batch rejected or quarantined according to the active disposition policy | Проверить источник и действующий DQ surface: `configs/base/quality.yaml`, `configs/contracts/**`, inline `pipeline.dq_overrides`, или Silver DQ request |
| Lock timeout           | Alert "Lock expired"                           | Проверить зомби-процессы; определить owner `run-id`; для same-process диагностики использовать `bioetl lock check/release --pipeline ... --run-id ...` |

## Приложение D: Схема Конфигурации Пайплайна

См. [ADR-039](../02-architecture/decisions/ADR-039-unified-entity-config-format.md) для unified entity config format, [ADR-025](../02-architecture/decisions/ADR-025-pipeline-config-unification.md) для исходной унификации конфигурации, [ADR-027](../02-architecture/decisions/ADR-027-dq-rules-externalization.md) для DQ rules и [ADR-028](../02-architecture/decisions/ADR-028-filter-rules-externalization.md) для filter rules.

Начиная с 2026-02-24, все 21 стандартных pipeline используют **unified entity config** формат:

```
configs/entities/{provider}/{entity}.yaml
```

Файл объединяет 5–6 ранее отдельных конфигов в одном YAML с явными секциями.

```yaml
# configs/entities/chembl/activity.yaml
# Unified entity config (ADR-039).
# Combines pipeline, schema, quality, filters, contracts, hash-policy.
version: 1.0.0
provider: chembl
entity: activity

pipeline:
  pipeline_name: chembl_activity
  provider: chembl
  entity_type: activity
  description: Extract biological activity records from ChEMBL API
  business_primary_keys: [activity_id]
  batch_size: 1000
  sink:
    silver:
      mode: merge
    gold:
      enabled: false

schema:
  column_groups:
    - name: system
      fields: [entity_id, content_hash, _source, _index]
    - name: business
      fields: [activity_id, assay_id, molecule_id, standard_value, standard_type, standard_units]
    - name: dq
      pattern: ^_dq_
  silver:
    include_groups: [system, business, dq]
    alias_policy: preserve
  gold:
    include_groups: [system, business]
    exclude_fields: [_dq_*, _index]
    alias_policy: canonical

quality:
  entity_field_validations:
    - field: activity_id
      type: required
      nullable: false
    - field: standard_value
      type: range
      min: 0
      max: 1000000000
      nullable: true
  entity_cross_field_validations:
    - name: value_requires_units
      fields: [standard_value, standard_units]
      condition: conditional_required
      trigger_field: standard_value
      required_field: standard_units
  entity_conditional_validations:
    - name: ic50_range_check
      condition_field: standard_type
      condition_value: IC50
      condition_operator: eq
      then_validations:
        - field: standard_value
          type: range
          min: 0.001
          max: 100000
          nullable: false
  key_nullability:
    - field: activity_id
      key_type: merge
      nullable: false

filters:
  extraction_params:
    standard_type__in: IC50,Ki
  silver_filters:
    required_fields: [activity_id, molecule_id, target_id, standard_value]
  gold_filters:
    required_fields: [standard_type, standard_value, standard_units, target_id]

contracts:
  primary_key: [activity_id]
  merge_keys: [activity_id]
  rename_map: {source: _source}
  hash_exclude: [_dq_warn, _dq_error, _index]

hash_policy:
  hash_policy:
    algorithm: sha256
    include_fields: [activity_id, assay_id, molecule_id, standard_type, standard_value, standard_units]
    exclude_patterns: [^_dq_]
```

Composite pipeline конфиги расположены в `configs/composites/{entity}.yaml`.

## Приложение E: Примеры Schema Evolution

### Minor Change (Обратная совместимость)

Добавление необязательного поля. Не требует пересчета истории.

```json
// Old Schema
{"id": "CHEMBL1", "score": 0.9}

// New Schema
{"id": "CHEMBL1", "score": 0.9, "source": "manual"}
```

### Major Change (Breaking)

Переименование или изменение типа. Требует миграции данных или новой версии таблицы (v2).

```json
// Old Schema
{"id": 123}  // int

// New Schema
{"id": "123"} // string
```

### E.3. Field Deprecation Workflow

**Day 0**: Пометить поле deprecated в схеме

```yaml
fields:
  old-field:
    deprecated: true
    replacement: new-field
```

**Days 1-14**: Dual-write период

- Писать оба поля: `old-field` и `new-field`
- Потребители мигрируют чтение на `new-field`

**Day 15** (после 14-дневного периода): Удаление `old-field`

- Bump major version схемы
- ADR с обоснованием изменения

## 6.4 Политика статусов ADR

Все ADR в `docs/02-architecture/decisions/ADR-*.md` MUST содержать явный статус в одном из разрешённых значений:

- `Accepted` — действующее архитектурное решение, обязательное к применению.
- `Superseded` — решение заменено более новым ADR; это ожидаемая эволюция архитектуры, а не дефект.
- `Deprecated` — решение устарело и находится в фазе вывода без прямой замены.
- `Added` — ADR добавлен в реестр и находится в стадии внедрения/ратификации до перехода в `Accepted`.

Нормализация для quality gate: допускаются расширенные формулировки в заголовке (например, `Accepted (Revised)`), но базовый статус MUST быть одним из четырёх значений выше.

## Приложение F: Реестр Architecture Decision Records (ADR)

Этот appendix остаётся published summary surface, а canonical live ADR registry
и generated status surfaces находятся в
`docs/02-architecture/decisions/README.md` и `docs/02-architecture/adr-registry.md`.
При добавлении новых ADR оба surface MUST оставаться синхронизированными.

| ADR                                                                                   | Название                                   | Статус                                  | Дата       |
| ------------------------------------------------------------------------------------- | ------------------------------------------ | --------------------------------------- | ---------- |
| [ADR-001](../02-architecture/decisions/ADR-001-delta-lake-vs-parquet.md)              | Delta Lake vs Parquet                      | Accepted                                | 2025-05    |
| [ADR-002](../02-architecture/decisions/ADR-002-medallion-architecture.md)             | Medallion Architecture                     | Accepted                                | 2025-05    |
| [ADR-003](../02-architecture/decisions/ADR-003-in-memory-locking-strategy.md)         | In-Memory Locking (MemoryLock)             | Superseded                              | 2025-12    |
| [ADR-004](../02-architecture/decisions/ADR-004-pydantic-vs-dataclasses.md)            | Pydantic vs Dataclasses                    | Accepted                                | 2025-05    |
| [ADR-005](../02-architecture/decisions/ADR-005-composition-layer-separation.md)       | Composition Layer Separation               | Accepted                                | 2025-12    |
| [ADR-006](../02-architecture/decisions/ADR-006-logger-metrics-ports.md)               | Logger and Metrics Ports                   | Accepted                                | 2025-12-18 |
| [ADR-007](../02-architecture/decisions/ADR-007-circuit-breaker-implementation.md)     | Circuit Breaker Implementation             | Accepted                                | 2025-12-22 |
| [ADR-008](../02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md)         | Graceful Shutdown Strategy                 | Superseded                              | 2025-12-22 |
| [ADR-009](../02-architecture/decisions/ADR-009-paginated-fetcher-mixin.md)            | PaginatedFetcherMixin Design               | Accepted                                | 2025-12-22 |
| [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md)              | Local-Only Deployment                      | Accepted                                | 2025-12-23 |
| [ADR-011](../02-architecture/decisions/ADR-011-remove-watermark-mechanism.md)         | Remove Watermark Mechanism                 | Accepted                                | 2025-12-23 |
| [ADR-012](../02-architecture/decisions/ADR-012-storage-clear-contract-and-run-id.md)  | Storage Clear Contract and Run ID          | Accepted                                | 2025-12-23 |
| [ADR-013](../02-architecture/decisions/ADR-013-async-storage-cleanup.md)              | Async Storage Cleanup                      | Accepted                                | 2025-12-24 |
| [ADR-014](../02-architecture/decisions/ADR-014-deterministic-writes.md)               | Deterministic Writes and Retries           | Accepted                                | 2025-12-24 |
| [ADR-015](../02-architecture/decisions/ADR-015-pipeline-services-lifecycle.md)        | Pipeline Services Lifecycle                | Accepted                                | 2025-12-24 |
| [ADR-016](../02-architecture/decisions/ADR-016-error-handling-strategy.md)            | Error Handling Strategy                    | Accepted                                | 2025-12-26 |
| [ADR-017](../02-architecture/decisions/ADR-017-observability-architecture.md)         | Observability Architecture                 | Accepted                                | 2025-12-26 |
| [ADR-018](../02-architecture/decisions/ADR-018-gold-strict-validation.md)             | Gold Strict Validation                     | Accepted                                | 2025-12-26 |
| [ADR-019](../02-architecture/decisions/ADR-019-observability-port-enforcement.md)     | Observability Port Enforcement             | Accepted                                | 2025-12-26 |
| [ADR-020](../02-architecture/decisions/ADR-020-basepipeline-decomposition.md)         | BasePipeline Decomposition                 | Accepted                                | 2025-12-16 |
| [ADR-021](../02-architecture/decisions/ADR-021-ddd-aggregates-adoption.md)            | DDD Aggregates Adoption                    | Accepted                                | 2025-12-29 |
| [ADR-022](../02-architecture/decisions/ADR-022-tracing-noop.md)                       | NoOp Tracing for Local-Only                | Accepted                                | 2025-12-30 |
| [ADR-023](../02-architecture/decisions/ADR-023-entity-type-patterns.md)               | Entity Type Patterns                       | Accepted                                | 2026-01-06 |
| [ADR-024](../02-architecture/decisions/ADR-024-entity-naming-unification.md)          | Entity Naming Unification                  | Accepted                                | 2026-01-06 |
| [ADR-025](../02-architecture/decisions/ADR-025-pipeline-config-unification.md)        | Pipeline Config Unification                | Accepted (partial supersede by ADR-039) | 2026-01-19 |
| [ADR-026](../02-architecture/decisions/ADR-026-composite-pipeline-pattern.md)         | Composite Pipeline Pattern                 | Accepted                                | 2026-01-15 |
| [ADR-027](../02-architecture/decisions/ADR-027-dq-rules-externalization.md)           | DQ Rules Externalization                   | Accepted                                | 2026-01-19 |
| [ADR-028](../02-architecture/decisions/ADR-028-filter-rules-externalization.md)       | Filter Rules Externalization               | Accepted                                | 2026-01-20 |
| [ADR-029](../02-architecture/decisions/ADR-029-output-metadata-unification.md)        | Output Metadata Unification                | Accepted                                | 2026-01-23 |
| [ADR-030](../02-architecture/decisions/ADR-030-publication-pagination-strategy.md)    | Publication Pagination Strategy            | Accepted                                | 2026-01-26 |
| [ADR-031](../02-architecture/decisions/ADR-031-loading-strategy-formalization.md)     | Loading Strategy Formalization             | Accepted                                | 2026-01-26 |
| [ADR-032](../02-architecture/decisions/ADR-032-unified-http-client.md)                | Unified HTTP Client Pattern                | Accepted                                | 2026-01-28 |
| [ADR-033](../02-architecture/decisions/ADR-033-publication-validation-strategy.md)    | Publication Metadata Validation Strategy   | Accepted                                | 2026-02-06 |
| [ADR-034](../02-architecture/decisions/ADR-034-schema-domain-pairs.md)                | Schema↔Domain Configuration Pairs          | Accepted                                | 2026-02-15 |
| [ADR-035](../02-architecture/decisions/ADR-035-json-field-typing-policy.md)           | JSON Field Typing Policy (Silver↔Gold)     | Accepted                                | 2026-02-17 |
| [ADR-036](../02-architecture/decisions/ADR-036-gold-contract-versioning-policy.md)    | Gold Contract Versioning Policy            | Accepted                                | 2026-02-18 |
| [ADR-037](../02-architecture/decisions/ADR-037-canonical-schema-generation.md)        | Canonical Schema Source and Generation     | Accepted                                | 2026-02-18 |
| [ADR-038](../02-architecture/decisions/ADR-038-enum-externalization.md)               | ChEMBL Enum Values Externalization to YAML | Accepted                                | 2026-02-16 |
| [ADR-039](../02-architecture/decisions/ADR-039-unified-entity-config-format.md)       | Unified Entity Configuration Format        | Accepted                                | 2026-02-24 |
| [ADR-040](../02-architecture/decisions/ADR-040-diagram-governance.md)                 | Diagram Governance and Layout Policy       | Accepted                                | 2026-02-25 |
| [ADR-041](../02-architecture/decisions/ADR-041-naming-policy-skills-agents.md)        | Naming Policy for Skills, Agents, Commands | Accepted                                | 2026-03-04 |
| [ADR-042](../02-architecture/decisions/ADR-042-testing-strategy-matrix.md)            | Testing Strategy Matrix & Fixture Gov.     | Accepted                                | 2026-03-09 |
| [ADR-043](../02-architecture/decisions/ADR-043-documentation-knowledge-management.md) | Documentation & Knowledge Management       | Accepted                                | 2026-03-09 |
| [ADR-044](../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)  | Run Manifest and Run Ledger Control Plane  | Accepted                                | 2026-03-24 |
| [ADR-045](../02-architecture/decisions/ADR-045-dq-contract-system.md)                  | Data Quality Contract System               | Accepted                                | 2026-03-26 |
| [ADR-046](../02-architecture/decisions/ADR-046-checkpoint-vs-ledger-resume.md)        | Checkpoint Versus Ledger-Based Resume      | Accepted                                | 2026-05-06 |
| [ADR-047](../02-architecture/decisions/ADR-047-workflow-control-plane.md)             | Workflow Control Plane for Declarative Workflows | Accepted                           | 2026-05-08 |
| [ADR-048](../02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md) | Domain Schema Boundary and Runtime Pandera Compatibility | Accepted | 2026-05-26 |
| [ADR-049](../02-architecture/decisions/ADR-049-context-aware-loc-target-policy.md) | Context-Aware LOC Target Policy | Accepted | 2026-05-26 |
| [ADR-050](../02-architecture/decisions/ADR-050-silver-structural-gold-semantic-filter-boundary.md) | Silver Structural and Gold Semantic Filter Boundary | Accepted | 2026-06-15 |
| [ADR-051](../02-architecture/decisions/ADR-051-quarantine-entry-aggregate-surface.md) | Quarantine Entry Aggregate Surface | Accepted | 2026-07-27 |
| [ADR-052](../02-architecture/decisions/ADR-052-infrastructure-config-package-root-public-api.md) | Infrastructure Config Package-Root as Permanent External Public API | Accepted | 2026-07-28 |
| [ADR-053](../02-architecture/decisions/ADR-053-optional-grafana-scenes-app-shell.md) | Optional Grafana Scenes App Shell as Presentation Adapter | Accepted | 2026-07-28 |
| [ADR-054](../02-architecture/decisions/ADR-054-passport-documentation-projections.md) | Evidence-backed Passport Documentation Projections | Accepted | 2026-07-29 |
| [ADR-055](../02-architecture/decisions/ADR-055-workflow-reconciliation-data-step-ownership.md) | Retain Foreign-key Reconciliation as a Governed Workflow Data Step | Accepted | 2026-07-29 |
| [ADR-056](../02-architecture/decisions/ADR-056-proof-or-stop-lifecycle-control.md) | Proof-or-Stop Lifecycle Control | Accepted | 2026-08-09 |
| [ADR-057](../02-architecture/decisions/ADR-057-deterministic-runtime-config-authority-and-identity.md) | Deterministic Runtime Config Authority and Identity | Accepted | 2026-08-10 |
| [ADR-058](../02-architecture/decisions/ADR-058-layered-port-registries.md) | Layered Port Registries | Accepted | 2026-08-25 |
| [ADR-059](../02-architecture/decisions/ADR-059-package-cohesion-budgets.md) | Package Cohesion Budgets | Accepted | 2026-08-25 |

## История Изменений (Changelog)

- **6.1.11** (2026-08-25): синхронизирован индекс принятых решений с
  ADR-058 (layered port registries) и ADR-059 (shrink-only package cohesion
  budgets).
- **6.1.10** (2026-08-14): добавлен scoped Dashboard Presentation Contract:
  измеримая плотность дополнительных panel groups, typography floors 12pt/14pt
  и запрет area fills вне первого окна; требования связаны с executable
  dashboard/render tests без увеличения quality budgets.
- **6.1.9** (2026-08-10): ADR Registry Governance Sync. Приложение F
  синхронизировано через ADR-057 (deterministic runtime config authority and
  versioned identity); precedence, provider transport SSOT и replay-compatible
  identity versioning закреплены без увеличения exception budgets.
- **6.1.8** (2026-08-09): ADR Registry Governance Sync. Приложение F синхронизировано через ADR-056 (Proof-or-Stop lifecycle control).
- **6.1.7** (2026-07-30): ADR Registry Governance Sync. Приложение F синхронизировано через ADR-055; добавлены ADR-054 (passport documentation projections) и ADR-055 (workflow reconciliation data-step ownership).
- **6.1.6** (2026-07-28): ADR Registry Governance Sync. Приложение F синхронизировано через ADR-053 (optional Grafana Scenes App Shell as presentation adapter; dual-path with provisioned JSON under ADR-010).
- **6.1.5** (2026-07-16): Qodo rules reconciliation. 66 unique Qodo rule IDs
  из broad best-effort semantic extraction нормализованы в 18 project gates;
  усилены secret/config/type/test/determinism/atomic-write/docs/change-control,
  architecture и Silver/Gold validation requirements. Qodo severity сохранена
  как `UNSPECIFIED`, без inference; technical-debt budgets не изменены.
- **6.1.4** (2026-06-25): Governance closure follow-up. Явно закреплены policy guardrails для pipeline IDs (`<provider>_<entity>` как current stable external identifier, конфликтующее legacy wording `<entity>_<source>` запрещено без ADR/migration plan) и для HTTP abstraction naming (`UnifiedHTTPClient` как единственный sanctioned runtime client, `UnifiedAPIClient` допустим только как controlled rename через ADR).
- **5.28** (2026-06-16): ADR Registry Governance Sync. Приложение F и generated ADR registry mirrors синхронизированы через ADR-050; published appendix теперь перечисляет ADR-049/050, а generated registry surfaces явно помечены как derived mirrors с canonical owner в `decisions/README.md`.
- **5.27** (2026-05-26, updated 2026-06-22): Domain Schema Boundary Sync. Добавлен ADR-048 и закреплено, что Pandera/Pandas допустимы в domain только как schema-contract representation под `domain/schemas` и `domain/contracts`; runtime Pandera monkeypatching retired, а retained bootstrap seam теперь выполняет только explicit validation без package import side effects.
- **5.26** (2026-05-15): ADR Governance Sync. Приложение F синхронизировано с ADR-046/047 и теперь явно делегирует canonical live registry в `decisions/README.md` и `adr-registry.md`. Исправлен generated ADR registry status parsing для explicit `Status:` metadata; `mkdocs.yml` синхронизирован с активной `scripts.docs check-links` guardrail surface.
- **5.25** (2026-04-29): Documentation Audit Stop-Loss. Исправлен published readiness endpoint (`/health/ready`), синхронизирован ADR registry с ADR-044/045, а Medallion write-mode terminology закреплена как policy-owned surface в §2.1.1-§2.1.2.
- **5.24** (2026-03-13): Docs Governance Sync. В §6 явно закреплена active-docs модель: `docs/00-05` как source of truth, `docs/99-archive/` как non-normative historical context, и docs guardrails как обязательная проверка для active/generated docs.
- **5.23** (2026-03-02): Dependency Policy Sync. Уточнена политика зависимостей: mixed strategy (`pyproject.toml` с диапазонами + воспроизводимость через `uv.lock`), строгие `==` оставлены как исключение для критичных инструментов.
- **5.22** (2026-02-24): Unified Entity Config. ADR-039 добавлен — Unified Entity Config Format. 21 стандартных pipeline config переведены из legacy pipeline config directory в `configs/entities/`; composite configs перенесены в `configs/composites/`; provider source configs — в `configs/providers/`.
- **5.21** (2026-02-21): Deduplication Policy Implementation.
- **5.20** (2026-02-17): Audit Sync. Future annotations (497→501, 93.8%). Тест-функций (`def test-`): ~9,442; параметризованных кейсов (`pytest --collect-only`): ~11,985. Python-файлов (~1,114→~1,161). Исправлен .importlinter gap (infrastructure→composition). Архивирован orphaned ADR-030. TYPE-002 `Any` justification — 21 инстанс.
- **5.19** (2026-02-16): Documentation Sync. Файлов кода (517→534), future annotations (481→497, 93.1%). ADR-034 (Schema↔Domain Configuration Pairs) добавлен в реестр. Тестов (~7,090→~11,985). Python-файлов (~1,094→~1,114). Синхронизация 00-map.md, CLAUDE.md, 00-overview.md, decisions/README.md.
- **5.18** (2026-02-15): Statistics Update. Обновлены числовые данные по результатам аудита 2026-02-14: файлов кода (499→517), future annotations (468→481), Int→Float coercion occurrences (~34→~88), publication field groups (94→106), LOC для ChemblAdapter (517→975), GoldWriter (593→946), PreflightService (527→818).
- **5.17** (2026-02-03): Chained Dependencies. Добавлена секция §2.9.1 "Dependency Pipelines (Chained Dependencies)" — поддержка `key-source` и `filter-field` для цепочечных зависимостей в composite pipelines. Обновлён ADR-026.
- **5.16** (2026-02-02): ADR Registry Update + Doc Sync. Добавлен ADR-032 в реестр (Приложение F): Unified HTTP Client Pattern. Синхронизация метрик с кодовой базой.
- **5.15** (2026-01-29): Field Group Registry. Добавлена §2.9.4 "Field Group Registry" — семантическая группировка полей для Gold-фильтрации и сортировки колонок. Домен: `FieldGroupRegistry`, `FieldMapping`, `FieldGroupDefinition`. YAML-конфиг: `configs/composites/field_groups/publication.yaml`. Интеграция с `MergeService` для автоматической фильтрации TRASH-полей из Gold.
- **5.14** (2026-01-28): Composite Pipeline Documentation. Добавлена секция §2.9 "Composite Pipelines" с документацией `preserve-all-sources` feature, column groups и merge strategies. Ссылка на ADR-026.
- **5.13** (2026-01-28): ADR Registry Update. Добавлены ADR-029..031 в реестр (Приложение F): Output Metadata Unification, Publication Pagination Strategy, Loading Strategy Formalization.
- **5.12** (2026-01-21): ADR Registry Update. Добавлены ADR-021..028 в реестр (Приложение F). Добавлены inline ссылки на новые ADR в соответствующие секции (§1.1, §2.8, §3.2, App D).
- **5.11** (2026-01-20): Int→Float Coercion Documentation. Добавлена §2.6 "Int→Float Coercion для Nullable Integers" — документация паттерна Gold-схем с `Series[float]` + `coerce=True` для nullable integer полей (~34 occurrences на момент 5.11; актуальное число может отличаться). Это осознанное архитектурное решение для обработки nullable integers в Pandas/Polars.
- **5.10** (2026-01-06): TTL/Heartbeat Values Correction. Исправлены значения Lock TTL (90s) и Heartbeat (30s) в §3.3 для соответствия реализации в `domain/config.py:238,241`. Синхронизация всех документов.
- **5.9** (2026-01-01): TTL/Heartbeat Sync Fix. Добавлены явные значения Lock TTL и Heartbeat в §3.3.
- **5.8** (2025-12-29): TTL/Heartbeat Sync. Добавлены явные значения Lock TTL и Heartbeat в §3.3 "Текущая реализация". Синхронизация с CLAUDE.md §5.
- **5.7** (2025-12-27): Pre-Refactoring Verification Requirement. Добавлено обязательное требование в §7.1: перед предложением рефакторинга MUST сверяться с CLAUDE.md §0 и секцией "УЖЕ РЕАЛИЗОВАНО" в refactoring-plan.md.
- **5.6** (2025-12-27): Anti-False-Claims Protocol (REQ-ARCH-041). Расширена §7 с детальными правилами анализа делегирования (§7.1.6), причинами ложных утверждений (§7.1.5), контрпримерами (ChemblAdapter, GoldWriter, PreflightService). Добавлены конкретные примеры из кодовой базы в §7.1.4.
- **5.5** (2025-12-27): Mandatory Architecture Review Verification Protocol. Добавлена §7 "Протокол Архитектурных Обзоров" с требованием двойной верификации (REQ-ARCH-040). Причина: анализ выявил ~50% ложных утверждений в планах рефакторинга.
- **5.4** (2025-12-25): Architecture Documentation Update. Добавлены §1.1.2 (Health Check Protocol), §2.4.2 (Medallion Clear Policy), §4.4 (Python Standards), §5.3.2 (Async Cleanup). Реестр ADR расширен (011-015). Добавлено ограничение на structlog в application/interfaces (§4.3, тест `test-no-structlog-in-application-interfaces`). Добавлен deterministic mode для retry jitter (§3.1.3).
- **5.3** (2025-12-24): Determinism and Reproducibility (ADR-014). Добавлен §4.3 с правилами детерминизма. Архитектурные тесты для random и datetime.now().
- **5.2** (2025-12-23): Local-Only Deployment (ADR-010). Обновлены §3.3 и §8.2 для MemoryLock. ADR-003 superseded.
- **5.1** (2025-12-22): ADR additions (007-009), ADR index appendix.
- **5.0** (2025-12-15): Production Ready. Final Governance Polish, Circuit Breaker half-open observability, Backfill lock timeouts, Generic Health Probes, Deprecation clarification.
- **4.6** (2025-12-15): Governance & Stability. RFC 2119, Entity ID vs Content Hash, Bronze Lifecycle, Hard Limits, Threat Model. Added Log Schema, Provider Health Matrix, Circuit Breaker details, Backfill Locking, and Deprecation workflows.
- **4.5** (2025-05-20): Final Polish & Governance. Medallion Paths, DQ Levels, Observability, Fencing Tokens, Security IAM.
- **4.4** (2025-05-20): Resilience & Operations. Circuit Breaker, DR Runbooks, Quarantine Ops, Env Isolation.
- **4.3** (2025-05-20): Security & DR. Salted Hashes, RPO/RTO, Heartbeat Locks, Environments, Delta Infrastructure.
- **4.2** (2025-05-20): Delta Lake Strategy, Unified Quarantine Schema, Threshold adjustments.
- **4.1** (2025-05-20): [DEPRECATED] Storage Fixes. (Заменено версией 4.2).
- **4.0** (2025-05-20): Data Contracts, Partitioning, Null Policy, Recovery Playbook.
- **3.0** (2025-05-20): Lineage, Backfill, Concurrency, Graceful Shutdown, Dev Experience.
- **2.0** (2025-05-20): Классификация ошибок, Medallion, Rate limiting, Перевод на русский.
- **1.0** (2025-04-01): Черновик.

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
