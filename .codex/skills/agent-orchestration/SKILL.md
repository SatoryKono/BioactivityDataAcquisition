______________________________________________________________________

## name: agent-orchestration description: Coordinate BioETL multi-agent workflow across py-\* profiles using the Codex-local orchestration map.

# Agent Orchestration

## Objective

Coordinate complex tasks across agent profiles (`py-*`) with clear handoffs and artifacts.

## Source Of Truth

- Orchestration map: ../../agents/ORCHESTRATION.md
- Agent profiles: ../../agents/py-\*.md
- Root runtime contract: ../../../AGENTS.md
- Memory policy: ../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md

## Workflow

1. Load `../../agents/ORCHESTRATION.md`.
1. Read the memory policy and retrieve the relevant shared/role-specific memory context.
1. Select path (full/quick/config/doc) based on task scope.
1. Route to corresponding `py-*` profile skills for each phase.
1. Keep artifacts and verification steps aligned with the selected path.
