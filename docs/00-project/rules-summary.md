______________________________________________________________________

Version: 1.0.2
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-14'

______________________________________________________________________

# Rules Summary

*Синхронизировано с RULES.md v6.1.10 (2026-08-14; ADR-053–057 + architecture stamps)*

> **Note**: Этот документ — выжимка из `docs/00-project/RULES.md`. Канонический источник правил — `RULES.md`.

## Уровни Требований (RFC 2119)

- **MUST** (Обязательно): Нарушение = дефект/блокер релиза.
- **SHOULD** (Рекомендуется): Отклонение требует обоснования в PR.
- **MAY** (Опционально): На усмотрение разработчика.

## Quick Reference

|| Задача                                 | Раздел RULES.md | Инструмент                               |
|| -------------------------------------- | --------------- | ---------------------------------------- |
|| Создать новый пайплайн                 | App D           | YAML config                              |
|| Добавить поле в схему                  | 2.2, App E      | Pydantic model                           |
|| Ошибка в проде (Alert)                 | App C           | Runbook                                  |
|| Удалить битые данные                   | 2.6             | `bioetl quarantine purge --pipeline ...` |
|| Подготовить staging-like local profile | 5.6.1           | Environment isolation                    |
|| Восстановление при аварии              | 5.5             | DR Runbook                               |
|| Откат релиза                           | 7.2             | Rollback Strategy                        |
|| Безопасность                           | 5.4             | Security Policy                          |
|| Forensic retention для таблицы         | 2.1.1, App D    | Config `forensic-retention`              |
|| Backfill с эксклюзивной блокировкой    | 2.4             | Lock Mechanism                           |
|| Deprecation поля                       | 7.1, App E      | Schema Evolution                         |

## 1. Архитектура

- Hexagonal (Ports & Adapters) + DDD.
- Слои: `domain`, `application`, `infrastructure`, `interfaces`, `composition`.
- Контракты через `typing.Protocol` в `domain/ports/`.
- Импорт портов только через фасад: `from bioetl.domain.ports import ...`.
- `domain` слой не делает I/O.
- Dependency direction: `domain` MUST NOT зависеть от `application` или `infrastructure`; `application` и `interfaces` MUST NOT импортировать concrete infrastructure implementations.
- Dependency injection: зависимости MUST передаваться через конструкторы или явные параметры; создание concrete dependencies и service-locator/global-registry lookup вне `composition/` запрещено.
- Factories и wiring принадлежат только composition root.
- Naming: cross-layer ports, application services, factories и adapters MUST использовать проектные суффиксы `*Port`, `*Service`, `*Factory` и `*Adapter`.

## 2. Medallion Architecture

|| Уровень    | Формат       | Валидация               | Retention             | Идемпотентность                                         |
|| ---------- | ------------ | ----------------------- | --------------------- | ------------------------------------------------------- |
|| **Bronze** | JSONL + zstd | Мин./Нет                | 90 дней hot → Archive | Append-only. Path: `bronze/{provider}/{entity}/{date}/` |
|| **Silver** | Delta Lake   | Мягкая (дрейф схемы)    | Постоянно             | **Merge/Upsert**. Raw Parquet **MUST NOT**.             |
|| **Gold**   | Delta Lake   | Строгая (`strict=True`) | Постоянно             | SCD Type 2 или партиции по дате                         |

### Delta Maintenance

- **VACUUM**: Еженедельно, `retention-period=7 days` (MUST)
- **Forensic Retention**: 7 дней (default), 30 дней для Critical tables
- Для `mode: scd2` обязателен явный `scd_config` в entity config.

## 3. Обработка Ошибок

|| Тип          | Поведение             | Пример                             |
|| ------------ | --------------------- | ---------------------------------- |
|| Critical     | Падение пайплайна     | Auth failure, Gold schema mismatch |
|| Recoverable  | Retry N раз (Backoff) | 429, 502/504, сетевой сбой         |
|| Data Quality | Остановить write или направить в `common.quarantine` | Невалидный SMILES |

### DQ Thresholds

- Soft: >5% DQ errors → Warning
- Hard: >20% → Fail Batch
- Quarantine: единая таблица `common.quarantine`, retention 30 дней.
- Невалидные Silver-строки **MUST NOT** молча отбрасываться: результат
  validation должен остановить write или явно направить строки в
  `common.quarantine`.

### Circuit Breaker

|| Параметр      | Значение                                       |
|| ------------- | ---------------------------------------------- |
|| Trigger       | 5 consecutive errors                           |
|| Open Duration | 5 минут                                        |
|| Recovery      | Half-Open → 1 пробный запрос                   |
|| Metrics       | `bioetl_circuit_breaker_state` (0/1/2), `bioetl_circuit_breaker_trips_total` |

## 4. Блокировки (Local-Only)

|| Параметр     | Значение                       |
|| ------------ | ------------------------------ |
|| Механизм     | `MemoryLock` (in-process)      |
|| TTL          | `heartbeat-interval * 3` = 90s |
|| Heartbeat    | 30s                            |
|| Max Duration | 4 часа                         |

**Invariant**: Потеря блокировки = Потеря права на запись.

- Distributed locks (`RedisLockAdapter`) запрещены (ADR-010 Local-Only).
- Для `backfill/rebuild` используется эксклюзивный lock-key (`:exclusive`).

## 5. Операции

### Secrets

- Источник: `os.environ`
- Формат: `BIOETL_{PROVIDER}_{KEY}`
- **Хардкод секретов MUST NOT** во всех tracked code/docs/config/test/log surfaces.
- Secret-bearing values и full environment/config objects **MUST NOT**
  попадать в logs или published artifacts.
- Файлы `.env`/`.env.*` в git **MUST NOT**; любые операции над ними требуют
  explicit per-task user approval.

### Disaster Recovery

|| Параметр       | Значение                |
|| -------------- | ----------------------- |
|| RPO            | 24 часа                 |
|| RTO            | 4 часа                  |
|| Restore drills | **SHOULD** периодически |

### Graceful Shutdown (SIGTERM/SIGINT)

1. Прекратить fetch новых записей
1. Дождаться завершения текущего батча
1. Сохранить чекпоинт
1. Выйти с кодом 0

## 6. Код и Качество

- PEP8, ruff, mypy (`--strict`)
- Логирование через `LoggerPort`; `application`/`interfaces` не импортируют `structlog` напрямую.
- `print()` запрещён.
- Тесты: Unit, Integration (VCR.py), E2E. Coverage ≥85%
- Детерминизм: без `random` в writers, timestamp только из application context.

### Architecture enforcement (quick reference → RULES.md §1)

- **Inward dependencies:** `domain` MUST NOT depend on `application`/`infrastructure`;
  `application`/`interfaces` MUST NOT import concrete infrastructure implementations.
- **DI:** dependencies via constructors or explicit parameters only.
- **Composition-only wiring:** factories and concrete creation only in `composition/`;
  no service-locator / global-registry lookup outside composition.
- **Role suffixes:** `*Port`, `*Service`, `*Factory`, `*Adapter` for corresponding roles.
- Full normative text: `docs/00-project/RULES.md` (not redefined here).

### Medallion write validation (quick reference → RULES.md §2.1)

- Silver/Gold **MUST** be Delta Lake (raw Parquet forbidden for those layers).
- Exact final DataFrame **MUST** pass Pandera validation after last transform and
  immediately before write; any post-validation transform requires re-validation.
- **Silver:** schema, nullability, types, applicable DQ/business constraints;
  invalid rows stop write or go to quarantine (result MUST NOT be ignored).
- **Gold:** fail-closed strict schema (`strict=True`); `SchemaError`/`SchemaErrors`
  MUST NOT be swallowed before write.

### Qodo-reconciled change-set gates

- 66 unique Qodo IDs нормализованы в 18 project gates в `RULES.md` §4.5;
  extraction best-effort, Qodo severity остаётся `UNSPECIFIED`.
- Public interfaces полностью типизированы; `Any` — только documented narrow
  boundary.
- Persisted outputs имеют stable ordering, canonical serialization и UTC;
  artifacts записываются через temporary file + `os.replace()`.
- Behavior changes требуют regression tests; assertions нельзя ослаблять ради
  прохождения suite; test time/random/network должны контролироваться.
- Contributor-facing и breaking CLI/API/schema/config changes синхронно
  обновляют docs, migration notes и changelog/version impact.
- При изменении `src/bioetl/**/*.py` обновляется module coverage inventory hash.
- Silver/Gold — Delta Lake; exact final DataFrame проходит Pandera validation
  schema, nullability, types и DQ/business constraints непосредственно перед write;
  невалидные данные останавливают запись или попадают в quarantine, Gold strict/fail-closed.
- Technical-debt budgets, quality thresholds и exclusions нельзя ослаблять.
- Architecture enforcement: inward dependency direction (domain не зависит от
  application/infrastructure), constructor/explicit-parameter DI, composition-only
  wiring (factories только в composition/), no service locator/global-registry lookup,
  role suffixes (*Port, *Service, *Factory, *Adapter).

## 7. Anti-Patterns (MUST NOT)

- Импорт `infrastructure` в `domain` или `application`
- Создание зависимостей внутри классов
- Sentinel values (`-1`, `"N/A"`)
- Блокирующий I/O в async
- Хардкод секретов
- `print()` для логирования
- Внедрение multi-instance deployment и межпроцессной lock-координации при текущем Local-Only стандарте

## TL;DR

1. RFC 2119: MUST = блокер, SHOULD = обоснование в PR, MAY = опционально.
1. Medallion: Bronze (JSONL) → Silver (Delta Lake, merge) → Gold (strict).
1. Quarantine: `common.quarantine`, retention 30 дней, sentinel values запрещены.
1. Locks: только `MemoryLock` (local), TTL 90s, Heartbeat 30s, Max 4h, Redis lock запрещён.
1. DR: RPO 24h, RTO 4h, периодические restore drills.
1. Schema Evolution: 14-дневный deprecation period, dual-write.
1. Coverage ≥85%, `mypy --strict`, deterministic writes.

______________________________________________________________________

*Полная версия: [RULES.md](RULES.md)*
