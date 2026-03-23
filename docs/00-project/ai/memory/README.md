# AI Memory Surface

*Статус: internal-published (Internal / Extended)*

Этот каталог хранит memory-артефакты для AI-рантаймов и role-specific agent
profiles в BioETL.

## Surface Model

- **Project memory entry point**:
  [agent-memory.md](agent-memory.md)
  — общий быстрый контекст по проекту, canonical docs anchors и operational
  shortcuts для новой AI-сессии.
- **Role-specific memory snapshots**:
  `memory-py-*.md`
  — focused memory sheets для отдельных агентных ролей; они наследуют
  project-level context из `agent-memory.md`, а не заменяют его.
- **Machine-readable memory artifact**:
  `mcp-memory.json`
  — служебный memory snapshot для tooling/integration сценариев, не human
  source of truth.

## Relationship To Other AI Surfaces

- Runtime orchestration и live agent registries остаются в
  `.codex/agents/` и `.claude/agents/`.
- Published mirror и assistant-facing guides живут в
  `docs/00-project/ai/agents/`.
- Prompts живут в `docs/00-project/ai/prompts/`.
- Skills и reference mirrors живут в `docs/00-project/ai/skills/`.

Если возникает конфликт между memory notes и runtime source, приоритет у
runtime source и canonical governance docs:

- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- accepted ADRs in `docs/02-architecture/decisions/`
- runtime registries in `.codex/agents/` and `.claude/agents/`

## Practical Reading Order

1. [agent-memory.md](agent-memory.md)
2. relevant `memory-py-*.md` file for the current role
3. `docs/00-project/ai/agents/` for guides and runtime-facing mirrors

## Notes

- This folder is **internal-published**, not a canonical runtime registry.
- Role-specific memory docs are retained for onboarding speed and task focus.
- When a memory note becomes stale, fix the note instead of silently treating it
  as normative truth.
