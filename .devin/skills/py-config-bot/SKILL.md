---
name: py-config-bot
description: "Validate or fix existing BioETL YAML configs, schemas, and pipeline contracts. For a new provider or entity pipeline, use new-pipeline."
---

# py-config-bot

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Primary profile: `../../agents/py-config-bot/AGENT.md`
- Team orchestration: `../../agents/ORCHESTRATION.md`
- Shared wrapper contract: [../py-audit-bot/references/wrapper-contract.md](../py-audit-bot/references/wrapper-contract.md)
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`
- Role memory: `../../../docs/00-project/ai/memory/memory-py-config-bot.md`

## Trigger Scope

Use this wrapper for existing config and schema work, drift, DQ contracts, generation inputs, and related audit closeout.
Use `new-pipeline` when scaffolding a pipeline for a new provider or a new entity.

## Workflow

1. Follow the shared wrapper contract.
1. Read and apply `../../agents/py-config-bot/AGENT.md`.
1. Locate related configs, schema validators, generated artifacts, and docs.
1. Keep generated baselines and docs synchronized when config behavior changes.

## Expected Output

- Changed config/schema surfaces or audit-confirmed no-op.
- Validation commands and outcomes.
- Explicit note when generated artifacts were refreshed.

## Validation

Prefer focused config gates such as `python -m scripts.schema validate-configs`,
`python -m scripts.schema check-invariants`, or the narrower command named by
the impacted config family.

## Fallback

If schema tooling is unavailable, report the exact skipped command and do not
claim config closure.
