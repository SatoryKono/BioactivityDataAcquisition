# AI Workspace Setup — Промт для настройки AI-агентов в репозитории

*Версия: 1.3.0 | Дата: 2026-03-08*

## Назначение

Промт для первоначальной настройки и аудита конфигурации AI-агентов (Claude, Codex, Copilot, Gemini) в репозитории BioETL. Используется при:
- Онбординге нового репозитория
- Аудите текущей конфигурации после миграции
- Добавлении нового AI-агента

---

## Промт

> Скопируй текст ниже (от `---BEGIN---` до `---END---`) и передай AI-агенту.

---BEGIN---

Проведи аудит и настройку AI-агентов в репозитории.

### Контекст репозитория

Репозиторий использует несколько AI-агентов параллельно. Структура AI-конфигурации:

#### Корень проекта
- `AGENTS.md` — единственный AI-файл в корне (инструкции для OpenAI Codex / общий)
- CLAUDE.md, CODEX.md, GEMINI.md — НЕ в корне, находятся в `docs/00-project/ai/agents/`

#### Каноническое хранилище (SSOT)

    docs/00-project/ai/
    ├── agents/                        ← Документация агентов
    │   ├── guides/                    ← Инструкции: CLAUDE.md, CODEX.md, GEMINI.md, AGENT.md
    │   ├── orchestration/             ← ORCHESTRATION.md, py-team-orchestration.md
    │   ├── runtime/                   ← Оперативные промты: py-qa-orchestrator, py-diagram-docs-orchestrator, agent-memory
    │   ├── policy/                    ← Политики именования и стандарты агентов
    │   ├── audit/                     ← Отчёты аудита и консолидации
    │   └── snapshots/                 ← Исторические снапшоты (non-SSOT, read-only)
    ├── skills/                        ← Скилы
    │   ├── global/                    ← Кросс-проектные скилы (py-audit-bot, py-test-bot, ...)
    │   ├── local/                     ← Проектно-специфичные скилы (py-test-swarm, documentation-cascade-audit, ...)
    │   ├── _references/               ← Общие справочные материалы для скилов
    │   └── collected/                 ← Исторические снапшоты скилов (non-SSOT)
    ├── prompts/                       ← Промты оркестрации
    │   ├── architecture_debt_reduction_orchestration.md
    │   ├── refactor_orchestration_prompt.md
    │   ├── refactor_orchestration_prompt_1-2.md
    │   ├── architecture_metric_exemptions_tasks_json_prompt.md
    │   ├── scripts_inventory_consolidation_cleanup_prompt.md
    │   ├── ai_workspace_setup.md      ← Этот промт
    │   └── collected/                 ← Исторические промты (non-SSOT)
    └── memory/                        ← Память агентов
        ├── agent-memory.md            ← Общий контекст проекта
        ├── memory-py-{name}.md        ← Специализированная память субагента
        └── mcp-memory.json            ← MCP knowledge graph (semantic memory)

**Приоритет при расхождениях:**
- Runtime-реестры (`.claude/agents/`, `.codex/agents/`) > docs mirror (`docs/00-project/ai/agents/`)
- `guides/` содержит канонические версии инструкций агентов
- `snapshots/` и `collected/` — read-only архивы, НЕ редактировать

#### Dot-директории агентов (runtime-конфигурации)

    .claude/              ← Claude Code: settings.json, rules/, commands/, agents/, skills/
    .codex/               ← OpenAI Codex: config.toml, settings.json, agents/, skills/
    .gemini/              ← Gemini: GEMINI.md, settings.json
    .github/              ← Copilot: copilot-instructions.md

### Задачи аудита

#### 1. Инвентаризация файлов

##### 1a. Инструкции агентов

Канонические инструкции — в `docs/00-project/ai/agents/guides/`:

| Агент | Guide (SSOT) | Runtime config |
|-------|-------------|----------------|
| Claude | `guides/CLAUDE.md` | `.claude/` (settings, rules, commands) |
| Codex | `guides/CODEX.md` | `.codex/` (config.toml, settings) |
| Gemini | `guides/GEMINI.md` | `.gemini/` (GEMINI.md, settings) |
| Copilot | — | `.github/copilot-instructions.md` |
| Jules (общая персона) | `guides/AGENT.md` | — |

Проверка:

    # Проверить что guides/ содержит канонические файлы
    ls docs/00-project/ai/agents/guides/

##### 1b. Подпапки agents/

| Папка | Назначение | Проверка |
|-------|------------|----------|
| `guides/` | Канонические инструкции агентов | `ls docs/00-project/ai/agents/guides/` |
| `orchestration/` | Оркестрация субагентов (ORCHESTRATION.md) | `ls docs/00-project/ai/agents/orchestration/` |
| `runtime/` | Оперативные промты (qa-orchestrator, diagram-docs) | `ls docs/00-project/ai/agents/runtime/` |
| `policy/` | Политики именования агентов | `ls docs/00-project/ai/agents/policy/` |
| `audit/` | Отчёты аудита конфигурации | `ls docs/00-project/ai/agents/audit/` |
| `snapshots/` | Архивные снапшоты (read-only) | `ls docs/00-project/ai/agents/snapshots/` |

##### 1c. Подпапки skills/

| Папка | Назначение | Проверка |
|-------|------------|----------|
| `global/` | Кросс-проектные скилы (py-audit-bot, py-test-bot, ...) | `ls docs/00-project/ai/skills/global/` |
| `local/` | Проектно-специфичные (py-test-swarm, documentation-cascade-audit) | `ls docs/00-project/ai/skills/local/` |
| `_references/` | Общие справочные материалы | `ls docs/00-project/ai/skills/_references/` |
| `collected/` | Исторические снапшоты скилов (non-SSOT) | — |

Проверка:

    # Проверить структуру скила (каждый должен иметь SKILL.md)
    for d in docs/00-project/ai/skills/global/*/; do
      [ -f "$d/SKILL.md" ] && echo "OK: $d" || echo "MISSING: $d/SKILL.md"
    done

##### 1d. Промты (prompts/)

| Файл | Назначение |
|------|------------|
| `architecture_debt_reduction_orchestration.md` | Оркестрация снижения архитектурного долга |
| `refactor_orchestration_prompt.md` | Промт для рефакторинг-оркестрации |
| `refactor_orchestration_prompt_1-2.md` | Компактная версия (фазы 1-2) |
| `architecture_metric_exemptions_tasks_json_prompt.md` | Задачи рефакторинга metric exemptions |
| `scripts_inventory_consolidation_cleanup_prompt.md` | Инвентаризация и очистка скриптов |
| `ai_workspace_setup.md` | Этот промт (настройка AI workspace) |
| `COLLECTED_PROMPTS_INDEX.md` | Индекс архивных промтов |

##### 1e. Runtime-конфигурации vs SSOT

| Проверка | Команда |
|----------|---------|
| Settings.json корректен | Проверить MCP-серверы, plugins, paths |
| Память подключена | Все ссылки → `docs/00-project/ai/memory/` |
| Скилы синхронизированы | `.claude/skills/` ↔ `docs/00-project/ai/skills/` |
| Субагенты синхронизированы | `.claude/agents/py-*.md` ↔ `.codex/agents/py-*.md` |

#### 2. Проверка путей памяти

Все ссылки на память агентов ДОЛЖНЫ указывать на `docs/00-project/ai/memory/`.

    # Найти устаревшие ссылки на старые пути
    grep -rl "\.ai/memory/" .claude/ .codex/ .gemini/ docs/ --include="*.md" --include="*.json" | grep -v "collected"

    # Проверить MCP memory path в settings.json
    grep -r "MEMORY_FILE_PATH" .claude/settings.json .codex/settings.json .gemini/settings.json
    # Ожидание: docs/00-project/ai/memory/mcp-memory.json

Файлы памяти:

| Файл | Назначение |
|------|------------|
| `agent-memory.md` | Общий контекст проекта для всех агентов |
| `memory-py-audit-bot.md` | Import matrix, anti-patterns, naming, scoring |
| `memory-py-test-bot.md` | Test structure, thresholds, VCR, failure classification |
| `memory-py-doc-bot.md` | Doc structure, ADR, CHANGELOG, docstrings |
| `memory-py-debug-bot.md` | Error classification, debugging methodology, fix patterns |
| `memory-py-config-bot.md` | Config hierarchy, templates, ADR compliance |
| `memory-py-plan-bot.md` | RF-* routing, DAG, composite design, parallelization |
| `mcp-memory.json` | MCP knowledge graph (semantic memory) |

#### 3. Проверка MCP-серверов

Для каждого агента с MCP-поддержкой (Claude, Codex, Gemini) проверь:

| Сервер | Назначение | Ключевая настройка |
|--------|------------|--------------------|
| `memory` | Semantic knowledge graph | `MEMORY_FILE_PATH` → `docs/00-project/ai/memory/mcp-memory.json` |
| `github` | GitHub API | Токен через `gh auth token` или env var |
| `filesystem` | Доступ к файлам | Корень проекта |
| `sequential-thinking` | Chain-of-thought | Без настроек |

#### 4. Проверка плагинов

Claude Code plugins (в `.claude/settings.json` → `enabledPlugins`):

| Plugin | Назначение |
|--------|------------|
| `context7` | Документация библиотек |
| `code-review` | Ревью кода |
| `code-simplifier` | Упрощение кода |
| `feature-dev` | Разработка фичей |
| `agent-sdk-dev` | Разработка с Agent SDK |

#### 5. Проверка субагентов

Субагенты загружаются из `.claude/agents/` (Claude) и `.codex/agents/` (Codex).
Каждый субагент ДОЛЖЕН ссылаться на свой файл памяти:

    # Проверить что все py-* субагенты ссылаются на docs/00-project/ai/memory/
    for agent in .claude/agents/py-*.md; do
      name=$(basename "$agent" .md)
      if grep -q "docs/00-project/ai/memory/" "$agent"; then
        echo "OK: $name"
      else
        echo "FAIL: $name — нет ссылки на memory"
      fi
    done

#### 6. Проверка скилов

Скилы загружаются из `.claude/skills/` (Claude) и `.codex/skills/` (Codex).
SSOT скилов: `docs/00-project/ai/skills/`.

Каждый скил — директория с обязательной структурой:

    {skill-name}/
    ├── SKILL.md              ← Обязательный: описание, триггеры, workflow
    ├── agents/
    │   └── openai.yaml       ← Опционально: Codex-совместимый agent descriptor
    └── references/           ← Опционально: справочные материалы (templates, patterns)

**Скилы в `global/`** (кросс-проектные, BioETL субагенты):
- `py-audit-bot`, `py-test-bot`, `py-doc-bot`, `py-debug-bot`
- `py-config-bot`, `py-plan-bot`, `py-code-bot`
- `py-review-orchestrator`

**Скилы в `local/`** (проектно-специфичные):
- `py-test-swarm` (L1→L2→L3 иерархическое тестирование)
- `documentation-cascade-audit` (каскадный аудит документации)
- `technical-designer-mermaid` (Mermaid-диаграммы с ADR-040)

Проверка:

    # Проверить что активные скилы ссылаются на правильные пути памяти
    find .claude/skills/ .codex/skills/ -name "SKILL.md" -exec grep -l "\.ai/memory/" {} \;
    # Ожидание: пустой вывод (все обновлены)

    # Проверить синхронизацию SSOT ↔ runtime
    diff <(ls docs/00-project/ai/skills/global/) <(ls .codex/skills/ | grep "^py-")

#### 7. Проверка корневых файлов

| Файл | Расположение | Кто читает | SSOT |
|------|-------------|------------|------|
| `AGENTS.md` | Корень проекта | OpenAI Codex, generic agents | Сам файл (единственная копия) |
| `.github/copilot-instructions.md` | `.github/` | GitHub Copilot | Сам файл |
| `.gemini/GEMINI.md` | `.gemini/` | Gemini CLI | `docs/00-project/ai/agents/guides/GEMINI.md` |
| `.claude/PROJECT_CONTEXT.md` | `.claude/` | Claude Code (автозагрузка) | Сам файл |
| `.claude/rules/*.md` | `.claude/rules/` | Claude Code (автозагрузка) | Сами файлы |

Claude Code НЕ требует CLAUDE.md в корне — он читает `.claude/rules/` и `.claude/PROJECT_CONTEXT.md` автоматически.

#### 8. Ограничения (что НЕЛЬЗЯ изменить)

| Ограничение | Причина |
|-------------|---------|
| Claude auto-memory path (`C:\Users\{USER}\.claude\projects\...\memory\MEMORY.md`) | Хардкодирован в Claude Code |
| `.claude/rules/` location | Claude Code загружает rules только из `.claude/rules/` |
| `.claude/commands/` location | Slash-команды работают только из `.claude/commands/` |
| `AGENTS.md` в корне | Codex ищет его именно там |
| `.github/copilot-instructions.md` | Copilot ищет его именно там |

### Формат отчёта

    ## AI Workspace Audit Report

    **Дата**: YYYY-MM-DD
    **Репозиторий**: {repo}

    ### Статус агентов

    | Агент | Инструкции | Settings | Memory | MCP | Статус |
    |-------|:----------:|:--------:|:------:|:---:|:------:|
    | Claude | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | OK/ISSUE |
    | Codex | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | OK/ISSUE |
    | Copilot | ✅/❌ | — | — | — | OK/ISSUE |
    | Gemini | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | OK/ISSUE |

    ### Субагенты (Claude/Codex)

    | Субагент | Memory ref | Статус |
    |----------|:----------:|:------:|
    | py-audit-bot | ✅/❌ | OK/FIX |
    | py-test-bot | ✅/❌ | OK/FIX |
    | ... | | |

    ### Обнаруженные проблемы

    1. {описание} → {рекомендация}

    ### Действия

    - [ ] {что нужно сделать}

---END---

---

## Вариации использования

### Быстрый аудит (только проверка)

> Выполни только задачи 1-2 из промта AI Workspace Setup.
> Покажи отчёт, НЕ вноси изменений.

### Полный аудит + исправление

> Выполни полный аудит по промту AI Workspace Setup.
> Исправь найденные проблемы. Покажи отчёт с diff-ами.

### Добавление нового AI-рантайма (Claude, Codex, Copilot, Gemini, ...)

> Добавь поддержку рантайма {NAME} по шаблону из AI Workspace Setup.
>
> 1. Создай guide: `docs/00-project/ai/agents/guides/{NAME}.md`
> 2. Создай runtime-конфиг: `.{name}/` (settings.json, инструкционный файл)
> 3. Подключи MCP memory если поддерживается

### Добавление нового субагента (py-*-bot)

> Добавь субагент {name} по шаблону из AI Workspace Setup.
>
> 1. Создай agent prompt: `.claude/agents/{name}.md` + `.codex/agents/{name}.md`
> 2. Создай скил:
>    - `docs/00-project/ai/skills/global/{name}/SKILL.md` (SSOT)
>    - `.claude/skills/{name}/SKILL.md` (runtime copy)
>    - `.codex/skills/{name}/SKILL.md` (runtime copy)
> 3. Создай файл памяти: `docs/00-project/ai/memory/memory-{name}.md`
> 4. Добавь в ORCHESTRATION.md (`docs/00-project/ai/agents/orchestration/` + `.claude/agents/`)
> 5. Добавь в `agent-orchestration-rules.md` (`.claude/rules/`)

### Шаблон файла памяти для нового субагента

> Создай файл памяти для субагента {name}:

    # Memory: {name}

    *Version: 1.0.0 | Date: YYYY-MM-DD | Parent: agent-memory.md*

    > **Focus**: {краткое описание специализации}

    ---

    ## 1. Identity & Scope

    - **Role**: {роль}
    - **Write zone**: {разрешённые пути для записи}
    - **Output artifacts**: {артефакты}
    - **ID system**: `{PREFIX}-001`, `{PREFIX}-002`, ...
    - **Model**: {opus/sonnet/haiku}

    ---

    ## 2. {Специализированные знания}

    {Правила, матрицы, команды, относящиеся к специализации субагента}

    ---

    ## 3. Common Pitfalls

    {Типичные ошибки и как их избежать}
