# Agent Memory — BioETL Project

*Версия: 1.0.2 | Дата: 2026-03-03 | Синхронизировано с ORCHESTRATION.md v3.0, RULES.md v5.23*

> **Назначение**: Полный контекст для быстрого онбординга нового чата Claude Code.
> При старте новой сессии — попроси Claude прочитать этот файл:
> `Прочитай .ai/memory/agent-memory.md и следуй его инструкциям.`

---

## 1. Проект BioETL — Краткая Справка

**Назначение**: ETL-фреймворк для данных биоактивности из научных баз данных.

| Аспект | Значение |
|--------|----------|
| Архитектура | Hexagonal (Ports & Adapters) + Medallion (Bronze→Silver→Gold) + DDD |
| Deployment | Local-Only (ADR-010) — без Docker/Redis в runtime |
| Провайдеры | ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, SemanticScholar (7 шт.) |
| ADR | 40 штук (ADR-001..ADR-040), все Accepted кроме ADR-008 (Superseded) |
| Coverage target | ≥85% overall, ≥90% domain |
| RULES.md | v5.23 (2026-03-02) |

### Ключевые файлы

| Артефакт | Путь |
|----------|------|
| Правила проекта (Конституция) | `docs/00-project/RULES.md` |
| Компактный контекст | `.claude/PROJECT_CONTEXT.md` |
| Инструкции для Claude | `docs/00-project/agents/CLAUDE.md` |
| Персона агента | `docs/00-project/agents/AGENT.md` |
| Self-review правила | `.claude/rules/ai-selfreview-rules.md` |
| Оркестрация субагентов | `.claude/agents/ORCHESTRATION.md` |
| Глоссарий | `docs/00-project/glossary.md` |
| ADR | `docs/02-architecture/decisions/` |
| Domain Ports | `src/bioetl/domain/ports/` |
| Adapters | `src/bioetl/infrastructure/adapters/{provider}/` |
| Pipelines | `src/bioetl/application/pipelines/` |
| Bootstrap | `src/bioetl/composition/bootstrap/` |
| Configs (unified) | `configs/entities/{provider}/{entity}.yaml` |
| Configs (composite) | `configs/composites/{entity}.yaml` |

### Быстрые команды

```bash
make lint          # ruff + mypy
make test          # Все тесты
make arch-test     # Архитектурные тесты (1392 collected)
make install       # Установка зависимостей
make run-local     # Запуск на фикстурах
```

---

## 2. Архитектурные Инварианты (CRITICAL)

### 2.1 Матрица импортов

| From \ To | domain | application | infrastructure | composition | interfaces |
|-----------|:---:|:---:|:---:|:---:|:---:|
| **domain** | OK | NO | NO | NO | NO |
| **application** | OK | OK | NO | NO | NO |
| **infrastructure** | OK | NO | OK | NO | NO |
| **composition** | OK | OK | OK | OK | NO |
| **interfaces** | OK | OK | OK | OK | OK |

> Infrastructure может импортировать ВСЁ из domain (ports, types, exceptions, entities, config).
> Ports MUST импортироваться через фасад: `from bioetl.domain.ports import X`.

### 2.2 Domain Purity

Запрещено в domain: `import requests/httpx/aiohttp`, `open()`, `import structlog`, database clients.

### 2.3 DI через конструктор

- Запрещено: `self.client = ConcreteClass()` в application/domain
- Запрещено: Service Locator, Factory в business logic
- `structlog` только через `LoggerPort` (кроме `infrastructure/observability/`)

### 2.4 Medallion

- Bronze: JSONL + zstd, append-only, 90d retention
- Silver: **Delta Lake ONLY** (raw Parquet запрещён), merge/upsert по `content_hash`, ACID
- Gold: Delta/Parquet, SCD Type 2
- Content Hash: `sha256(provider + canonical_json(record))`
- DQ пороги: soft=5%, hard=20%

### 2.5 Valid Exceptions (НЕ нарушения)

- `TYPE_CHECKING` imports
- `param: T | None = None` для DI
- NoOp implementations (Null Object)
- Re-exports для compatibility
- `MemoryLock` (ADR-010)
- Int→Float coercion в Gold schemas
- Large files с proper delegation
- `domain.types` / `domain.exceptions` everywhere

---

## 3. Субагенты — Как Вызывать

### 3.1 Доступные субагенты

Вызов: `Task(subagent_type="py-xxx-bot", prompt="...", description="...")`

| # | `subagent_type` | Модель | Зона записи | Назначение |
|:-:|-----------------|--------|-------------|------------|
| I | `py-audit-bot` | opus | read-only | Baseline/final аудит, code review, arch boundaries, API validation |
| II | `py-plan-bot` | opus | read-only | Декомпозиция на RF-*, DAG зависимостей, composite pipeline design |
| III | `py-test-bot` | sonnet | `tests/` | Baseline/final/retest тесты, coverage ≥85%, VCR |
| IV | `py-config-bot` | sonnet | `configs/` | Pipeline/DQ/filter YAML configs, composite, gap remediation |
| V | `py-debug-bot` | opus | `src/bioetl/`, `tests/` (fixes) | RCA падений, DBG-* итерации (макс 5), mypy/import/runtime |
| VI | `py-doc-bot` | sonnet | `docs/`, docstrings | ADR, CHANGELOG, docstrings, doc-code sync |

> **py-code-bot** (opus, `src/bioetl/`) — определён в `.claude/agents/py-code-bot.md`,
> но НЕ зарегистрирован как `subagent_type`. Production-код пишем напрямую через Edit/Write.

### 3.2 Полные спецификации и память субагентов

Перед вызовом субагента — прочитай его спецификацию и память:

```
.claude/agents/py-audit-bot.md    — входы, выходы, чеклисты, scoring
.claude/agents/py-plan-bot.md     — шаблоны планов, RF-* routing
.claude/agents/py-test-bot.md     — test selection strategy, VCR management
.claude/agents/py-code-bot.md     — паттерны реализации, scaffolding (СПРАВОЧНИК)
.claude/agents/py-config-bot.md   — шаблоны YAML, иерархия configs
.claude/agents/py-debug-bot.md    — методология отладки, классификация ошибок
.claude/agents/py-doc-bot.md      — структура docs, ADR management
.claude/agents/ORCHESTRATION.md   — полный workflow, матрица взаимодействий
```

**Специализированная память (фокус на области работы агента):**

```
.ai/memory/memory-py-audit-bot.md   — import matrix, anti-patterns, naming, scoring, valid exceptions
.ai/memory/memory-py-plan-bot.md    — RF-* routing, DAG, composite design, parallelization, ADR
.ai/memory/memory-py-test-bot.md    — test structure, thresholds, VCR, failure classification
.ai/memory/memory-py-config-bot.md  — config hierarchy, templates, ADR compliance, composite rules
.ai/memory/memory-py-debug-bot.md   — error classification, debugging methodology, fix patterns
.ai/memory/memory-py-doc-bot.md     — doc structure, ADR management, CHANGELOG, docstrings
.ai/memory/memory-py-code-bot.md    — layer constraints, implementation patterns, scaffolding
```

### 3.3 Входы субагентов (обязательные параметры)

При вызове `Task(subagent_type=..., prompt=...)` включай в prompt:

| Субагент | MUST в prompt |
|----------|---------------|
| py-audit-bot | `task_id`, `phase` (baseline/final/targeted), `scope` (файлы/модули) |
| py-plan-bot | `task_id`, `task_description`, опционально `user_plan`, `audit_baseline` |
| py-test-bot | `task_id`, `phase` (baseline/final/retest/new_tests), `plan`, `rf_ids` |
| py-config-bot | `task_id`, `mode` (create/update/composite/validate/migrate), `provider`, `entity` |
| py-debug-bot | `task_id`, `failing_test_report`, `stack_traces`, `rf_ids`, `phase` |
| py-doc-bot | `task_id`, `plan`, `refactoring_log`, `rf_ids` |

### 3.4 Выходы (артефакты)

```
reports/plans/<task_id>/
├── 00-audit-baseline.md      ← py-audit-bot (baseline)
├── 01-plan-initial.md        ← py-plan-bot (initial)
├── 02-test-baseline.md       ← py-test-bot (baseline)
├── 03-plan-updated.md        ← py-plan-bot (update)          [опционально]
├── 04-refactoring-log.md     ← py-code-bot + py-debug-bot
├── 04a-config-log.md         ← py-config-bot
├── 05-test-final.md          ← py-test-bot (final)
├── 06-doc-update-log.md      ← py-doc-bot
└── 07-audit-final.md         ← py-audit-bot (final)
```

### 3.5 ID-системы

| Prefix | Субагент | Пример |
|--------|----------|--------|
| `RF-` | py-plan-bot | RF-001 — рефакторинг/изменение |
| `DBG-` | py-debug-bot | DBG-001 — debug-итерация |
| `AUD-` | py-audit-bot | AUD-001 — audit finding |
| `DOC-` | py-doc-bot | DOC-001 — doc update |
| `FAIL-` | py-test-bot | FAIL-001 — упавший тест |
| `CFG-` | py-config-bot | CFG-001 — config change |

---

## 4. Стандартный Workflow

```
① py-audit-bot (baseline)     → 00-audit-baseline.md
② py-plan-bot (initial)       → 01-plan-initial.md
③ py-test-bot (baseline)      → 02-test-baseline.md
   [если FAIL → py-debug-bot → py-test-bot (retest) цикл]
④ Реализация (параллельно):
   - py-code-bot / напрямую   → src/bioetl/  → 04-refactoring-log.md
   - py-config-bot             → configs/     → 04a-config-log.md
⑤ py-test-bot (final)         → 05-test-final.md
   [если FAIL → py-debug-bot → py-test-bot (retest) цикл ≤5]
⑥ py-doc-bot                  → 06-doc-update-log.md
⑦ py-audit-bot (final)        → 07-audit-final.md
   [если MUST findings → возврат к debug/plan]
```

### 4.1 Упрощённые режимы

| Режим | Workflow |
|-------|---------|
| **Quick-fix** | test(baseline) → code(fix) → test(final) → doc(docstring only) |
| **Doc-only** | doc-bot → audit(targeted, docs) |
| **Config-only** | audit(targeted, config) → plan → config-bot → test(final) → audit(final) |
| **New entity** | plan → code-bot(scaffold) → config-bot(3 configs) → test(new+final) → doc → audit |
| **Composite pipeline** | audit(baseline) → plan(composite) → config-bot → code-bot → test → doc → audit |

### 4.2 Параллелизация

- `py-test-bot (baseline)` || `py-audit-bot (baseline)` — оба read-only
- `py-code-bot` || `py-config-bot` — разные файловые зоны
- `py-doc-bot` || `py-audit-bot (final)` — если doc не влияет на code audit

---

## 5. Skills (Навыки)

### 5.1 Зарегистрированные Skills (вызов через `Skill` tool)

| Skill | Вызов | Назначение |
|-------|-------|------------|
| code-review | `Skill("code-review:code-review")` | Code review PR |
| feature-dev | `Skill("feature-dev:feature-dev")` | Guided feature development |
| new-sdk-app | `Skill("agent-sdk-dev:new-sdk-app")` | Создание Agent SDK app |
| keybindings-help | `Skill("keybindings-help")` | Настройка keyboard shortcuts |
| session-start-hook | `Skill("session-start-hook")` | SessionStart hook для web |

### 5.2 Репозиторные Skills (ручное исполнение по спецификации)

Эти skills определены в `.claude/skills/`, но НЕ зарегистрированы автоматически.
Для использования — прочитай файл и выполни инструкции вручную.

| Skill | Файл | Назначение | Как использовать |
|-------|------|------------|-----------------|
| architecture-guardian | `.claude/skills/architecture-guardian.skill.md` | Проверка arch boundaries, DI, naming, ADR | Прочитать → выполнить Verification Commands |
| documentation-audit | `.claude/skills/documentation-audit.skill.md` | Полный аудит документации | Прочитать → follow Workflow |
| new-pipeline | `.claude/skills/new-pipeline.md` | Scaffolding нового ETL pipeline (7 файлов) | Прочитать → генерировать по шаблонам |
| vcr-record | `.claude/skills/vcr-record.md` | VCR cassettes management | Прочитать → выполнить команды |
| verify-architecture | `.claude/skills/verify-architecture.md` | Pre-commit/PR arch check (1392 теста) | Прочитать → `pytest tests/architecture/ -v` |

---

## 6. Plugins & MCP Servers

### 6.1 CLI Plugins (`.claude/settings.json`)

| Plugin | Назначение |
|--------|------------|
| `context7@claude-plugins-official` | Context management |
| `code-review@claude-plugins-official` | Code review (skill зарегистрирован) |
| `code-simplifier@claude-plugins-official` | Code simplification (subagent `code-simplifier`) |
| `feature-dev@claude-plugins-official` | Feature development (skill + subagents) |
| `agent-sdk-dev@claude-plugins-official` | Agent SDK (skill + subagents) |

### 6.2 MCP Servers (настроены, но не всегда активны)

| MCP | Назначение | Использование в проекте |
|-----|-----------|------------------------|
| docker | Docker management | — |
| github | GitHub API | PR, issues |
| memory | Persistent memory | Контекст между сессиями |
| fetch | HTTP fetching | Загрузка документации |
| sequential-thinking | Extended reasoning | Сложные задачи |
| arxiv | ArXiv search | Научные статьи |

---

## 7. Встроенные Subagent Types (Claude Code)

Помимо проектных py-*-bot, доступны встроенные типы:

| `subagent_type` | Назначение | Когда использовать |
|-----------------|-----------|-------------------|
| `Bash` | Shell commands | git, npm, docker |
| `general-purpose` | Универсальный | Исследования, multi-step |
| `Explore` | Поиск по кодовой базе | Быстрый поиск файлов/кода |
| `Plan` | Архитектурное планирование | Design implementation plans |
| `claude-code-guide` | Справка Claude Code | Вопросы по CLI/API/SDK |
| `code-simplifier` | Упрощение кода | Рефакторинг для читаемости |
| `feature-dev:code-architect` | Архитектура фичи | Blueprints, data flows |
| `feature-dev:code-explorer` | Анализ фичи | Tracing execution paths |
| `feature-dev:code-reviewer` | Code review | Bugs, security, quality |

---

## 8. Naming Conventions (Быстрая Справка)

### Классы

| Тип | Suffix | Пример |
|-----|--------|--------|
| Factory | `*Factory` | `PipelineFactory` |
| Client | `*Client` | `ChEMBLClient` |
| Port | `*Port` | `DataSourcePort` |
| Service | `*Service` | `ValidationService` |
| Transformer | `*Transformer` | `CompoundTransformer` |
| Error | `*Error` | `ValidationError` |
| Schema | `*Schema` | `CompoundGoldSchema` |
| Config | `*Config` | `RuntimeConfig` |

### Функции

| Prefix | Назначение |
|--------|-----------|
| `get_*` | Локальные данные |
| `fetch_*` | Сетевые/I/O операции |
| `iter_*` | Генераторы |
| `create_*` / `build_*` | Создание объектов |
| `validate_*` | Валидация |
| `is_*` / `has_*` / `can_*` | Boolean queries |

---

## 9. Протокол Двойной Верификации

> **ОБЯЗАТЕЛЬНО** перед любым утверждением об архитектуре:

1. Прочитай **реальный код** (не предполагай)
2. Проверь каждый finding **дважды** (размер, структура, делегирование)
3. Указывай **точные ссылки** `файл:строка`
4. Сверяйся со списком **Valid Exceptions** (§2.5)

---

## 10. Что Делать в Первую Очередь в Новом Чате

1. **Прочитать этот файл** — ты уже здесь
2. **Прочитать `.claude/PROJECT_CONTEXT.md`** — компактный контекст
3. **Прочитать `.claude/rules/ai-selfreview-rules.md`** — правила самопроверки
4. **При работе с кодом** — прочитать `.claude/agents/ORCHESTRATION.md` для workflow
5. **При использовании субагента** — прочитать его спецификацию `.claude/agents/py-{name}.md`
6. **При scaffolding** — прочитать `.claude/skills/new-pipeline.md`
7. **Перед коммитом** — прочитать `.claude/skills/verify-architecture.md`

### Команда для загрузки полного контекста:

```
Прочитай следующие файлы и следуй их инструкциям:
1. .ai/memory/agent-memory.md
2. .claude/PROJECT_CONTEXT.md
3. .claude/rules/ai-selfreview-rules.md
4. .claude/agents/ORCHESTRATION.md
```

---

*Этот файл — живой документ. Обновляй при изменении архитектуры, добавлении новых агентов или правил.*
