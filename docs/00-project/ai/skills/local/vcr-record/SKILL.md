______________________________________________________________________

## name: vcr-record description: Record, validate, update, and clean VCR cassettes for BioETL HTTP tests with secret-safety checks.

# VCR Record

## Objective

Manage VCR cassette lifecycle for provider integration tests.

## Source Of Truth

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
