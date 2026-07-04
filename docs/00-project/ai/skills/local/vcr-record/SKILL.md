> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source:
> - Codex: `.codex/skills/vcr-record/SKILL.md`
> Governance: [AI Runtime Mirror Ownership](../../../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md), [Memory Usage](../../../agents/guides/MEMORY_USAGE.md), [Post-Change Validation](../../../agents/policy/POST_CHANGE_VALIDATION.md).
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

## name: vcr-record description: Record, validate, update, and clean VCR cassettes for BioETL HTTP tests with secret-safety checks.

# VCR Record

## Objective

Manage VCR cassette lifecycle for provider integration tests.

## Source Of Truth

- Root runtime contract: `../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Primary instructions: `../../../.codex/skills/vcr-record/SKILL.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## Workflow

1. Open and follow `../../../.codex/skills/vcr-record/SKILL.md`.
1. Adapt shell examples to the current environment when needed.
1. Always include cassette validation and secret sanitization checks.
1. Prefer repository-local commands (`uv run ...`) consistent with project standards.

## Notes

- The Codex skill file contains the canonical action modes (`record`, `list`, `validate`, `update`, `clean`).
