> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/verify-architecture/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "verify-architecture"
description: "Run BioETL architecture compliance checks in quick, full, or category mode before commit, PR, merge, or architecture debt closeout."
---

# Verify Architecture

## Objective

Execute architecture validation checks and report blocking/non-blocking issues.

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
- Canonical runtime entrypoint: this `SKILL.md`
- Shared wrapper contract: [../py-audit-bot/references/wrapper-contract.md](../py-audit-bot/references/wrapper-contract.md)
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`

## Trigger Scope

Use this wrapper when a task needs architecture verification after structural
edits, before PR/merge, or for architecture debt closeout. It is a validation
skill, not an audit replacement.

## Workflow

1. Follow the shared wrapper contract.
1. Use memory plus repo search to locate related architecture tests, ADRs,
   docs, diagrams, and evidence reports before choosing validation scope.
1. Select mode (`quick`, `full`, `category`) based on request scope.
1. Adapt command examples to the active shell and installed toolchain.
1. Report findings with failing tests/checks and actionable next fixes.

## Expected Output

- Selected mode and rationale.
- Commands run and outcomes.
- Failing checks with actionable next fixes.

## Validation Modes

- `quick`: focused architecture tests for touched surfaces.
- `category`: named architecture family, for example config, docs drift,
  runtime mirrors, import boundaries, or inventory.
- `full`: broad `tests/architecture` sweep when requested or needed by risk.

## Fallback

If a full architecture run is too slow for the current environment, run the
focused category checks and report the skipped full command exactly.
