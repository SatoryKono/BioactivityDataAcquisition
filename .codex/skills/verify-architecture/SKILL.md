______________________________________________________________________

## name: verify-architecture description: Run architecture compliance checks for BioETL (quick/full/category modes) before commit or PR.

# Verify Architecture

## Objective

Execute architecture validation checks and report blocking/non-blocking issues.

## Source Of Truth

- Canonical runtime entrypoint: this `SKILL.md`
- Project rules: `../../../AGENTS.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`

## Workflow

1. Follow this skill file as the canonical Codex runtime instructions.
1. Use memory plus repo search to locate related architecture tests, ADRs,
   docs, diagrams, and evidence reports before choosing validation scope.
1. Select mode (`quick`, `full`, `category`) based on request scope.
1. Adapt command examples to the active shell and installed toolchain.
1. Report findings with failing tests/checks and actionable next fixes.

## Notes

- Treat this file as canonical for runtime trigger and mode selection.
