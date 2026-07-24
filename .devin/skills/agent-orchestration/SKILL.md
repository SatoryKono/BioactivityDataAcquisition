---
name: agent-orchestration
description: Coordinate BioETL multi-agent workflow across py-\* profiles using the Codex-local orchestration map.
---

# Agent Orchestration

## Objective

Coordinate complex tasks across agent profiles (`py-*`) with clear handoffs and artifacts.

## Source Of Truth
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Orchestration map: `.codex/agents/ORCHESTRATION.md` (v4.3, 2026-07-24)
- Agent profiles: `.codex/agents/py-\*.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Memory sheets: `../../../docs/00-project/ai/memory/memory-py-*.md`
- Daily workflow: `../../../src/memory/DAILY_WORKFLOW.md`

## Workflow

1. Load `.codex/agents/ORCHESTRATION.md` (v4.3).
1. Read the memory policy (`MEMORY_USAGE.md`) and daily workflow (`DAILY_WORKFLOW.md`).
1. Retrieve relevant shared/role-specific memory context via `python -m memory.tooling.workflow pre-task ...`.
1. Select path (full/quick/config/doc) based on task scope.
1. Route to corresponding `py-*` profile skills for each phase using memory sheets (`memory-py-*.md`).
1. Keep artifacts and verification steps aligned with the selected path.
1. Run `python -m memory.tooling.workflow post-task ...` after task completion.
1. Promote only durable lessons to curated memory.
