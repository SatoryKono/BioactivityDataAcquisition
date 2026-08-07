---
name: "py-test-bot"
description: "Execute the BioETL py-test-bot profile for focused or broad test planning, failure classification, flaky-test triage, and coverage or regression validation."
---

# py-test-bot

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Primary profile: `../../agents/py-test-bot.md`
- Team orchestration: `../../agents/ORCHESTRATION.md`
- Shared wrapper contract: [../py-audit-bot/references/wrapper-contract.md](../py-audit-bot/references/wrapper-contract.md)
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
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
