> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/agent-orchestration/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "agent-orchestration"
description: "Coordinate BioETL multi-agent workflow across py-\\* profiles using the Codex-local orchestration map."
---

# Agent Orchestration

## Objective

Coordinate complex tasks across agent profiles (`py-*`) with clear handoffs and artifacts.

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`

- Orchestration map: ../../agents/ORCHESTRATION.md
- Agent profiles: ../../agents/py-\*.md

## Workflow

1. Load `../../agents/ORCHESTRATION.md`.
1. Read the memory policy and retrieve the relevant shared/role-specific memory context.
1. Select path (full/quick/config/doc) based on task scope.
1. Route to corresponding `py-*` profile skills for each phase.
1. Keep artifacts and verification steps aligned with the selected path.
