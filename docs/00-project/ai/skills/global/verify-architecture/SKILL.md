> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source:
> - Gemini: `.gemini/skills/verify-architecture/SKILL.md`
> Governance: [AI Runtime Mirror Ownership](../../../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md), [Memory Usage](../../../agents/guides/MEMORY_USAGE.md), [Post-Change Validation](../../../agents/policy/POST_CHANGE_VALIDATION.md).
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

## name: verify-architecture description: Run architecture compliance checks for BioETL (quick/full/category modes) before commit or PR.

# Verify Architecture

*Статус: internal-published (Internal / Extended)*

## Objective

Execute architecture validation checks and report blocking/non-blocking issues.

## Source Of Truth

- Codex SSOT: `.codex/skills/verify-architecture/SKILL.md`
- Runtime mirrors: published docs or runtime-specific registries may exist, but Codex SSOT controls current workflow.

## Workflow

1. Open and follow the SSOT skill file for your active runtime.
1. Select mode (`quick`, `full`, `category`) based on request scope.
1. Adapt command examples to the active shell and installed toolchain.
1. Report findings with failing tests/checks and actionable next fixes.

## Notes

- The `.codex/skills/` directory is canonical for test groupings and command sets.
