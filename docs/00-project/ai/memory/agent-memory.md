# Agent Memory — BioETL Project

*Статус: internal-published (Internal / Extended)*

*Версия: 1.0.5 | Дата: 2026-03-10 | Синхронизировано с ORCHESTRATION.md v4.1, RULES.md v5.24*

> **Назначение**: Полный контекст для быстрого онбординга новой AI-сессии в BioETL.
> При старте новой сессии — попроси агент прочитать этот файл:
> `Прочитай docs/00-project/ai/memory/agent-memory.md и следуй его инструкциям.`

---

## 1. Проект BioETL — Краткая Справка

**Назначение**: ETL-фреймворк для данных биоактивности из научных баз данных.

| Аспект | Значение |
|--------|----------|
| Архитектура | Hexagonal (Ports & Adapters) + Medallion (Bronze→Silver→Gold) + DDD |
| Deployment | Local-Only (ADR-010) — без Docker/Redis в runtime |
| Провайдеры | ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, SemanticScholar (7 шт.) |
| ADR | 43 файла (ADR-001..ADR-043), исторически superseded: ADR-008 |
| Coverage target | ≥85% overall, ≥90% domain |
| RULES.md | v5.23 (2026-03-02) |

### Ключевые файлы

| Артефакт | Путь |
|----------|------|
| Правила проекта (Конституция) | `docs/00-project/RULES.md` |
| Правила оркестратора и runtime policy | `AGENTS.md` |
| Инструкции для Claude | `docs/00-project/ai/agents/guides/CLAUDE.md` |
| Персона агента | `docs/00-project/ai/agents/guides/AGENT.md` |
| Claude compact context (runtime-specific) | `.claude/PROJECT_CONTEXT.md` |
| Claude self-review rules (runtime-specific) | `.claude/rules/ai-selfreview-rules.md` |
| Оркестрация субагентов | `.codex/agents/ORCHESTRATION.md` |
| Папка с промтами проекта | `docs/00-project/ai/prompts/` |
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
make test          # Локальный стабильный suite с coverage (без E2E)
make test-architecture  # Архитектурные тесты
make install       # Установка зависимостей
make run-local     # Запуск на фикстурах
```

### Unified Script Entry Points

Все скрипты доступны через `python -m scripts.<group> <command>`:

| Group | Entry Point | Назначение |
|-------|-------------|------------|
| `scripts.qa` | `python -m scripts.qa` | Quality checks: naming, C901, terminology |
| `scripts.ci` | `python -m scripts.ci` | CI pipeline: pytest runner, quality gates |
| `scripts.schema` | `python -m scripts.schema` | Schema/config validation и генерация |
| `scripts.data` | `python -m scripts.data` | Data integrity: VCR, checksums, delta |
| `scripts.docs` | `python -m scripts.docs` | Documentation: links, drift, docstrings |
| `scripts.diagrams` | `python -m scripts.diagrams` | Diagram lint, check, fix, render |
| `scripts.repo` | `python -m scripts.repo` | Repo hygiene: inventory, catalog, versions |
| `scripts.ops` | `python -m scripts.ops` | Ops: salt rotation, Grafana, deploy |
| `scripts.dev` | `python -m scripts.dev` | Dev setup, test runner, mock metrics |
| `scripts.diagnostics` | `python -m scripts.diagnostics` | Debug: cleanup, pandera, storage |

Каждая группа поддерживает `--help` и `<command> --help`. Скрипты также доступны напрямую: `python scripts/qa/naming_audit.py`.

#### Ключевые команды по задачам

```bash
# Архитектурная валидация
python -m scripts.qa check-naming --check
python -m scripts.qa check-c901
python -m scripts.repo check-inventory --check

# Config/schema
python -m scripts.schema validate-configs
python -m scripts.schema check-invariants
python -m scripts.schema generate-pipeline --check

# Документация
python -m scripts.docs check-links --links --specs --configs
python -m scripts.docs check-drift --ports --classes
python -m scripts.docs check-docstrings --summary

# Диаграммы
python -m scripts.diagrams lint
python -m scripts.diagrams check quality-gates
python -m scripts.diagrams render-pdf

# Data integrity
python -m scripts.data check-vcr-placement
python -m scripts.data checksums --generate

# CI / Quality gates
python -m scripts.ci quality-gate
python -m scripts.ci run-tests
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

Вызов: `spawn_agent(agent_type="default" | "explorer" | "worker", message="...")`

| # | `subagent_type` | Модель | Зона записи | Назначение |
|:-:|-----------------|--------|-------------|------------|
| I | `py-audit-bot` | opus | read-only | Baseline/final аудит, code review, arch boundaries, API validation |
| II | `py-plan-bot` | opus | read-only | Декомпозиция на RF-*, DAG зависимостей, composite pipeline design |
| III | `py-test-bot` | sonnet | `tests/` | Baseline/final/retest тесты, coverage ≥85%, VCR |
| IV | `py-config-bot` | sonnet | `configs/` | Pipeline/DQ/filter YAML configs, composite, gap remediation |
| V | `py-debug-bot` | opus | `src/bioetl/`, `tests/` (fixes) | RCA падений, DBG-* итерации (макс 5), mypy/import/runtime |
| VI | `py-doc-bot` | sonnet | `docs/`, docstrings | ADR, CHANGELOG, docstrings, diagrams, doc-code sync |

> Production-код пишем напрямую через Edit/Write (без отдельного субагента).

### 3.2 Полные спецификации и память субагентов

Перед вызовом субагента — прочитай его спецификацию и память:

```
.codex/agents/py-audit-bot.md    — входы, выходы, чеклисты, scoring
.codex/agents/py-plan-bot.md     — шаблоны планов, RF-* routing
.codex/agents/py-test-bot.md     — test selection strategy, VCR management
.codex/agents/py-config-bot.md   — шаблоны YAML, иерархия configs
.codex/agents/py-debug-bot.md    — методология отладки, классификация ошибок
.codex/agents/py-doc-bot.md      — структура docs, ADR management, diagrams
.codex/agents/ORCHESTRATION.md   — полный workflow, матрица взаимодействий
```

**Специализированная память (фокус на области работы агента):**

```
docs/00-project/ai/memory/memory-py-audit-bot.md   — import matrix, anti-patterns, naming, scoring, valid exceptions
docs/00-project/ai/memory/memory-py-plan-bot.md    — RF-* routing, DAG, composite design, parallelization, ADR
docs/00-project/ai/memory/memory-py-test-bot.md    — test structure, thresholds, VCR, failure classification
docs/00-project/ai/memory/memory-py-config-bot.md  — config hierarchy, templates, ADR compliance, composite rules
docs/00-project/ai/memory/memory-py-debug-bot.md   — error classification, debugging methodology, fix patterns
docs/00-project/ai/memory/memory-py-doc-bot.md     — doc structure, ADR management, CHANGELOG, docstrings, diagrams
```

### 3.3 Входы субагентов (обязательные параметры)

При вызове `spawn_agent(...)` или соответствующего runtime wrapper включай в `message`:

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
├── 04-refactoring-log.md     ← orchestrator + py-debug-bot
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
   - напрямую (orchestrator)   → src/bioetl/  → 04-refactoring-log.md
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
| **New entity** | plan → orchestrator(scaffold) → config-bot(3 configs) → test(new+final) → doc → audit |
| **Composite pipeline** | audit(baseline) → plan(composite) → config-bot → orchestrator → test → doc → audit |

### 4.2 Параллелизация

- `py-test-bot (baseline)` || `py-audit-bot (baseline)` — оба read-only
- `orchestrator` || `py-config-bot` — разные файловые зоны
- `py-doc-bot` || `py-audit-bot (final)` — если doc не влияет на code audit

---

## 5. Skills (Навыки)

### 5.1 Проектные Skills и entrypoints

Механика вызова зависит от активного runtime. SSOT для проектных skills и
workflow-ролей находится в `.codex/skills/` и `.codex/agents/`.

| Skill / entrypoint | Где смотреть SSOT | Назначение |
|-------------------|-------------------|------------|
| `agent-orchestration` | `.codex/skills/agent-orchestration/` | Координация multi-agent workflow |
| `py-audit-bot` | `.codex/skills/py-audit-bot/` | Baseline/final audit |
| `py-plan-bot` | `.codex/skills/py-plan-bot/` | RF-планирование |
| `py-test-bot` | `.codex/skills/py-test-bot/` | Post-change verification |
| `py-doc-bot` | `.codex/skills/py-doc-bot/` | Документационные правки |
| `py-config-bot` | `.codex/skills/py-config-bot/` | Config/docs sync |
| `py-debug-bot` | `.codex/skills/py-debug-bot/` | Failure triage |
| `py-review-orchestrator` | `.codex/skills/py-review-orchestrator/` | Независимый double-check |
| `py-test-swarm` | `.codex/skills/py-test-swarm/` | Иерархическое тестирование |
| `new-pipeline` | `.codex/skills/new-pipeline/` | Scaffolding pipeline |
| `verify-architecture` | `.codex/skills/verify-architecture/` | Архитектурные проверки |
| `documentation-audit` | `.codex/skills/documentation-audit/` | Аудит документации |
| `architecture-guardian` | `.codex/skills/public/architecture-guardian/` | Граничный архитектурный review |

### 5.2 Runtime-specific conveniences

Claude slash-команды, built-in `Skill(...)` вызовы и прочие runtime-specific
entrypoints допустимы только как дополнительное удобство. Их нельзя считать
каноническим workflow для BioETL: приоритет у `.codex/agents/ORCHESTRATION.md`,
`AGENTS.md` и `.codex/skills/`.

Если нужна фактическая команда для текущего runtime, смотри его собственный
реестр команд/skills, а не эту память.

---

## 6. Runtime Integrations

Runtime-конфигурация зависит от активного AI-клиента и должна читаться из
его реестров, а не из статического списка в этой памяти.

| Runtime | Что проверять |
|---------|---------------|
| Codex | `.codex/config.toml`, `.codex/settings.json`, `.codex/agents/`, `.codex/skills/` |
| Claude | `.claude/settings.json`, `.claude/agents/`, `.claude/skills/` |
| Copilot | `.github/copilot-instructions.md`, workspace MCP config |
| Gemini | `.gemini/` |

### 6.1 MCP / Tool Policy

- Для текущего набора MCP-серверов проверяй активный runtime-конфиг, а не docs mirror.
- Для Codex используй `codex mcp list`, если нужен фактический список серверов в этой сессии.
- При расхождениях runtime-реестры имеют приоритет над документационными копиями.

---

## 7. Native Agent Types (Codex Runtime)

В Codex runtime для логических профилей `py-*` используются native `agent_type`:

| `agent_type` | Назначение | Когда использовать |
|--------------|------------|-------------------|
| `default` | Аудит, планирование, оркестрация, review | Baseline/final audit, RF-plan, docs/code review |
| `explorer` | Read-only discovery | Инвентаризация, поиск фактов, узкие проверки |
| `worker` | Изолированная write-zone работа | Docs/config/test edits с явной зоной владения |

Claude-specific built-ins и plugin-инвентари допустимо хранить только как
исторический контекст. Для текущего workflow BioETL их нельзя считать SSOT:
приоритет у `.codex/agents/ORCHESTRATION.md`.

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
2. **Прочитать `AGENTS.md`** — правила оркестратора, ограничения и tooling
3. **Прочитать `.codex/agents/ORCHESTRATION.md`** — текущий workflow и роли
4. **При использовании логического профиля** — прочитать `.codex/agents/py-{name}.md`
5. **При scaffolding** — использовать workflow `new-pipeline`
6. **Перед завершением code/docs changes** — прогнать `verify-architecture` или эквивалентный project check
7. **Только если активный runtime = Claude** — дополнительно прочитать `.claude/PROJECT_CONTEXT.md`
8. **Только если активный runtime = Claude** — дополнительно прочитать `.claude/rules/ai-selfreview-rules.md`

### Команда для загрузки полного контекста:

```
Прочитай следующие файлы и следуй их инструкциям:
1. docs/00-project/ai/memory/agent-memory.md
2. AGENTS.md
3. .codex/agents/ORCHESTRATION.md
4. .codex/agents/py-{name}.md  # если используется логический профиль
```

---

*Этот файл — живой документ. Обновляй при изменении архитектуры, добавлении новых агентов или правил.*
