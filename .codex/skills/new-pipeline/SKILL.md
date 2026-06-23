---
name: "new-pipeline"
description: "Scaffold a new BioETL provider/entity pipeline with configs, transformer registration, and baseline verification checks."
---

# New Pipeline

## Objective

Create a new ETL pipeline for a provider/entity pair in BioETL.

## Source Of Truth

- Canonical runtime entrypoint: this `SKILL.md`
- Project rules: `../../../AGENTS.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## Workflow

1. Follow this skill file as the canonical Codex runtime instructions.
1. Read `../../../docs/00-project/ai/memory/agent-memory.md`, then the matching
   `memory-py-*.md` sheet when one exists for the active role, and use memory
   plus repo search to discover related configs, tests, contract docs, and
   diagrams before scaffolding.
1. If source examples are shell-specific, adapt commands to the current shell/environment.
1. Keep generated code/config aligned with project architecture rules in `AGENTS.md`.
1. Before finalizing, re-scan for impacted tests, contract surfaces, config
   validators, docs, and runtime mirrors affected by the scaffold.
1. Run verification commands from this skill (or closest working equivalents in this environment).

## Notes

- Treat this file as canonical for the runtime workflow and verification sequence.
