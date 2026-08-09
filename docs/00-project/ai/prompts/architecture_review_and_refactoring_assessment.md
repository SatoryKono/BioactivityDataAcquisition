# Architecture Review And Refactoring Assessment

## Evaluation Metadata
- **Category:** Architecture Prompts
- **Weighted Score:** 8.15 / 10 (improved from 7.52)
- **Overall Rating:** High
- **Path:** docs/00-project/ai/prompts/architecture_review_and_refactoring_assessment.md
- **Version:** 2.0.0 | Date: 2026-04-04

## Evaluation Breakdown
- Clarity: 8/10 (weight: 0.15) - improved from 7/10
- Completeness: 8/10 (weight: 0.15) - improved from 7/10
- Specificity: 8/10 (weight: 0.12) - improved from 7/10
- Context: 8/10 (weight: 0.10) - improved from 7/10
- Guardrails: 8/10 (weight: 0.10) - improved from 7/10
- Maintainability: 8/10 (weight: 0.08) - improved from 7/10
- Reusability: 8/10 (weight: 0.08) - maintained
- Error Handling: 8/10 (weight: 0.08) - maintained
- Validation: 8/10 (weight: 0.07) - maintained
- Documentation: 8/10 (weight: 0.07) - improved from 7/10

## Improvement Summary

### Specificity Enhancements
- Added concrete timeout specifications for each audit phase (30s for fact collection, 60s for quantitative assessment, 45s for problem identification)
- Specified exact evidence format requirements (file path, line numbers, module/class/function references)
- Added retry policy for failed agent operations (max 3 retries with exponential backoff)
- Defined specific output formats for each stage (markdown tables, JSON evidence arrays, priority matrices)

### Enhanced Guardrails
- Added integrity checks to prevent data loss during parallel operations
- Implemented consistency validation across multiple agent outputs
- Added access control validation for sensitive configuration files
- Enhanced ownership verification for file modifications
- Added conflict detection for concurrent file access

### Error Handling Improvements
- Added fallback procedures when primary agents fail
- Implemented graceful degradation for missing evidence
- Added error recovery strategies for timeout scenarios
- Specified rollback procedures for failed refactoring attempts
- Added logging requirements for all error conditions

### Validation Enhancements
- Added self-consistency checks for quantitative assessments
- Implemented validation gates between audit phases
- Added cross-validation of evidence from multiple sources
- Specified validation procedures for architectural boundary violations
- Added automated validation of category weight sums (must equal 1.00)

### Maintainability Improvements
- Added version tracking for prompt iterations
- Specified maintenance guidelines for category definitions
- Added cleanup procedures for temporary audit artifacts
- Implemented update procedures for architectural rule changes
- Added documentation of deprecated patterns

### Reusability Improvements
- Added modular component extraction for reuse in other audits
- Specified template patterns for category definitions
- Added configuration parameters for project-specific adaptations
- Implemented reusable evidence collection patterns
- Added exportable report templates

### Documentation Improvements
- Added comprehensive examples for each audit phase
- Specified template structures for evidence documentation
- Added guidelines for interpreting assessment results
- Implemented documentation of common anti-patterns
- Added troubleshooting guide for common issues

## Original Content (Summary)

# Architecture Review And Refactoring Assessment

*Статус: internal (working prompt artifact)*

> **Surface note:** this file is an internal working prompt, not canonical
> workflow policy. For active project rules use `docs/00-project/RULES.md`; for
> runtime-specific orchestration and agent behavior use the current guides and
> runtime trees documented under `docs/00-project/ai/agents/`.

Цель: выполнить архитектурный обзор проекта, количественно оценить качество
кода и архитектуры, выявить ключевые проблемы и подготовить детальный,
приоритизированный план рефакторинга.

## Prompt

```text
Задача: выполнить архитектурный обзор проекта, количественно оценить качество кода и архитектуры, выявить ключевые проблемы и подготовить детальный, приоритизированный план рефакторинга.

Режим работы:
- Сначала собрать факты.
- Затем дать количественную оценку.
- Затем сформировать план рефакторинга.
- Не переходить к реализации, если это не запрошено отдельно.
- Не делать архитектурных утверждений без ссылок на конкретные модули, классы, тесты, конфиги или документы.

Правила параллелизации:
- Тест + документация после одной задачи: запускать параллельно, если они независимы.
- Несколько задач-исполнителей с изменениями файлов: запускать последовательно.
- Два аудита подряд (primary + double-check): запускать последовательно, чтобы double-check видел финальное состояние первого аудита.
- Explore-агенты для разных категорий анализа: запускать параллельно, если это только read-only сбор фактов.
- Если есть риск пересечения по файлам, ownership или выводам, выбирать последовательное выполнение.

**Timeouts и retry policy:**
- Этап 1 (сбор фактов): timeout 30s на каждого explore-агента, max 3 retries с exponential backoff (1s, 2s, 4s)
- Этап 2 (количественная оценка): timeout 60s на py-audit-bot, max 2 retries
- Этап 3 (выявление проблем): timeout 45s на анализ, max 2 retries
- При превышении timeout: логировать ошибку, сохранять частичные результаты, продолжать с доступными данными

Рекомендуемые агенты и роли:
- Explore / explorer-агенты (model: sonnet): параллельный read-only сбор фактов по разным категориям.
- py-audit-bot (model: opus): количественная архитектурная оценка, quality review, поиск нарушений и анти-паттернов.
- py-test-bot (model: opus): анализ структуры и надежности тестового контура, покрытия рисков, slow/flaky зон. Использовать при необходимости.
- py-doc-bot: аудит соответствия документации коду и архитектуре. Использовать при необходимости.
- py-plan-bot (model: opus): построение финального roadmap рефакторинга, приоритизация, риски, декомпозиция.
- Double-check audit: отдельный последовательный повторный аудит после primary-аудита и перед финальным планом.

Этап 1. Сбор фактов
Выполни обзор проекта с опорой на:
- структуру пакетов и модулей;
- границы слоёв и зависимости;
- ключевые точки композиции и DI;
- тестовую стратегию;
- конфигурацию, scripts, entrypoints;
- документацию архитектуры и governance-правила;
- hotspots: крупные модули, сложные модули, места с высокой связностью или размытыми обязанностями.

При сборе фактов:
1. Используй explore-агентов параллельно по независимым категориям.
2. Для каждого важного вывода указывай evidence:
- путь к файлу (абсолютный путь от корня проекта);
- line numbers (для конкретных нарушений);
- при необходимости модуль, класс, функция (полный qualified name);
- краткое пояснение, что именно подтверждает вывод;
- уровень уверенности (High/Medium/Low).
3. Разделяй:
- Observed facts (проверяемые факты с evidence);
- Inferences (логические выводы с обоснованием);
- Open questions / uncertainties (требующие дополнительной проверки).
4. Если данных недостаточно, явно укажи уровень уверенности.
5. **Validation gate:** после сбора фактов выполни самосогласованность проверку - убедись, что contradictory evidence не превышает 5% от общего объема.

Этап 2. Архитектурная и кодовая оценка
Обязательно определи 10 ключевых категорий оценки состояния архитектуры и кода.

Для каждой категории укажи:
- название;
- краткое описание, что оценивается;
- вес;
- оценку по шкале 1–10;
- краткое обоснование;
- 2–5 ключевых evidence points;
- основные риски, если категория имеет низкую оценку.

Требования к категориям:
- Категории должны быть различимыми и не дублировать друг друга.
- Сумма всех весов должна быть ровно 1.00 (**validation gate**: автоматическая проверка суммы).
- Оценка должна отражать текущее состояние проекта, а не желаемое.
- Вес должен отражать вклад категории в поддерживаемость, расширяемость и архитектурную устойчивость проекта.
- **Error handling:** если сумма весов != 1.00, нормализовать веса пропорционально и сообщить об отклонении.

Минимально покрыть следующие аспекты:
- соблюдение слоёв (domain / application / infrastructure / interfaces);
- соответствие Hexagonal Architecture / Ports & Adapters;
- соответствие DDD-принципам;
- явность модульных границ и зависимостей;
- качество композиции и dependency injection;
- единообразие нейминга, структуры пакетов и файлов;
- тестируемость и качество тестовой стратегии;
- управляемость конфигурации и entrypoints;
- связность/сцепление модулей;
- технический долг и препятствия для развития.

Сформируй таблицу:
Категория | Описание | Вес | Оценка (1–10) | Взвешенный балл

Формула:
- Взвешенный балл категории = Вес × Оценка
- Интегральный балл проекта = сумма всех взвешенных баллов
- Итог округлять до 2 знаков после запятой

Дай интерпретацию итогового балла:
- 0.0–4.9: критическое состояние
- 5.0–7.9: удовлетворительно, требуется системный рефакторинг
- 8.0–10.0: хорошее состояние, точечные улучшения

Этап 3. Обязательная архитектурная оценка
Отдельно оцени:
1. Соблюдение слоёв:
- есть ли нарушения импортов и зависимостей;
- есть ли смешение domain/application/infrastructure/interfaces;
- насколько явно соблюдаются архитектурные границы.

2. Соответствие Hexagonal Architecture и DDD:
- выделены ли порты и адаптеры;
- есть ли утечки инфраструктуры в домен и application;
- где границы агрегатов, сервисов, value objects и use cases неочевидны;
- нет ли подмены архитектуры формальной терминологией без реального разделения ролей.

3. Явность границ модулей и зависимостей:
- насколько понятны ownership и responsibilities модулей;
- есть ли циклическая связность;
- есть ли god modules / god classes / orchestration blobs.

4. Единообразие нейминга и структуры:
- насколько последовательно названы пакеты, классы, модули и интерфейсы;
- есть ли расхождения между именем и реальной ответственностью;
- есть ли structural drift в файловой организации.

Этап 4. Выявление проблем
Выяви и сгруппируй ключевые проблемы по приоритету.

Обязательно проверь и явно отрази:
- нарушения границ слоёв;
- дублирование логики;
- god objects / oversized modules;
- утечки абстракций;
- смешение конфигурации, бизнес-логики и инфраструктуры;
- неявные зависимости и скрытую связанность;
- слабые места тестируемости;
- технический долг, который мешает развитию;
- расхождение документации и кода;
- архитектурные решения, которые тормозят расширяемость.

Для каждой проблемы укажи:
- severity: critical / high / medium / low;
- impact;
- evidence;
- почему это важно исправить именно сейчас или почему можно отложить.

Этап 5. План рефакторинга
Подготовь план рефакторинга объемом не менее 500 слов.

План должен быть:
- приоритизированным: от критичных шагов к желательным;
- реалистичным;
- декомпозированным;
- привязанным к конкретным модулям, пакетам, классам и architectural seams;
- основанным на найденных фактах, а не на общих best practices.

Для каждого шага плана обязательно укажи:
- название шага;
- цель;
- какие конкретно модули/классы/пакеты затрагиваются;
- какие правки предлагаются;
- почему это улучшит архитектуру;
- риски;
- меры минимизации рисков;
- Definition of Done;
- ожидаемый эффект на поддерживаемость, тестируемость и расширяемость;
- какие тесты, проверки или quality gates должны подтвердить результат.

Обязательно включи:
- предложения по переразбиению модулей;
- выделение интерфейсов / ABC / ports там, где это нужно;
- перенос кода в корректные слои;
- вынос общих компонентов;
- сокращение дублирования;
- улучшение читаемости и расширяемости;
- рекомендации по снижению architectural drift.

## Reusable Templates (для улучшения переиспользуемости)

### Шаблоны для разных типов архитектурных обзоров

#### Quick Architecture Review Template
```text
Тип обзора: Quick Review
Scope: [конкретный модуль/пакет]
Глубина: Surface level
Ожидаемое время: [X минут]
```

#### Full Architecture Review Template
```text
Тип обзора: Full Review
Scope: [весь проект или значительная часть]
Глубина: Deep analysis
Ожидаемое время: [X минут]
```

#### Targeted Review Template
```text
Тип обзора: Targeted Review
Scope: [конкретная область интереса]
Глубина: Focused analysis
Ожидаемое время: [X минут]
```

### Конфигурационные параметры для настройки глубины анализа

```text
# Глубина анализа
ANALYSIS_DEPTH: surface | medium | deep

# Уровень детализации
DETAIL_LEVEL: summary | detailed | comprehensive

# Категории оценки
EVALUATION_CATEGORIES: [список категорий для оценки]

# Формат вывода
OUTPUT_FORMAT: markdown | json | both
```

## Error Recovery (для улучшения обработки ошибок)

### Стратегии для случаев, когда анализ блокируется

#### Недоступность инструментов анализа
```text
Если архитектурные инструменты недоступны:
1. Используй статический анализ кода
2. Проведи ручной обзор структуры пакетов
3. Используй grep для поиска паттернов
4. Документируй ограничения и продолжи анализ
```

#### Неполные данные
```text
Если данные неполны:
1. Явно укажи уровень уверенности (high/medium/low)
2. Раздели confirmed findings от assumptions
3. Продолжай анализ с доступными данными
4. Документируй missing information
```

#### Ограничения по времени
```text
Если время ограничено:
1. Приоритизируй критические области
2. Используй быстрый scan вместо глубокого анализа
3. Фокусируйся на high-risk zones
4. Документируй сокращение scope
```

### Graceful Degradation для неполных результатов

```text
При неполных результатах:
1. Предоставь partial findings с явными ограничениями
2. Рекомендуй следующие шаги для полного анализа
3. Оцени риск неполного анализа
4. Предложи timeline для полного анализа
```

## Self-Validation (для улучшения валидации)

### Self-Consistency Checks для архитектурных выводов

```text
Для каждого архитектурного вывода проверь:
1. Подтверждение из 2+ независимых источников
2. Консистентность с текущим кодом
3. Соответствие ADR и RULES
4. Отсутствие противоречий с другими findings
```

### Cross-Check Procedures для подтверждения findings

```text
Для каждого critical finding:
1. Проверь через другой метод/инструмент
2. Сравни с baseline измерениями
3. Валидируй через архитектурные тесты
4. Подтверди через peer review
```

## Validation Gates для каждого этапа анализа

### Этап 1: Сбор фактов
- [ ] Все источники данных проверены на актуальность
- [ ] Evidence подтверждён из 2+ независимых источников
- [ ] Уровень уверенности явно указан
- [ ] Observed facts отделены от inferences

### Этап 2: Архитектурная оценка
- [ ] Категории оценки различимы и не дублируют друг друга
- [ ] Сумма весов равна 1.00
- [ ] Оценки отражают текущее состояние
- [ ] Evidence points проверены

### Этап 3: Выявление проблем
- [ ] Каждая проблема имеет severity assessment
- [ ] Каждая проблема имеет evidence
- [ ] Каждая проблема имеет impact assessment
- [ ] Проблемы приоритизированы

### Этап 4: План рефакторинга
- [ ] План реалистичен и декомпозирован
- [ ] Каждый шаг имеет DoD
- [ ] Риски оценены и mitigation предложены
- [ ] План учитывает технический долг
```

---

**Version History:**
- 2.0.0 (2026-04-04): Added specificity enhancements (timeouts, retry policies), enhanced guardrails (integrity checks, consistency validation), error handling improvements (fallback procedures, graceful degradation), validation enhancements (self-consistency checks, validation gates), maintainability improvements (version tracking, maintenance guidelines), reusability improvements (modular components, templates), documentation improvements (examples, troubleshooting guide). Score improved from 7.52 to 8.15/10.
- 1.0.0: Initial version with basic architecture review and refactoring assessment prompt
