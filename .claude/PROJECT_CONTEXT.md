# BioETL: Компактный Контекст для Claude

*Синхронизировано с RULES.md v5.18 (2026-02-03)*

> **Это сокращённая версия.** Полная документация:
> - `docs/00-project/RULES.md` — **Единственный источник истины** для архитектурных правил
> - `docs/00-project/agents/CLAUDE.md` — Протокол верификации и архитектурные пояснения
> - `docs/00-project/agents/AGENT.md` — Персона, workflow и инструкции для агента

---

## Быстрый Старт

```bash
make lint && make test   # Проверка перед работой
make install             # Установка зависимостей
```

---

## 1. Архитектура

> **Полная документация**: См. `docs/00-project/RULES.md` §1 и `docs/00-project/agents/CLAUDE.md` §2

```
src/bioetl/
├── domain/          # Чистая логика, Protocols (Ports). БЕЗ I/O.
├── application/     # Пайплайны, Use Cases, оркестрация
├── composition/     # Composition Root (DI-контейнер, factories)
├── infrastructure/  # Адаптеры (HTTP, storage)
└── interfaces/      # CLI
```

**Ключевые ограничения:**
- Матрица импортов: `domain` ← `application` ← `composition` → `infrastructure`
- **Нарушение = Блокер PR**
- DI: Зависимости в конструктор. `composition/bootstrap/` — единственное место сборки

> **⚠️ Протокол верификации**: Перед утверждениями о компонентах проверяй код!
> См. `docs/00-project/agents/CLAUDE.md` §0 и §2.3 для списка частых ложных выводов.

---

## 2. Medallion Architecture

> **Полная документация**: См. `docs/RULES.md` §2

- **Bronze**: JSONL + zstd, append-only, 90d retention
- **Silver**: Delta Lake, merge/upsert по `content_hash`, ACID
- **Gold**: Delta/Parquet, SCD Type 2 или партиции

**Content Hash**: `sha256(provider + canonical_json(record))`
**DQ Пороги**: >5% warning, >20% fail batch

---

## 3. Обработка Ошибок и Блокировки

> **Полная документация**: См. `docs/RULES.md` §3

| Тип | Поведение |
|-----|-----------|
| **Critical** | Падение пайплайна |
| **Recoverable** | Retry с backoff |
| **Data Quality** | Лог + пропуск |

**Circuit Breaker**: 5 errors → Open 5 мин ([ADR-007](docs/02-architecture/decisions/ADR-007-circuit-breaker-implementation.md))
**Блокировки**: `MemoryLock` (Local-Only, [ADR-010](docs/02-architecture/decisions/ADR-010-local-only-deployment.md))

---

## 4. Тестирование

> **Полная документация**: См. `docs/RULES.md` §4.2

| Уровень | Директория |
|---------|------------|
| Unit | `tests/unit/` |
| Integration | `tests/integration/` (VCR.py) |
| Architecture | `tests/architecture/` |

**Цель покрытия**: ≥85% | **Команды**: `make test`, `make arch-test`

---

## 5. Ключевые Файлы

| Артефакт | Путь |
|----------|------|
| Domain Ports | `src/bioetl/domain/ports/` |
| Adapters | `src/bioetl/infrastructure/adapters/{provider}/` |
| Pipelines | `src/bioetl/application/pipelines/` |
| Bootstrap | `src/bioetl/composition/bootstrap/` |
| Configs | `configs/pipelines/{provider}/{entity}.yaml` |
| ADR | `docs/02-architecture/decisions/` |

---

## 6. Anti-Patterns (Критичные)

- ❌ Импорт `infrastructure` в `domain`/`application`
- ❌ Создание зависимостей внутри классов
- ❌ Sentinel values (`-1`, `"N/A"`) → `None`
- ❌ HTTP без VCR-кассет

---

## 7. Диагностика

| Ошибка | Решение |
|--------|---------|
| `ImportError: cannot import from domain` | Проверь матрицу импортов (`RULES.md` §1.1) |
| `RuntimeError: Event loop is closed` | `run_in_executor` |
| Тесты падают в CI | Запиши VCR-кассету |
| Неясности в задаче | **СПРОСИ ПОЛЬЗОВАТЕЛЯ** |

---

## 8. Приоритеты при Разработке

1. **Безопасность**: Секреты, PII
2. **Надёжность**: Lock invariants, graceful shutdown
3. **Observability**: Structured logs, metrics
4. **Поддерживаемость**: Type safety, testing

---

*Строй надёжно. Документируй честно. Спрашивай смело.*
