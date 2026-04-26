______________________________________________________________________

## name: vcr-record description: Record, validate, update, and clean VCR cassettes for BioETL HTTP tests with secret-safety checks.

# VCR Record

*Статус: internal-published (Internal / Extended)*

## Objective

Manage VCR cassette lifecycle for provider integration tests.

## Source Of Truth

- Codex SSOT: `.codex/skills/vcr-record/SKILL.md`
- Runtime mirrors: published docs or runtime-specific registries may exist, but Codex SSOT controls current workflow.

## Workflow

1. Open and follow the SSOT skill file for your active runtime.
1. Adapt shell examples to the current environment when needed.
1. Always include cassette validation and secret sanitization checks.
1. Prefer repository-local commands (`uv run ...`) consistent with project standards.

## Notes

- The `.codex/skills/` directory contains the canonical action modes (`record`, `list`, `validate`, `update`, `clean`).
