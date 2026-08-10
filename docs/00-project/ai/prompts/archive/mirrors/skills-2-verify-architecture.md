# Verify Architecture

## Evaluation Metadata
- **Category:** Skills
- **Weighted Score:** 8.02 / 10
- **Overall Rating:** High
- **Path:** .codex/skills/verify-architecture/SKILL.md

## Evaluation Breakdown
- Clarity: 8/10 (weight: 0.15)
- Completeness: 8/10 (weight: 0.15)
- Specificity: 8/10 (weight: 0.12)
- Context: 8/10 (weight: 0.10)
- Guardrails: 8/10 (weight: 0.10)
- Maintainability: 7/10 (weight: 0.08)
- Reusability: 8/10 (weight: 0.08)
- Error Handling: 7/10 (weight: 0.08)
- Validation: 9/10 (weight: 0.07)
- Documentation: 8/10 (weight: 0.07)

## Original Content

---
name: "verify-architecture"
description: "Run BioETL architecture compliance checks in quick, full, or category mode before commit, PR, merge, or architecture debt closeout."
---

# Verify Architecture

## Objective

Execute architecture validation checks and report blocking/non-blocking issues.

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Canonical runtime entrypoint: this `SKILL.md`
- Shared wrapper contract: [wrapper-contract.md](../../../../.codex/skills/py-audit-bot/references/wrapper-contract.md)
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

## Memory Integration

Follow `docs/00-project/ai/agents/guides/MEMORY_USAGE.md` and use the canonical memory workflow from `src/memory/DAILY_WORKFLOW.md`.

## Post-Change Validation

After any edits to this skill:
1. Re-scan impacted code/config/doc/runtime surfaces
2. Use repo search plus memory/evidence anchors to find related tests, docs, contracts, configs, and workflows
3. Edit runtime source first, then sync docs mirrors when behavior or contributor guidance changed
4. Run the shared wrapper contract validation
5. Report checks run, skipped checks, and mirror-sync status
