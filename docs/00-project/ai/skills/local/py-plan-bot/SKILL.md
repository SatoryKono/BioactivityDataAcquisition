> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/py-plan-bot/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "py-plan-bot"
description: "Execute the BioETL py-plan-bot profile for scoped implementation, refactor, audit-remediation, or release plans. Use when the user asks for a plan or when findings need sequencing before edits."
---

# py-plan-bot

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Primary profile: `../../agents/py-plan-bot.md`
- Team orchestration: `../../agents/ORCHESTRATION.md`
- Shared wrapper contract: [../py-audit-bot/references/wrapper-contract.md](../py-audit-bot/references/wrapper-contract.md)
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`
- Role memory: `../../../docs/00-project/ai/memory/memory-py-plan-bot.md`

## Trigger Scope

Use this wrapper when the requested work needs sequencing, dependency ordering,
explicit scope control, or conversion of audit findings into a plan.

## Workflow

1. Follow the shared wrapper contract.
1. Read and apply `../../agents/py-plan-bot.md`.
1. Separate implementation, validation, docs/mirror sync, and closeout steps.
1. Keep the plan bounded by the user's requested scope.

## Expected Output

- Ordered plan with clear completion criteria.
- Risks, blockers, and validation gates.
- No implementation unless the user also asked to proceed.

## Validation

Plans are validated by source inspection: every proposed step must map to a real
file, command, test, config, doc, or issue.

## Fallback

If planning inputs are incomplete, state the assumptions and mark decisions that
require user input before implementation.
