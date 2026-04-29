______________________________________________________________________

## name: vcr-record description: Record, validate, update, and clean VCR cassettes for BioETL HTTP tests with secret-safety checks.

# VCR Record

## Objective

Manage VCR cassette lifecycle for provider integration tests.

## Source Of Truth

- Canonical runtime entrypoint: this `SKILL.md`
- Project rules: `../../../AGENTS.md`

## Workflow

1. Follow this skill file as the canonical Codex runtime instructions.
1. Adapt shell examples to the current environment when needed.
1. Always include cassette validation and secret sanitization checks.
1. Prefer repository-local commands (`uv run ...`) consistent with project standards.

## Notes

- The canonical action modes are `record`, `list`, `validate`, `update`, and `clean`.
