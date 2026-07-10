> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/py-doc-bot/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "py-doc-bot"
description: "Execute the BioETL py-doc-bot profile for documentation updates, docs drift remediation, runtime mirror sync, and documentation validation. Use when work primarily changes docs or contributor guidance."
---

# py-doc-bot

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
- Primary profile: `../../agents/py-doc-bot.md`
- Team orchestration: `../../agents/ORCHESTRATION.md`
- Shared wrapper contract: [../py-audit-bot/references/wrapper-contract.md](../py-audit-bot/references/wrapper-contract.md)
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`
- Role memory: `../../../docs/00-project/ai/memory/memory-py-doc-bot.md`

## Trigger Scope

Use this wrapper for docs edits, doc drift, docs generated artifact refresh,
runtime mirror updates, and documentation validation.

## Workflow

1. Follow the shared wrapper contract.
1. Read and apply `../../agents/py-doc-bot.md`.
1. Verify cited code/config/runtime surfaces directly.
1. Update runtime source first, then docs mirrors when runtime behavior changes.

## Expected Output

- Docs changed or drift audit result.
- Claim-to-source verification summary.
- Mirror-sync status.

## Validation

Use targeted docs checks such as `python -m scripts.docs check-links` and
`python -m scripts.docs check-drift --runtime-mirrors --freshness`.

## Fallback

If docs validation is too broad for the environment, report the skipped command
and keep claims limited to files inspected directly.
