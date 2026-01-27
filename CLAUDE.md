# CLAUDE.md

Справочник для Claude Code при работе с репозиторием BioETL.

*Синхронизировано с RULES.md v5.12 (2026-01-27) | Версия: 7.0.0*

---

## TL;DR — Быстрый Старт

```bash
./dev_setup.sh          # Автоматическая настройка (рекомендуется)
make lint && make test  # Проверка перед работой
```

**Ключевые ресурсы:**
- `docs/RULES.md` — **Конституция проекта** (единственный источник истины)
- `AGENT.md` — Персона и workflow для агента
- `docs/archived/refactoring-plan.md` — Реестр ложных утверждений

---

## 1. Протокол Обязательной Верификации

> **КРИТИЧЕСКИ ВАЖНО**: Анализ выявил ~50% ложных утверждений в планах рефакторинга.
> **НИКОГДА** не утверждай о компоненте без верификации кодом.

### 1.1. Чек-лист Перед Любым Утверждением

| Шаг | Действие |
|-----|----------|
| 1 | Проверить `archived/refactoring-plan.md` → "ЛОЖНЫЕ УТВЕРЖДЕНИЯ" |
| 2 | Прочитать целевой файл (Read tool) |
| 3 | Измерить размер: `wc -l`, `grep -c "def "` |
| 4 | Проверить делегирование: `grep -n "self\._.*\."` |

### 1.2. Формат Верифицированного Утверждения

**❌ НЕ делай так:**
> "bootstrap_pipeline смешивает ответственности"

**✅ Делай так:**
> "bootstrap_pipeline (`bootstrap.py:68-167`, 100 строк) делегирует `bootstrap_observability()` (строка 108), `FilterConfigBuilder.build()` (строка 139). **Вывод**: Уже декомпозирован."

---

## 2. Архитектура

> **Полная документация**: `docs/RULES.md` §1

```
src/bioetl/
├── domain/          # Чистая логика, Protocols. БЕЗ I/O.
├── application/     # Пайплайны, Use Cases
├── composition/     # DI-контейнер, bootstrap
├── infrastructure/  # Адаптеры (HTTP, storage)
└── interfaces/      # CLI
```

**Матрица импортов**: `domain` ← `application` ← `composition` → `infrastructure`
**Нарушение = Блокер PR**

---

## 3. Реестр Ложных Утверждений

> Эти утверждения делаются ошибочно. **Проверяй код!**

| Компонент | ❌ Ложное | ✅ Реальность |
|-----------|----------|---------------|
| **PipelineRunner** | "God object" | 186 строк, делегирует через `RunnerServices` |
| **bootstrap_pipeline** | "Смешивает ответственности" | Делегирует фабрикам |
| **ChEMBL Adapter** | "Монолит" | Делегирует: `EntityMapper`, `ErrorClassifier`, `AdapterMetrics` |
| **GoldWriter** | "Монолит 593 LOC" | Делегирует: `CsvExporter`, `AuditPort` |
| **CLI подтверждения** | "Бизнес-логика в interfaces" | Законная ответственность UI |
| **MemoryLock** | "Нужен Redis" | Достаточен для local-only дизайна |
| **MemoryMonitor** | "Баг — возвращает нули" | Graceful degradation (50% estimate) |
| **DQ метрики** | "Не реализованы" | `postrun_service.py:158-163` |
| **Coverage gate** | "Нет в CI" | `Makefile:63` (`--cov-fail-under=85`) |
| **Email в config** | "PII требует хэширования" | Технический ID для NCBI API |

**Полный список**: `docs/archived/refactoring-plan.md`

---

## 4. Паттерны — НЕ Нарушения

1. **Optional parameters с defaults** — валидный DI паттерн
2. **NoOp implementations** — Null Object Pattern
3. **Подтверждения в CLI** — ответственность interfaces слоя
4. **Большой файл с делегированием** — размер ≠ god object
5. **Int→Float в Gold-схемах** — паттерн для nullable integers
6. **Click (не Typer)** — осознанный выбор

### Критерии "монолита" (ВСЕ должны выполняться):
- 500+ строк
- Мало делегирования (< 3 вызовов `self._component.method()`)
- Много публичных методов с разной ответственностью
- Низкая когезия

---

## 5. Medallion и Ошибки

> **Полная документация**: `docs/RULES.md` §2-3

| Слой | Формат | Стратегия |
|------|--------|-----------|
| Bronze | JSONL + zstd | append-only |
| Silver | Delta Lake | merge по `content_hash` |
| Gold | Delta/Parquet | SCD2 или overwrite |

**Ошибки**: Critical (падение) → Recoverable (retry) → DQ (лог + пропуск)
**DQ пороги**: >5% warning, >20% fail batch
**Circuit Breaker**: 5 errors → Open 5 мин ([ADR-007])

---

## 6. Блокировки

| Параметр | Значение |
|----------|----------|
| Механизм | `MemoryLock` (in-memory) |
| TTL | 90s |
| Heartbeat | 30s |

**Почему НЕ нужен Redis**: Local-only дизайн ([ADR-010])

---

## 7. Тестирование

> **Полная документация**: `docs/RULES.md` §4.2

```bash
make test        # Все тесты (~5277)
make test-unit   # Только unit
make arch-test   # Архитектурные тесты
```

**Покрытие**: ≥85% | **VCR.py**: обязательно для HTTP

---

## 8. Ключевые Файлы

| Артефакт | Путь |
|----------|------|
| Domain Ports | `src/bioetl/domain/ports/` |
| Adapters | `src/bioetl/infrastructure/adapters/{provider}/` |
| Bootstrap | `src/bioetl/composition/bootstrap.py` |
| ADR (31) | `docs/02-architecture/decisions/` |

---

## 9. Anti-Patterns

- ❌ Импорт `infrastructure` в `domain`/`application`
- ❌ Создание зависимостей внутри классов
- ❌ Sentinel values (`-1`, `"N/A"`) → `None`
- ❌ HTTP без VCR-кассет
- ❌ Утверждения без верификации кодом

**Перед коммитом**: `make lint && make test`

---

## 10. Диагностика

| Ошибка | Решение |
|--------|---------|
| `ImportError: cannot import from domain` | Проверь матрицу импортов |
| `RuntimeError: Event loop is closed` | `run_in_executor` |
| Тесты падают в CI | Запиши VCR-кассету |
| Неясности в задаче | **СПРОСИ ПОЛЬЗОВАТЕЛЯ** |

---

## 11. Документация

| Документ | Описание |
|----------|----------|
| `docs/RULES.md` | **Конституция** — единственный источник истины |
| `AGENT.md` | Персона, workflow |
| `.claude/PROJECT_CONTEXT.md` | Компактный контекст |
| `docs/02-architecture/decisions/` | ADR (001-031) |

> При противоречиях приоритет имеет `docs/RULES.md`.

---

*Строй надёжно. Документируй честно. Спрашивай смело.*
