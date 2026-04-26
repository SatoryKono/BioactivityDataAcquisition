______________________________________________________________________

Version: 1.0.0
Status: Accepted (Revised 2025-12-23, see also ADR-010)
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-003: In-Memory Locking Strategy (MemoryLock)

**Date:** 2025-05-20
**Status:** Accepted (Revised 2025-12-23, see also ADR-010)
**Last updated:** 2026-01-02
**Decision makers:** @BioETL-Team
**Superseded by:** [ADR-010](ADR-010-local-only-deployment.md) (local-only locking scope and deployment posture)
**Related:** [ADR-010: Local-Only Deployment](ADR-010-local-only-deployment.md)

## Context

Система требует механизм блокировок для предотвращения одновременного запуска одного пайплайна (например, `chembl_activity`). Это защищает от race conditions, повреждения данных и избыточных API-вызовов.

### Исходное решение (Superseded)

Изначально (2025-05-20) было принято решение использовать **Redis** для распределённых блокировок:

- `SETNX` для атомарного захвата
- TTL для автоматического освобождения
- Heartbeat для продления блокировки

### Причины отказа от Redis

Анализ реальных сценариев использования выявил:

1. **Избыточность**: Проект используется для локальной разработки и исследований — распределённые блокировки не нужны
1. **Усложнение**: Redis требует Docker Compose, конфигурации, мониторинга
1. **Замедление разработки**: Новым разработчикам нужно настраивать внешние сервисы
1. **Single Instance by Design**: Система спроектирована как однопроцессное приложение

## Decision

**ОТКАЗ ОТ REDIS**. Использование **MemoryLock** для всех блокировок в рамках Local-Only архитектуры.

### Strict Single Instance Constraint

- **ЗАПРЕЩЕНО** запускать несколько экземпляров одного пайплайна одновременно
- **ЗАПРЕЩЕНО** горизонтальное масштабирование (Horizontal Scaling)
- **ЗАПРЕЩЕНО** использование Redis Lock и распределённых блокировок
- Система полагается на эксклюзивный доступ к файловой системе

## Justification

### 1. Достаточность MemoryLock

MemoryLock полностью реализует `LockPort` и покрывает все сценарии локального запуска:

| Функционал               | Реализация                                  | Файл:строки              |
| ------------------------ | ------------------------------------------- | ------------------------ |
| **Атомарный захват**     | `acquire()` с asyncio.Lock                  | `memory_lock.py:66-130`  |
| **TTL-based expiration** | `_ttl_checker_loop()` — фоновая задача      | `memory_lock.py:43-64`   |
| **Heartbeat**            | `heartbeat()` — продлевает TTL              | `memory_lock.py:176-204` |
| **Safety Guard**         | `validate_owner()` — проверка перед записью | `memory_lock.py:206-238` |
| **Graceful Shutdown**    | `aclose()` — освобождение всех блокировок   | `memory_lock.py:240-256` |

### 2. Упрощение стека

| Было (Redis)           | Стало (MemoryLock)     |
| ---------------------- | ---------------------- |
| `redis`, `aioredis`    | Нет зависимостей       |
| Docker Compose         | Python venv только     |
| `fakeredis` для тестов | In-memory по умолчанию |
| Конфигурация Redis URL | Нет конфигурации       |
| Мониторинг Redis       | Нет внешних сервисов   |

### 3. Конфигурация по умолчанию

Из `PipelineSettings` (`config.py`):

- `heartbeat_interval = 30s`
- `effective_lock_ttl = heartbeat_interval * 3 = 90s`
- TTL check interval = 1s

## Implementation

```python
# Инициализация
lock = MemoryLock()

# Захват блокировки
await lock.acquire(
    key="pipeline:chembl_activity", owner_id=run_id, ttl=90, exclusive=True
)

# Heartbeat в пайплайне (каждые 30s)
await lock.heartbeat(key="pipeline:chembl_activity", owner_id=run_id)

# Safety Guard перед записью
if not await lock.validate_owner(key="pipeline:chembl_activity", owner_id=run_id):
    raise LockNotHeldError("Lock lost during processing")

# Освобождение
await lock.release(key="pipeline:chembl_activity", owner_id=run_id)

# Graceful Shutdown
await lock.aclose()
```

### Lock Keys Convention

| Тип запуска      | Key формат                           |
| ---------------- | ------------------------------------ |
| Incremental      | `lock:{provider}_{entity}`           |
| Backfill/Rebuild | `lock:{provider}_{entity}:exclusive` |

## Consequences

### Positive

1. **Простота**: Нет внешних зависимостей и конфигурации
1. **Быстрый старт**: `make install && make test` — всё работает
1. **Тестируемость**: Unit тесты без моков внешних сервисов
1. **Портативность**: Работает на любой машине с Python 3.11+

### Negative

1. **Только один процесс**: MemoryLock не защищает от межпроцессных гонок
1. **Нет распределённости**: Невозможен запуск на нескольких машинах

### Mitigation

Ограничения **by design** — это не недостатки, а сознательный выбор:

- Система спроектирована как Single Instance Application
- Порты (Protocols) сохранены для потенциального расширения
- При необходимости распределённого запуска потребуется ревизия ADR-010

## Alternatives Considered (Historical)

### Redis (Rejected)

**Причины выбора (2025-05):**

- Атомарные операции `SETNX`
- Встроенный TTL
- Подготовка к облачному развёртыванию

**Причины отказа (2025-12):**

- Избыточная сложность для Local-Only сценариев
- Дополнительные зависимости (redis, aioredis, fakeredis)
- Требует Docker/managed service
- Облачное развёртывание не планируется

### Database Locks (Not Considered)

Не рассматривались, так как проект не использует SQL базу данных.

### File-based Locks (Not Chosen)

Рассматривались, но отвергнуты:

- Сложнее в реализации кросс-платформенно
- Проблемы с stale locks при crash
- MemoryLock проще и достаточен для single-instance

## References

- [ADR-010](ADR-010-local-only-deployment.md): Local-Only Deployment — определяет Local-Only стратегию (Updated: 2025-12-23)
- [ADR-007](ADR-007-circuit-breaker-implementation.md): Circuit Breaker — комплементарный паттерн устойчивости (Updated: 2025-12-22)
- [ADR-008](ADR-008-graceful-shutdown-strategy.md): Graceful Shutdown — освобождение блокировок при shutdown (Updated: 2025-12-22)

## Rollout

При обновлении с версий, использовавших Redis:

1. Удалить `docker-compose.yml` (секция redis)
1. Удалить переменные окружения `REDIS-*`
1. Удалить зависимости: `pip uninstall redis aioredis fakeredis`
1. Обновить код: заменить `RedisLock` на `MemoryLock`

## Compliance

| Control      | Requirement                                                                | Status     | Evidence                                          |
| ------------ | -------------------------------------------------------------------------- | ---------- | ------------------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass`     | `ADR-003-in-memory-locking-strategy.md`           |
| Status       | ADR status MUST be explicit and consistent                                 | `pass`     | `Accepted (Revised 2025-12-23, see also ADR-010)` |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `declared` | `metadata block`                                  |
| Verification | Implementation and validation expectations MUST be documented              | `pass`     | `Verification / Acceptance Criteria`              |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass`     | `References`                                      |

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
