---
name: vcr-record
description: Record, validate, update, and clean VCR cassettes for BioETL HTTP tests with secret-safety checks.
---

# VCR Record

## Objective

Manage VCR cassette lifecycle for provider integration tests.

## Source Of Truth
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Canonical runtime entrypoint: this `SKILL.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## Environment Configuration

This skill may use provider API keys from the repository root `.env` file when recording
VCR cassettes for providers that require authentication:

- `BIOETL_UNIPROT_API_KEY` - UniProt API key (if recording UniProt tests)
- `BIOETL_OPENALEX_API_KEY` - OpenAlex API key (if recording OpenAlex tests)
- `BIOETL_PUBMED_API_KEY` - PubMed API key (if recording PubMed tests)
- `BIOETL_SEMANTICSCHOLAR_API_KEY` - Semantic Scholar API key (if recording Semantic Scholar tests)
- `BIOETL_CROSSREF_EMAIL` - CrossRef email (if recording CrossRef tests)

**Note:** Provider API keys are only required when recording new cassettes. For playback
of existing cassettes, no API keys are needed. The `.env` file is machine-local and
secret-bearing.

## Workflow

1. Follow this skill file as the canonical Codex runtime instructions.
1. Adapt shell examples to the current environment when needed.
1. Always include cassette validation and secret sanitization checks.
1. Prefer repository-local commands (`uv run ...`) consistent with project standards.

## Notes

- The canonical action modes are `record`, `list`, `validate`, `update`, and `clean`.
