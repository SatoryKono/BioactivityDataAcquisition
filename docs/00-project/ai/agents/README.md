# AI Agents Context

Этот каталог содержит документацию по агентам для разных рантаймов AI в BioETL.

## Canonical Sources (SSOT)

| Runtime | Canonical path | Notes |
| --- | --- | --- |
| Claude Code | `.claude/agents/` | Основной реестр профилей Claude |
| Codex | `.codex/agents/` | Основной реестр профилей Codex |
| Docs mirror | `docs/00-project/ai/agents/` | Документационный слой, не runtime-реестр |

При расхождении между runtime-реестром и docs приоритет у runtime-реестра.

## Structure

| Zone | Path | Purpose |
| --- | --- | --- |
| Guides | [guides/](guides/) | Инструкции для конкретных ассистентов |
| Runtime docs | [runtime/](runtime/) | Канонические docs-артефакты агентных prompt/workflow |
| Policy | [policy/](policy/) | Политики именования и стандарты |
| Audit | [audit/](audit/) | Отчёты аудита и консолидации |
| Snapshots | [snapshots/](snapshots/) | Исторические/собранные снапшоты (non-SSOT) |
| Aliases | [aliases/](aliases/) | Документация compatibility-слоя |

## Canonical Documents

| Document | File | Purpose |
| --- | --- | --- |
| Jules Guide | [guides/AGENT.md](guides/AGENT.md) | Основной инженерный гайд и workflow |
| Claude Guide | [guides/CLAUDE.md](guides/CLAUDE.md) | Практики для Claude при работе с репозиторием |
| Codex Guide | [guides/CODEX.md](guides/CODEX.md) | Инструкции Architecture Auditor + Implementation Engineer |
| Gemini Guide | [guides/GEMINI.md](guides/GEMINI.md) | Профильный набор правил и ограничений для Gemini |
| QA Orchestrator | [runtime/py-qa-orchestrator.md](runtime/py-qa-orchestrator.md) | Prompt для иерархического QA-оркестратора |
| Diagram Docs Orchestrator | [runtime/py-diagram-docs-orchestrator.md](runtime/py-diagram-docs-orchestrator.md) | Оркестратор обновления/rerender диаграммных docx/pdf |
| Agent Memory (quick) | [runtime/agent-memory.md](runtime/agent-memory.md) | Краткая оперативная память по проекту |
| Team Orchestration | [runtime/orchestration/py-team-orchestration.md](runtime/orchestration/py-team-orchestration.md) | Адаптированная docs-копия оркестрации |

## Snapshot Zone

Папка [snapshots/collected/](snapshots/collected/) содержит снапшот материалов для аудита/истории и не является SSOT.

- Индекс снапшота: [snapshots/COLLECTED_AGENTS_INDEX.md](snapshots/COLLECTED_AGENTS_INDEX.md)
- Scope текущего снапшота: в основном `.claude/agents/*` + связанные артефакты
- Правило: содержимое snapshot-дерева не редактируется вручную

## Audit Reports

- [audit/AUDIT_CONSOLIDATION_REPORT_2026-03-08.md](audit/AUDIT_CONSOLIDATION_REPORT_2026-03-08.md)
- [policy/AGENT_NAMING_POLICY_AND_RENAME_PLAN_2026-03-08.md](policy/AGENT_NAMING_POLICY_AND_RENAME_PLAN_2026-03-08.md)

## Compatibility

Legacy paths are retained as deprecated stubs:

- `AGENT.md`, `CLAUDE.md`, `CODEX.md`, `GEMINI.md`
- `agent-memory.md`, `memory.md`
- `py-qa-orchestrator.md`, `qa_orchestrator.md`
- `py-diagram-docs-orchestrator.md`, `diagram_docs_orchestrator.md`
- `orchestration/ORCHESTRATION.md`, `orchestration/py-team-orchestration.md`

See [aliases/README.md](aliases/README.md).

## Notes

- `docs/00-project/RULES.md` остаётся canonical source RFC 2119 требований.
- При конфликте инструкций приоритет: System/Developer/User > локальные инструкции агента.
