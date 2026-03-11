---
name: vcr-record
description: Record, validate, update, and clean VCR cassettes for BioETL HTTP tests with secret-safety checks.
---

# VCR Record

*Статус: internal-published (Internal / Extended)*

## Objective
Manage VCR cassette lifecycle for provider integration tests.

## Source Of Truth
- Codex SSOT: `.codex/skills/vcr-record/SKILL.md`
- Claude runtime: `.claude/commands/vcr-record.md`

## Workflow
1. Open and follow the SSOT skill file for your active runtime.
2. Adapt shell examples to the current environment when needed.
3. Always include cassette validation and secret sanitization checks.
4. Prefer repository-local commands (`uv run ...`) consistent with project standards.

## Notes
- The `.codex/skills/` directory contains the canonical action modes (`record`, `list`, `validate`, `update`, `clean`).
