> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source:
> - Codex: `.codex/skills/verify-architecture/SKILL.md`
> Governance: [AI Runtime Mirror Ownership](../../../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md), [Memory Usage](../../../agents/guides/MEMORY_USAGE.md), [Post-Change Validation](../../../agents/policy/POST_CHANGE_VALIDATION.md).
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

## name: verify-architecture description: Run architecture compliance checks for BioETL (quick/full/category modes) before commit or PR.

# Verify Architecture

## Objective

Execute architecture validation checks and report blocking/non-blocking issues.

## Source Of Truth
- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../../../02-architecture/decisions`
- Primary instructions: `../../../.codex/skills/verify-architecture/SKILL.md`

## Workflow

1. Open and follow `../../../.codex/skills/verify-architecture/SKILL.md`.
1. Select mode (`quick`, `full`, `category`) based on request scope.
1. Adapt command examples to the active shell and installed toolchain.
1. Report findings with failing tests/checks and actionable next fixes.

## Notes

- The Codex skill file is canonical for test groupings and command sets.
