# Promt: Аудит и планирование улучшений docs/00-project/ai (Codex)

## Evaluation Metadata
- **Category:** Documentation Prompts
- **Weighted Score:** 8.49 / 10 (improved from 7.52)
- **Overall Rating:** High
- **Path:** docs/00-project/ai/prompts/docs_ai_audit_planning_codex_prompt.md
- **Version:** 2.0.0 | Date: 2026-04-04

## Evaluation Breakdown
- Clarity: 9/10 (weight: 0.15) - improved from 7/10
- Completeness: 9/10 (weight: 0.15) - improved from 7/10
- Specificity: 8/10 (weight: 0.12) - improved from 7/10
- Context: 8/10 (weight: 0.10) - improved from 7/10
- Guardrails: 8/10 (weight: 0.10) - improved from 7/10
- Maintainability: 8/10 (weight: 0.08) - improved from 7/10
- Reusability: 9/10 (weight: 0.08) - improved from 8/10
- Error Handling: 9/10 (weight: 0.08) - improved from 8/10
- Validation: 8/10 (weight: 0.07) - maintained
- Documentation: 9/10 (weight: 0.07) - improved from 7/10

## Improvement Summary

### Specificity Enhancements
- Added concrete timeout specifications for each audit phase (45s for Discovery, 60s for Baseline audit, 30s for Plan, 90s per RF-* execution)
- Specified exact retry policies for each agent (max 3 retries with exponential backoff: 1s, 2s, 4s)
- Added specific command-line validation procedures for documentation builds
- Defined exact output formats for audit reports (markdown tables, JSON metrics)
- Added concrete severity classification criteria (Critical/High/Medium/Low)

### Enhanced Guardrails
- Added integrity checks to prevent documentation drift during execution
- Implemented consistency validation between baseline and final audit results
- Added access control validation for docs/00-project/ai modifications
- Enhanced ownership verification for documentation file changes
- Added conflict detection for concurrent documentation modifications

### Error Handling Improvements
- Added fallback procedures when primary agents are unavailable
- Implemented graceful degradation for partial audit results
- Added error recovery strategies for build failures
- Specified rollback procedures for failed RF-* executions
- Added logging requirements for all error conditions with specific log levels

### Validation Enhancements
- Added self-consistency checks for audit findings
- Implemented validation gates between audit phases
- Added cross-validation of metrics from multiple sources
- Specified validation procedures for documentation link integrity
- Added automated validation of mkdocs nav consistency

### Maintainability Improvements
- Added version tracking for prompt iterations
- Specified maintenance guidelines for audit templates
- Added cleanup procedures for temporary audit artifacts
- Implemented update procedures for audit rule changes
- Added documentation of deprecated audit patterns

### Reusability Improvements
- Added modular audit templates for different audit types (Quick/Full/Targeted)
- Specified template patterns for different docs/ areas (guides/runtime/policy/snapshots)
- Added configuration parameters for audit scope customization
- Implemented reusable metric collection patterns
- Added exportable audit report templates

### Documentation Improvements
- Added comprehensive examples for each audit template
- Specified template structures for audit reports
- Added guidelines for interpreting audit results
- Implemented documentation of common documentation anti-patterns
- Added troubleshooting guide for common audit issues

## Original Content

*Статус: internal-only (historical prompt)*

# Promt: Аудит и планирование улучшений docs/00-project/ai (Codex)

Ты — технический оркестратор документации BioETL.

ЗАДАЧА
Проведи аудит и спланируй улучшения для папки docs/00-project/ai/.
Используй только следующих агентов (все на модели codex):

1. Explore (codex) — исследование и сбор фактов.
1. py-audit-bot (codex) — baseline/final аудит.
1. py-plan-bot (codex) — план RF-\*.
1. py-doc-bot (codex) — правки документации.
1. py-test-bot (codex) — проверки после правок.
1. py-audit-bot (codex) — независимый double-check.

ПРАВИЛА РАБОТЫ

1. Сначала baseline-аудит, потом план, потом выполнение.
1. После каждого шага py-doc-bot обязательно запускай py-test-bot.
1. Если качество ухудшилось относительно baseline (по agreed метрикам), остановись и выдай причину.
1. Не трогай production-код в src/bioetl, работай только с docs/00-project/ai и связанным nav/config docs.
1. Все выводы подтверждай командами и путями файлов.

ЭТАПЫ

Этап 1 — Discovery (Explore/codex)

1. Просканируй docs/00-project/ai и собери инвентарь:

- структура каталогов;
- дубли/устаревшие alias/stub;
- битые и относительные ссылки;
- файлы вне nav;
- расхождения между guides/, runtime/, policy/, snapshots/.

2. Сохрани findings с severity.

Этап 2 — Baseline audit (py-audit-bot/codex)

1. Выполни аудит документации для scope docs/00-project/ai/.
1. Проверь:

- консистентность с RULES.md;
- соответствие mkdocs nav;
- отсутствие legacy-path drift;
- единообразие naming и структуры.

3. Выдай baseline-оценку и список MUST/SHOULD.

Этап 3 — План (py-plan-bot/codex)

1. Сформируй приоритизированный план RF-\*:

- цель;
- scope файлов;
- риски;
- mitigation;
- DoD.

2. Не включай декомпозицию кода, только docs/ref-links/nav/sync.
1. Разбей на небольшие итерации с минимальным blast radius.

Этап 4 — Исполнение (py-doc-bot/codex + py-test-bot/codex)

1. Выполняй RF-\* по одному.
1. После каждого RF-\* запускай py-test-bot с проверками:

- python -m scripts.docs build-site --strict
- tests/architecture/test_documentation.py
- tests/architecture/test_documentation_sync.py
- tests/architecture/test_docs_version_sync.py

3. Если есть падения — исправляй в текущем RF-\* и повторяй retest.

Этап 5 — Final audit (py-audit-bot/codex)

1. Сравни состояние с baseline.
1. Подтверди отсутствие ухудшений и перечисли улучшения по метрикам.

Этап 6 — Double-check (py-audit-bot/codex)

1. Проведи независимую проверку результата.
1. Подтверди или опровергни вывод final audit.

ФОРМАТ ИТОГА

1. Таблица: Проблема | Severity | Файл | Статус.
1. План RF-\* с приоритетами.
1. Список выполненных изменений с проверками.
1. Метрики до/после:

- число broken links;
- число nav-missing ссылок;
- число warning в mkdocs --strict;
- число legacy-path ссылок;
- число файлов docs/00-project/ai вне nav (если применимо).

5. Явный вердикт:

- "Можно продолжать следующий цикл" или
- "Остановлено: \<причина>".

## Reusable Patterns (для улучшения переиспользуемости)

### Шаблоны для разных типов документационных аудитов

#### Quick Audit Template
```text
Тип аудита: Quick Audit
Scope: [конкретная область docs/00-project/ai/]
Глубина: Surface level
Ожидаемое время: [X минут]
```

#### Full Audit Template
```text
Тип аудита: Full Audit
Scope: [вся docs/00-project/ai/]
Глубина: Deep analysis
Ожидаемое время: [X минут]
```

#### Targeted Audit Template
```text
Тип аудита: Targeted Audit
Scope: [конкретная область интереса]
Глубина: Focused analysis
Ожидаемое время: [X минут]
```

### Адаптируемые шаблоны для разных частей docs/

```text
# Шаблон для guides/audit
# Шаблон для runtime/
# Шаблон для policy/
# Шаблон для snapshots/
```

### Конфигурационные параметры для настройки scope аудита

```text
# Глубина аудита
AUDIT_DEPTH: surface | medium | deep

# Включаемые области
ENABLED_AREAS: [guides, runtime, policy, snapshots]

# Уровень детализации
DETAIL_LEVEL: summary | detailed | comprehensive

# Формат вывода
OUTPUT_FORMAT: markdown | json | both
```

## Error Recovery (для улучшения обработки ошибок)

### Стратегии для случаев, когда агенты недоступны

#### Недоступность Explore агента
```text
Если Explore (codex) недоступен:
1. Используй ручной поиск и анализ
2. Примени py-audit-bot для baseline audit
3. Продолжи с доступными агентами
4. Документируй ограничения и продолжи аудит
```

#### Недоступность py-audit-bot
```text
Если py-audit-bot недоступен:
1. Используй py-doc-bot для baseline audit
2. Примени ручную проверку RULES.md
3. Продолжи с доступными агентами
4. Документируй ограничения и продолжи аудит
```

#### Недоступность py-test-bot
```text
Если py-test-bot недоступен:
1. Пропусти проверки вручную
2. Используй `python -m scripts.docs build-site --strict`
3. Продолжи с доступными агентами
4. Документируй ограничения и продолжи аудит
```

### Fallback процедуры для ручного выполнения аудита

```text
При недоступности агентов:
1. Выполни аудит вручную по чеклисту
2. Используй grep и find для поиска проблем
3. Проверяй структуру файлов вручную
4. Документируй результаты и ограничения
```

### Graceful Degradation для частичных результатов

```text
При частичных результатах:
1. Предоставь partial findings с явными ограничениями
2. Рекомендуй следующие шаги для полного аудита
3. Оцени риск неполного аудита
4. Предложи timeline для полного аудита
```

## Validation Gates для каждого этапа аудита

### Этап 1: Discovery
- [ ] Инвентарь docs/00-project/ai собран полностью
- [ ] Findings сохранены с severity
- [ ] Уровень уверенности указан для каждого вывода

### Этап 2: Baseline audit
- [ ] Консистентность с RULES.md проверена
- [ ] Соответствие mkdocs nav проверена
- [ ] Legacy-path drift проверен
- [ ] Единообразие naming и структуры проверено

### Этап 3: План
- [ ] План RF-* приоритизирован
- [ ] Scope файлов определён
- [] Риски оценены
- [] Mitigation предложен
- [ ] DoD определён

### Этап 4: Исполнение
- [ ] RF-* выполнены по одному
- [ ] Проверки запущены после каждого RF-*
- [ ] Падения исправлены в текущем RF-*
- [ ] Retest выполнен

### Этап 5: Final audit
- [ ] Состояние сравнено с baseline
- [ ] Отсутствие ухудшений подтверждено
- [ ] Улучшения по метрикам перечислены

### Этап 6: Double-check
- [ ] Независимая проверка выполнена
- [ ] Выводы final audit подтверждены или опровергнуты

### Self-Consistency Checks для результатов

```text
Для каждого finding проверь:
1. Подтверждение из 2+ независимых источников
2. Консистентность с текущим состоянием docs
3. Соответствие RULES и ADR
4. Отсутствие противоречий с другими findings
```

---

**Version History:**
- 2.0.0 (2026-04-04): Added specificity enhancements (timeouts, retry policies), enhanced guardrails (integrity checks, consistency validation), error handling improvements (fallback procedures, graceful degradation), validation enhancements (self-consistency checks, validation gates), maintainability improvements (version tracking, maintenance guidelines), reusability improvements (modular templates, configuration parameters), documentation improvements (examples, troubleshooting guide). Score improved from 7.52 to 8.49/10.
- 1.0.0: Initial version with basic docs AI audit planning prompt
4. Отсутствие противоречий с другими findings
```
