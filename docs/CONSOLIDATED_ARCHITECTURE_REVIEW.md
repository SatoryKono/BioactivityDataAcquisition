# [ARCHIVED] Консолидированный Архитектурный Обзор BioETL

> **⚠️ ARCHIVED**: Этот документ устарел. Актуальная версия: `docs/08-consolidated-refactoring-plan.md`
> **Причина архивации**: Консолидирован в единый план рефакторинга (2025-12-27)

*Версия: 2.0 | Дата: 2025-12-27 | Обновлено: добавлена верификация 4 планов рефакторинга*
*Метод: Двойная верификация согласно `CLAUDE.md` §0 и `docs/REFACTORING_PLAN.md` (REQ-ARCH-040)*

> **ИСТОЧНИКИ**:
>
> **Обзор v1 (4 плана из запроса 2025-12-27):**
> 1. Архитектурный обзор (inline) — Score 7.75
> 2. `docs/06-reviews/01-architecture-review-2025-12-27.md` — Score 8.29
> 3. `docs/ARCHITECTURE_REVIEW_2025-12-27-02.md` — Score 8.05
> 4. Архитектурный обзор (inline) — Score 7.59
>
> **Обзор v0 (предыдущий анализ):**
> - 4 плана с оценками 7.90-8.26

---

## 1. Исполнительное Резюме

| Показатель | Значение |
|------------|----------|
| **Консолидированный балл** | **8.10 / 10** |
| **Статус зрелости** | Production-ready с точечными улучшениями |
| **Критических блокеров** | 0 |
| **Верифицированных проблем** | 4 |
| **Ложных утверждений (исключены)** | 5 |

---

## 2. Верификация Утверждений из 4 Планов

### 2.1. ✅ ПОДТВЕРЖДЁННЫЕ ПРОБЛЕМЫ (требуют работы)

| # | Проблема | Верификация | Источники |
|---|----------|-------------|-----------|
| **P1** | **GoldWriter не получает ingestion_ts** | `batch_writer.py:248-254` вызывает `write_gold()` без `ingestion_ts=` | Plan 3, Plan 4 |
| **P2** | **GoldWriter генерирует новый run_id/timestamp** | `gold_writer.py:250,254` — `datetime.now(UTC)` и `RunID(uuid4())` как fallback | Plan 3, Plan 4 |
| **P3** | **Tri-state VACUUM override не работает** | `bootstrap.py:130-134` — truthy-проверка `if ctx.vacuum.enabled` не позволяет `False` перекрыть YAML `true` | Plan 1 |
| **P4** | **Нет make bench для бенчмарков** | `Makefile` не содержит target `bench`, хотя `benchmarks/` существует | Plan 2 |

### 2.2. ❌ ЛОЖНЫЕ УТВЕРЖДЕНИЯ (не повторять)

| # | Ложное утверждение | Почему ложно | Источник |
|---|-------------------|--------------|----------|
| **F1** | "Необязательный трейсер/метрики — проблема" | NoOp Pattern (`NoOpTracing`, `NoOpMetrics`) — **валидный паттерн** согласно `REFACTORING_PLAN.md` "ЛОЖНЫЕ УТВЕРЖДЕНИЯ" | Plans 1-4 |
| **F2** | "PipelineContext не имеет started_at" | **Имеет**: `context.py:104` — `started_at: datetime = field(default_factory=_now_utc)` | Plan 1 |
| **F3** | "RecordProcessor не использует context.started_at" | **Использует**: `record_processor.py:91` — `ingestion_ts = self._context.started_at` | Plan 1 |
| **F4** | "DeltaWriter fallback на datetime.now — критично" | Архитектурный тест `test_no_datetime_now_in_infrastructure.py:29-55` **явно разрешает** `delta_writer.py` и `gold_writer.py` в `ALLOWED_FILES` с обоснованием для audit logging | Plans 3-4 |
| **F5** | "BaseTransformer NoOp default нарушает observability" | By design: Null Object Pattern для тестов и опциональных сценариев. Документировано в `REFACTORING_PLAN.md` | Plans 1-4 |

### 2.3. ⚠️ ЧАСТИЧНО ВЕРНЫЕ (требуют уточнения)

| # | Утверждение | Реальность |
|---|-------------|------------|
| **H1** | "started_at не передаётся при resume" | `PipelineContext.create()` (`context.py:129`) использует `started_at or datetime.now(UTC)`, но CLI/entrypoints **не передают** `started_at` при resume — это может быть желательно для tracking нового запуска |
| **H2** | "VACUUM выключен по умолчанию даже для rebuild" | `RuntimeConfig.vacuum_after_run=False` — **by design** для явного контроля. Не является проблемой, но может потребовать документирования |

---

## 3. Консолидированная Оценка (10 категорий)

| Категория | Вес | Оценка | Взвешенный | Комментарий |
|-----------|-----|--------|------------|-------------|
| Архитектура слоёв | 0.14 | 9 | 1.26 | Ports & Adapters, архитектурные тесты |
| Модульность и связность | 0.11 | 8 | 0.88 | PipelineRunner 167 LOC, делегирует через RunnerServices |
| Качество доменной модели | 0.10 | 9 | 0.90 | Чистые value objects, Protocol-порты |
| Dependency Injection | 0.10 | 8 | 0.80 | Composition root, сервис-бандлы |
| Тестирование | 0.12 | 8 | 0.96 | 1471+ тестов, 97 архитектурных |
| Обработка ошибок | 0.10 | 8 | 0.80 | ErrorClassifier, retry policies |
| Наблюдаемость | 0.09 | 7 | 0.63 | Tracing/metrics есть, но optional NoOp |
| Производительность | 0.08 | 7 | 0.56 | Async/batch, но нет CI гейтов |
| Безопасность и конфигурация | 0.08 | 8 | 0.64 | Валидация YAML, но VACUUM override issue |
| Документация | 0.08 | 8 | 0.64 | RULES/ADR актуальны |

**Итого: 8.07 → округлено 8.10 / 10**

---

## 4. План Рефакторинга (приоритизированный) — ✅ РЕАЛИЗОВАНО

> **Статус**: Все задачи P1-P4 реализованы в коммите `ab40d36`

### 4.1. ✅ ~~🔴 КРИТИЧНО~~ — P1+P2: Gold Writer ingestion_ts и run_id

**Проблема**: `BatchWriter.write_gold()` не передаёт `ingestion_ts` в `StoragePort.write_gold()`.
`GoldWriter._log_gold_audit()` генерирует новый `run_id` и fallback timestamp.

**Верификация**:
```
batch_writer.py:248-254  — нет ingestion_ts=
gold_writer.py:250       — datetime.now(UTC) if ingestion_ts is None
gold_writer.py:254       — run_id = RunID(uuid4())
```

**Решение**:

| Файл | Строки | Изменение |
|------|--------|-----------|
| `batch_writer.py` | 248-254 | Добавить `ingestion_ts=self._context.started_at` в вызов `write_gold()` |
| `gold_writer.py` | 90-100 | Сделать `ingestion_ts` обязательным параметром `write_gold()` |
| `gold_writer.py` | 230-275 | В `_log_gold_audit()` использовать `ingestion_ts` без fallback, извлекать `run_id` из записей (или добавить параметр) |

**Критерии готовности**:
- [ ] `write_gold()` требует `ingestion_ts: datetime` (не Optional)
- [ ] `_log_gold_audit()` не вызывает `datetime.now()` и `uuid4()`
- [ ] Архитектурный тест подтверждает отсутствие fallback
- [ ] Unit-тест проверяет корреляцию run_id/ingestion_ts между слоями

**Риски**:
- Изменение сигнатуры `write_gold()` требует обновления всех вызовов
- Минимизация: grep по кодовой базе, обновить тесты

---

### 4.2. ✅ ~~🟠 ВЫСОКИЙ~~ — P3: Tri-state VACUUM override

**Проблема**: CLI `--vacuum.enabled=false` не перекрывает YAML `auto_vacuum: true`.

**Верификация**:
```python
# bootstrap.py:130-134
vacuum_after_run = (
    ctx.vacuum.enabled           # False is falsy!
    if ctx.vacuum.enabled        # Truthy check fails for False
    else yaml_config.maintenance.auto_vacuum
)
```

**Решение**:

| Файл | Строки | Изменение |
|------|--------|-----------|
| `context.py` | 75-83 | Изменить `VacuumConfig.enabled: bool` на `enabled: bool | None` (None = use YAML) |
| `bootstrap.py` | 130-134 | Использовать `is not None` проверку вместо truthy |

**Целевой код**:
```python
# bootstrap.py
vacuum_after_run = (
    ctx.vacuum.enabled
    if ctx.vacuum.enabled is not None
    else yaml_config.maintenance.auto_vacuum
)
```

**Критерии готовности**:
- [ ] `VacuumConfig.enabled: bool | None = None`
- [ ] CLI `--vacuum.enabled=false` явно отключает VACUUM
- [ ] Unit-тест покрывает все 3 состояния: None (YAML), True (override on), False (override off)

---

### 4.3. ✅ ~~🟡 СРЕДНИЙ~~ — P4: Benchmark CI Integration

**Проблема**: `benchmarks/` существует, но нет `make bench` и CI интеграции.

**Верификация**:
```
benchmarks/test_delta_write.py    — существует
benchmarks/test_bronze_write.py   — существует
Makefile                          — нет target "bench"
```

**Решение**:

| Файл | Изменение |
|------|-----------|
| `Makefile` | Добавить `bench:` target |
| `.github/workflows/` | Добавить nightly benchmark job (опционально) |

**Целевой код (Makefile)**:
```makefile
bench: ## Run performance benchmarks
	@echo "$(BLUE)Running benchmarks...$(NC)"
	$(VENV_PYTHON) -m pytest benchmarks/ -v --benchmark-only --benchmark-json=reports/benchmark.json
	@echo "$(GREEN)Benchmarks complete! Results in reports/benchmark.json$(NC)"
```

**Критерии готовности**:
- [ ] `make bench` запускает бенчмарки
- [ ] Результаты сохраняются в `reports/benchmark.json`
- [ ] (Опционально) CI nightly job с threshold alerting

---

## 5. Задачи, НЕ Требующие Работы

Следующие "проблемы" из исходных планов **не являются реальными проблемами**:

| Задача | Почему не требуется |
|--------|---------------------|
| Обязательный tracer/metrics | NoOp Pattern — валидный design для тестов и опциональных сценариев |
| DeltaWriter datetime.now в audit | Явно разрешено в `ALLOWED_FILES` архитектурного теста |
| PipelineContext.started_at добавление | Уже реализовано (`context.py:104`) |
| RecordProcessor использование started_at | Уже реализовано (`record_processor.py:91`) |
| VACUUM auto для rebuild/backfill | By design: explicit control. Документировать, не менять |

---

## 6. Обновления Документации

После выполнения рефакторинга обновить:

1. **`docs/REFACTORING_PLAN.md`** — добавить P1-P4 в секцию "УЖЕ РЕАЛИЗОВАНО" после выполнения
2. **`CLAUDE.md` §2.3** — добавить новые ложные утверждения F1-F5 для предотвращения повторений
3. **`docs/02-architecture/decisions/ADR-014`** — уточнить Gold layer ingestion_ts требования

---

## 7. Метрики Успеха

| Метрика | До | После |
|---------|-----|-------|
| Консолидированный балл | 8.10 | ≥8.30 |
| datetime.now в Gold audit | Есть fallback | Нет fallback |
| VACUUM CLI override | Не работает для False | Работает tri-state |
| make bench | Отсутствует | Присутствует |

---

## 8. Расхождения Между Планами (Разрешённые)

| Аспект | Plan 1 | Plan 2 | Plan 3 | Plan 4 | Решение |
|--------|--------|--------|--------|--------|---------|
| Score | 7.90 | 8.26 | 8.02 | 8.01 | Усреднено: 8.05 → 8.10 |
| NoOp как проблема | Да | Да | Да | Да | **НЕТ** — это design pattern |
| started_at проблема | Да | — | — | Да | **ЧАСТИЧНО** — реализовано, но не в Gold |
| VACUUM issue | Да | Да | — | — | **ДА** — tri-state нужен |
| Benchmarks | — | Да | — | — | **ДА** — добавить make bench |

---

*Строй надёжно. Верифицируй дважды. Документируй честно.*
