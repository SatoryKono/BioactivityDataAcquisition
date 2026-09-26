> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/py-test-bot/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "py-test-bot"
description: "Execute the BioETL py-test-bot profile for focused or broad test planning, failure classification, flaky-test triage, and coverage or regression validation."
---

# py-test-bot

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`

- Primary profile: `../../agents/py-test-bot.md`
- Team orchestration: `../../agents/ORCHESTRATION.md`
- Shared wrapper contract: [../py-audit-bot/references/wrapper-contract.md](../py-audit-bot/references/wrapper-contract.md)
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`

## Trigger Scope

Use this wrapper to choose, run, or interpret tests. It can also classify
failures and recommend the next debugging or implementation handoff.
Use `mode=focused` by default. Use `mode=broad` for the retired test-swarm
workflow: partition test domains, aggregate results, and keep one consolidated
report; do not create a separate routing skill.

## Workflow

1. Follow the shared wrapper contract.
1. Read and apply `../../agents/py-test-bot.md`.
1. Locate related tests before choosing scope.
1. Prefer the narrowest meaningful pytest node first.
1. Broaden to architecture/integration/golden checks when behavior or shared
   contracts are touched.

## Expected Output

- Test scope and rationale.
- Commands run and outcomes.
- Failure classification or pass evidence.

## Validation

Use repo wrappers when available, for example
`bash scripts/engineering/dev/run_pytest.sh <tests>`, or the platform-specific
equivalent from memory guidance.

## Fallback

If a suite times out or the environment blocks it, preserve the command and
failure mode exactly and do not report it as green.
