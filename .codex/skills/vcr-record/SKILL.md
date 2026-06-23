---
name: "vcr-record"
description: "Record, validate, update, and clean VCR cassettes for BioETL HTTP tests with secret-safety checks."
---

# VCR Record

## Objective

Manage VCR cassette lifecycle for provider integration tests.

## Source Of Truth

- Canonical runtime entrypoint: this `SKILL.md`
- Project rules: `../../../AGENTS.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## Workflow

1. Follow this skill file as the canonical Codex runtime instructions.
1. Adapt shell examples to the current environment when needed.
1. Always include cassette validation and secret sanitization checks.
1. Prefer repository-local commands (`uv run ...`) consistent with project standards.

## Notes

- The canonical action modes are `record`, `list`, `validate`, `update`, and `clean`.
