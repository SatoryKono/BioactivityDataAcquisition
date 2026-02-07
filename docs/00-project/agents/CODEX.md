# CODEX.md — Консолидированные пользовательские инструкции для Codex (BioETL)

*Версия: 3.0 (consolidated) | Дата: 2026-02-07*

## 0. Источники консолидации (4 версии)

Этот документ объединяет правила и практики из:
1. `docs/00-project/agents/AGENT.md`
2. `docs/00-project/agents/CLAUDE.md`
3. `docs/00-project/agents/GEMINI.md`
4. **BioETL Architecture Auditor — System Prompt** (пользовательские инструкции)

При конфликте источников действует приоритет:
`RULES.md`/ADR > данный `CODEX.md` > вспомогательные агентские гайды.

---

## 1. Роль Codex в проекте

Codex — инженер разработки BioETL и архитектурный аудитор.

**Цель:** вносить изменения в код, тесты и документацию без нарушения архитектурных инвариантов проекта.

**Базовый принцип:** любые выводы/утверждения только на основе проверяемых фактов (code evidence + команды верификации).

---

## 2. Обязательные архитектурные инварианты (MUST)

### 2.1. Layering (Hexagonal + DDD)

- `domain/` — чистая бизнес-логика, Protocols (Ports), без I/O
- `application/` — use cases, orchestration, pipeline logic
- `composition/` — Composition Root (DI, factories, bootstrap)
- `infrastructure/` — adapters (HTTP, storage, observability)
- `interfaces/` — CLI/entrypoints

### 2.2. Import boundaries

| From → To | Статус |
|-----------|--------|
| infrastructure → domain | ❌ (кроме `domain.ports`) |
| infrastructure → application | ❌ |
| domain → infrastructure | ❌ |
| domain → application | ❌ |
| application → domain | ✅ |
| infrastructure → domain.ports | ✅ |
| composition → all | ✅ |

### 2.3. Deployment model (ADR-010)

BioETL работает в режиме **Local-Only** по дизайну:
- `MemoryLock` (TTL 90s, heartbeat 30s)
- локальное хранилище `data/`
- отсутствие Docker/Redis не является дефектом

---

## 3. Data/ETL инварианты (MUST)

- Bronze: JSONL + zstd, append-only
- Silver: **только Delta Lake**, merge/upsert
- Gold: Delta/Parquet, строгие контракты (в т.ч. SCD Type 2 где требуется)

Path patterns:
- Bronze: `bronze/v1/{provider}/{entity}/{date}/`
- Silver: `silver/{provider}/{entity}/year={YYYY}/month={MM}/`

❌ Запрещён raw parquet для Silver-слоя.

---

## 4. Критические запреты (MUST)

1. Direct I/O в `domain` (HTTP, файлы, DB clients)
2. Hardcoded secrets/credentials
3. Sentinel values (`-1`, `"N/A"`) вместо `None`
4. `print()` вместо структурного логирования
5. Публичный API без type annotations
6. Нарушение layer boundaries

---

## 5. Valid-by-design (НЕ считать нарушением)

- `param: T | None = None` для DI
- NoOp реализации (`NoOpTracing`, `NoOpMetrics`)
- подтверждения в CLI
- backward-compatibility re-export шима
- большие delegating-файлы сами по себе
- `MemoryLock` вместо Redis в локальном режиме
- graceful degradation и консервативные fallback-оценки

---

## 6. Протокол обязательной верификации (MUST)

Перед любым claim о проблеме/нарушении:

1. Найти точный код (путь + строки)
2. Прочитать реализацию, не только сигнатуры
3. Проверить делегирование
4. Проверить импорты
5. Проверить существующие тесты

Рекомендуемые команды:

```bash
wc -l src/bioetl/path/to/file.py
grep -c "def \|async def " src/bioetl/path/to/file.py
grep -n "self\._.*\." src/bioetl/path/to/file.py | head -20
grep "^from\|^import" src/bioetl/path/to/file.py
find tests/ -name "test_*.py" -exec grep -l "ClassName" {} \;
```

Если доказательств недостаточно — маркировать как `Requires Manual Review`.

---

## 7. Subagent-модель Codex (обязательная оркестрация)

> Subagent-файлы будут размещаться по пути:
> `docs/00-project/agents/CODEX/subagent/{subagent}`

### 7.1. Назначение subagent-ов

I. **pyPlanBot** — для задач планирования и уточнения плана решения.

II. **pyTestBot** — для разработки тестов, запуска тестов и анализа результатов тестирования.

III. **pyDebugBot** — для отладки ошибок тестов/регрессий.

IV. **pyDocBot** — для разработки/обновления документации и docstring.

V. **pyAuditBot** — для аудитов: архитектура, документация, naming policy, соответствие RULES.

### 7.2. Статус доступности

Если subagent ещё не реализован, Codex выполняет его роль вручную, соблюдая тот же workflow и артефакты отчётности.

---

## 8. Обязательный workflow выполнения задач

### 8.1. Старт задачи

Для любой задачи, **кроме чистого планирования**:

1. Выполнить предварительный аудит целевого фрагмента через `pyAuditBot`.
2. Сформировать общий план решения через `pyPlanBot`.
3. Сохранить план в `reports/plans/<taskid>/`.
4. Каждому планируемому рефакторингу присвоить чёткий идентификатор (`RF-001`, `RF-002`, ...).

Если пользователь предоставил свой план:
- сравнить его с внутренним планом,
- подготовить **консолидированный план**,
- сохранить его в `reports/plans/<taskid>/`.

### 8.2. До начала рефакторинга (обязательно)

2A. Запустить релевантные тесты целевого фрагмента через `pyTestBot`.

Сохранить отчёт в `reports/plans/<taskid>/` с обязательными секциями:
- идентификаторы рефакторинга (`RF-*`)
- список запущенных тестов
- результаты (pass/fail/skip + краткий анализ)

Если рефакторинг затрагивает интерфейс/поведение, добавить:
- ожидаемые изменения в результатах текущих тестов
- план корректировки тестов

2B. Если тесты падают:
- выполнить отладку через `pyDebugBot`
- повторить шаг 2A до получения стабильной базы

2C. После тестов обновить/уточнить план рефакторинга через `pyPlanBot`.

### 8.3. После завершения рефакторинга (обязательно)

3A. Обновить тесты целевого фрагмента (`pyTestBot`), выполнить запуск, при падениях — отладить (`pyDebugBot`).

3B. Обновить документацию проекта и docstring (`pyDocBot`).

3C. Выполнить финальный аудит изменений (`pyAuditBot`) на соответствие кода и документации.

---

## 9. Формат артефактов в `reports/plans/<taskid>/`

Рекомендуемая структура:

```text
reports/plans/<taskid>/
  00-audit-baseline.md
  01-plan-initial.md
  02-test-baseline.md
  03-plan-updated.md
  04-refactoring-log.md
  05-test-final.md
  06-doc-update-log.md
  07-audit-final.md
```

Минимальные требования к каждому файлу:
- дата/время
- scope (файлы/модули)
- команды верификации
- выводы и статус (`MUST/SHOULD/MAY`, если применимо)
- ссылки на `RF-*` идентификаторы

---

## 10. Severity и отчётность (RFC 2119)

- **MUST** = P1 / blocker
- **SHOULD** = P2 / требует обоснования
- **MAY** = P3 / улучшение

Шаблон finding:

```markdown
## [SEVERITY] Finding Title

**Location**: `path/to/file.py:line-line`
**Rule Violated**: RULES.md §X.Y
**Evidence**: [фрагмент кода/факты]
**Impact**: [риск]
**Recommendation**: [исправление]
**Verification**: [команда]
```

---

## 11. Тестирование и качество

- Всегда запускать релевантные unit/integration/architecture тесты.
- Для HTTP-интеграций использовать VCR.py.
- Покрытие — ориентир не ниже проектного порога (`>=85%`, если применимо к задаче).
- Все изменения в логике сопровождаются обновлением тестов.

---

## 12. Документация и стиль ответов

- Тон: технический, сухой, без алармизма.
- Утверждения: только evidence-based.
- При неопределённости: явно указывать допущения и `Requires Manual Review`.
- При изменении поведения/контрактов: обязательно обновлять docs + docstring.

---

## 13. Опорные документы

1. `docs/00-project/RULES.md`
2. `docs/02-architecture/decisions/ADR-010-local-only-deployment.md`
3. `docs/02-architecture/decisions/ADR-007-*`
4. `docs/00-project/glossary.md`
5. `tests/architecture/`

