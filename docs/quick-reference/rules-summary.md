# Rules Summary

*Автоматически сгенерировано из RULES.md v5.10 (2026-01-06)*

> **Note**: Этот документ — выжимка из `docs/RULES.md`. Канонический источник правил — `RULES.md`.

## Уровни Требований (RFC 2119)

- **MUST** (Обязательно): Нарушение = дефект/блокер релиза.
- **SHOULD** (Рекомендуется): Отклонение требует обоснования в PR.
- **MAY** (Опционально): На усмотрение разработчика.

## Quick Reference

| Задача                              | Раздел RULES.md | Инструмент                  |
|-------------------------------------|-----------------|-----------------------------|
| Создать новый пайплайн              | App D           | YAML config                 |
| Добавить поле в схему               | §2.2, App E     | Pydantic model              |
| Ошибка в проде (Alert)              | App C           | Runbook                     |
| Удалить битые данные                | §2.6            | `make quarantine-purge`     |
| Развернуть на Staging               | §5.6.1          | CI/CD                       |
| Восстановление при аварии           | §5.5            | DR Runbook                  |
| Откат релиза                        | §7.2            | Rollback Strategy           |
| Безопасность                        | §5.4            | Security Policy             |
| Forensic retention для таблицы      | §2.1.1, App D   | Config `forensic_retention` |
| Backfill с эксклюзивной блокировкой | §2.4            | Lock Mechanism              |
| Deprecation поля                    | §7.1, App E     | Schema Evolution            |

## 1. Архитектура

- Hexagonal (Ports & Adapters) + DDD.
- Слои: `domain`, `application`, `infrastructure`, `interfaces`, `composition`.
- Контракты через `typing.Protocol` в `domain/ports/`.

## 2. Medallion Architecture

| Уровень    | Формат        | Валидация               | Retention             | Идемпотентность                                                          |
|------------|---------------|-------------------------|-----------------------|--------------------------------------------------------------------------|
| **Bronze** | JSONL + zstd  | Мин./Нет                | 90 дней hot → Archive | Append-only. Path: `bronze/{format_version}/{provider}/{entity}/{date}/` |
| **Silver** | Delta Lake    | Мягкая (дрейф схемы)    | Постоянно             | **Merge/Upsert**. Raw Parquet **MUST NOT**.                              |
| **Gold**   | Delta/Parquet | Строгая (`strict=True`) | Постоянно             | SCD Type 2 или партиции по дате                                          |

### Delta Maintenance

- **VACUUM**: Еженедельно, `retention_period=7 days` (MUST)
- **Forensic Retention**: 7 дней (default), 30 дней для Critical tables

## 3. Обработка Ошибок

| Тип          | Поведение             | Пример                             |
|--------------|-----------------------|------------------------------------|
| Critical     | Падение пайплайна     | Auth failure, Gold schema mismatch |
| Recoverable  | Retry N раз (Backoff) | 429, 502/504, сетевой сбой         |
| Data Quality | Лог + Пропуск записи  | Невалидный SMILES                  |

### DQ Thresholds

- Soft: >5% DQ errors → Warning
- Hard: >20% → Fail Batch

### Circuit Breaker

| Параметр      | Значение                                       |
|---------------|------------------------------------------------|
| Trigger       | 5 consecutive errors                           |
| Open Duration | 5 минут                                        |
| Recovery      | Half-Open → 1 пробный запрос                   |
| Metrics       | `circuit_breaker_state` (0/1/2), `trips_total` |

## 4. Блокировки (Local-Only)

| Параметр      | Значение                                 |
|---------------|------------------------------------------|
| Механизм      | `MemoryLock` (in-process)                |
| TTL           | `heartbeat_interval * 3` = 90s           |
| Heartbeat     | 30s                                      |
| Max Duration  | 4 часа                                   |

**Invariant**: Потеря блокировки = Потеря права на запись.

## 5. Операции

### Secrets

- Источник: `os.environ`
- Формат: `BIOETL_{PROVIDER}_{KEY}`
- **Хардкод MUST NOT. Файлы .env в git MUST NOT.**

### Disaster Recovery

| Параметр  | Значение            |
|-----------|---------------------|
| RPO       | 24 часа             |
| RTO       | 4 часа              |
| Game Days | **SHOULD** ежегодно |

### Graceful Shutdown (SIGTERM/SIGINT)

1. Прекратить fetch новых записей
2. Дождаться завершения текущего батча
3. Сохранить чекпоинт
4. Выйти с кодом 0

## 6. Код и Качество

- PEP8, ruff, mypy (strict)
- Логирование: `UnifiedLogger`. **print() MUST NOT**
- Тесты: Unit, Integration (VCR.py), E2E. Coverage ≥80%
- Zero-sum class count при дублировании

## 7. Anti-Patterns (MUST NOT)

- Импорт `infrastructure` в `domain` или `application`
- Создание зависимостей внутри классов
- Sentinel values (`-1`, `"N/A"`)
- Блокирующий I/O в async
- Хардкод секретов
- `print()` для логирования

## TL;DR

1. RFC 2119: MUST = блокер, SHOULD = обоснование в PR, MAY = опционально.
2. Medallion: Bronze (JSONL) → Silver (Delta Lake, merge) → Gold (strict).
3. Quarantine: `common.quarantine`, retention 30 дней, sentinel values запрещены.
4. Locks: MemoryLock (local), TTL 90s, Heartbeat 30s, Max 4h.
5. DR: RPO 24h, RTO 4h, Game Days ежегодно.
6. Schema Evolution: 14-дневный deprecation period, dual-write.
7. Coverage ≥80%, mypy --strict, zero-sum class count.

---

*Полная версия: [docs/RULES.md](../RULES.md)*
