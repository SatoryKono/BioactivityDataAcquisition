# Русский промт: аудит и исправление AI-workspace

Источник: `docs/00-project/ai/prompts/codex/ai-workspace-audit-and-fix.md`
Назначение: аудит и безопасное выравнивание AI-конфигурации BioETL.

## Промт

Ты — Codex, выполняющий роль аудитора и оператора настройки AI-workspace в репозитории BioETL.

Используй локальные файлы и вывод команд как источник истины. Работай по циклу: `инвентаризация -> аудит -> безопасное исправление -> проверка -> отчёт`.

### Цель

Провести аудит и выровнять конфигурацию AI-агентов для Claude, Codex, Copilot и Gemini, не затрагивая production-код.

### Scope

Включено:

- `docs/00-project/ai/**`
- `.claude/**`
- `.codex/**`
- `.gemini/**`
- `.github/copilot-instructions.md`
- `.vscode/mcp.json`, если это нужно для выравнивания MCP

Исключено:

- `src/bioetl/**`

### Правила SSOT

Если источники расходятся, используй такой приоритет:

1. `.claude/agents/` и `.codex/agents/` важнее, чем docs-mirror в `docs/00-project/ai/agents/agents/`.
2. `docs/00-project/ai/agents/guides/` — каноническое docs-layer расположение инструкций агентов.
3. `.codex/skills/` — SSOT для локальных skills; `docs/00-project/ai/skills/` — mirror.
4. `docs/00-project/ai/prompts/collected/` — архив, а не SSOT.
5. Все memory-ссылки должны указывать на `docs/00-project/ai/memory/`.

### Рабочий протокол

#### Фаза 1. Инвентаризация

Собери evidence-backed инвентарь для:

- agent guides
- runtime-директорий агентов
- skills и их mirrors
- prompts и collected prompts
- memory-файлов и MCP-ссылок
- root-level AI entry points

Для каждого расхождения зафиксируй:

- путь
- тип проблемы
- severity
- evidence
- рекомендуемое исправление

#### Фаза 2. Аудит согласованности

Проверь как минимум:

- все memory-ссылки ведут в `docs/00-project/ai/memory/`
- MCP memory config указывает на `docs/00-project/ai/memory/mcp-memory.json`
- `guides/` содержит канонический набор инструкций
- локальные skills синхронизированы с runtime-набором там, где это ожидается
- deprecated alias-файлы явно помечены
- root AI-файлы лежат в ожидаемых местах

#### Фаза 3. Безопасные исправления

Разрешены только низкорисковые правки:

- исправление путей
- обновление stale references
- синхронизация docs mirrors
- нормализация MCP-путей
- уточнение статуса deprecated/reference-only файлов

Запрещено:

- менять `src/bioetl/**`
- удалять файлы без сильного evidence
- переносить runtime-managed пути в неподдерживаемые locations

#### Фаза 4. Проверка

После каждого change-set перепроверь:

- консистентность memory-путей
- консистентность MCP-путей
- синхронизацию skill mirrors
- memory-ссылки у subagents
- отсутствие новых broken references

### Итоговый отчёт

1. Краткая сводка инвентаризации
2. Таблица findings: `Severity | Path | Problem | Evidence | Action`
3. Список внесённых изменений
4. Выполненные проверки и их результаты
5. Оставшиеся риски и manual follow-ups
