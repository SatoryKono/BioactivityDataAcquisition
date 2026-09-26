> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/new-pipeline/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "new-pipeline"
description: "Scaffold a new BioETL provider/entity pipeline with configs, transformer registration, docs, tests, and baseline verification checks. Use only when the user asks to add a new provider/entity pipeline or extend the pipeline catalog."
---

# New Pipeline

## Objective

Create a new ETL pipeline for a provider/entity pair in BioETL.

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`

- Canonical runtime entrypoint: this `SKILL.md`
- Shared wrapper contract: [../py-audit-bot/references/wrapper-contract.md](../py-audit-bot/references/wrapper-contract.md)

## Trigger Scope

Use this wrapper for a new provider/entity pipeline, not for normal pipeline bug
fixes. Confirm provider, entity, source API, expected medallion layers, and
configuration ownership before writing files.

## Workflow

1. Follow the shared wrapper contract.
1. Read `../../../docs/00-project/ai/memory/agent-memory.md`, then the matching
   `memory-py-*.md` sheet when one exists for the active role, and use memory
   plus repo search to discover related configs, tests, contract docs, and
   diagrams before scaffolding.
1. If source examples are shell-specific, adapt commands to the current shell/environment.
1. Keep generated code/config aligned with project architecture rules in `AGENTS.md`.
1. Add or update configs, transformer registration, tests, docs, and generated
   baselines as one coherent change.
1. Before finalizing, re-scan for impacted tests, contract surfaces, config
   validators, docs, and runtime mirrors affected by the scaffold.
1. Run verification commands from this skill (or closest working equivalents in this environment).

## Expected Output

- Provider/entity pipeline surfaces created or updated.
- Config and schema validation evidence.
- Focused tests and docs/generator updates.

## Validation

Prefer provider/entity focused tests plus config/schema gates:

```bash
python -m scripts.schema validate-configs
python -m scripts.schema check-invariants
```

Add focused pytest nodes for the new extractor, transformer, and pipeline
registration.

## Fallback

If source API details or entity contracts are unknown, stop at a scaffold plan
and ask for the missing contract rather than generating speculative pipeline
logic.
