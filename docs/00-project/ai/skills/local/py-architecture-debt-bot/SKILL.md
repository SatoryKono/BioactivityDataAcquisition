> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/py-architecture-debt-bot/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "py-architecture-debt-bot"
description: "Execute the full BioETL architecture-debt reduction workflow: generate tasks from the exemptions registry, build an execution plan, coordinate targeted debt reduction, and close with verification across py-test-bot, py-config-bot, py-doc-bot, and py-audit-bot."
---

# py-architecture-debt-bot

## Objective

Run the role-specific workflow as defined in the py-architecture-debt-bot profile.

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`

- Canonical runtime entrypoint: this `SKILL.md`
- Team orchestration: `../../../.codex/agents/ORCHESTRATION.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`
- Role-specific memory: `../../../docs/00-project/ai/memory/memory-py-architecture-debt-bot.md`
- Deterministic helpers:
  - `python -m scripts.qa generate-debt-tasks`
  - `python -m scripts.qa reduce-architecture-debt`

## Workflow

1. Start with the canonical memory loop from `../../../src/memory/DAILY_WORKFLOW.md` and run `python -m memory.tooling.workflow pre-task ...` for the debt-reduction task.
1. Read `MEMORY_USAGE.md`, `agent-memory.md`, and
   `memory-py-architecture-debt-bot.md` before planning the wave.
1. Treat this skill file as the canonical Codex runtime profile for the workflow.
1. Use the deterministic helpers before editing code or delegating subagents.
1. Keep `configs/` mutations delegated to `py-config-bot`.
1. Close every debt-reduction wave with `py-test-bot`, `py-doc-bot`, and `py-audit-bot`.
1. After closeout, run `python -m memory.tooling.workflow post-task ...` and promote only durable debt-reduction lessons or architecture incidents.
