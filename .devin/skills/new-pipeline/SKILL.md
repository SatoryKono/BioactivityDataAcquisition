---
name: new-pipeline
description: Scaffold a new BioETL provider/entity pipeline with configs, transformer registration, and baseline verification checks.
---

# New Pipeline

## Objective

Create a new ETL pipeline for a provider/entity pair in BioETL.

## Source Of Truth
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Canonical runtime entrypoint: this `SKILL.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## Environment Configuration

This skill may use provider API keys from the repository root `.env` file when scaffolding
pipelines for providers that require authentication:

- `BIOETL_UNIPROT_API_KEY` - UniProt API key (if scaffolding UniProt pipeline)
- `BIOETL_OPENALEX_API_KEY` - OpenAlex API key (if scaffolding OpenAlex pipeline)
- `BIOETL_PUBMED_API_KEY` - PubMed API key (if scaffolding PubMed pipeline)
- `BIOETL_SEMANTICSCHOLAR_API_KEY` - Semantic Scholar API key (if scaffolding Semantic Scholar pipeline)
- `BIOETL_CROSSREF_EMAIL` - CrossRef email (if scaffolding CrossRef pipeline)

**Note:** Provider API keys are optional for scaffolding. The skill will create placeholder
configuration that can be filled later. The `.env` file is machine-local and secret-bearing.

## Workflow

1. Follow this skill file as the canonical Codex runtime instructions.
1. Read `../../../docs/00-project/ai/memory/agent-memory.md`, then the matching
   `memory-py-*.md` sheet when one exists for the active role, and use memory
   plus repo search to discover related configs, tests, contract docs, and
   diagrams before scaffolding.
1. If source examples are shell-specific, adapt commands to the current shell/environment.
1. Keep generated code/config aligned with project architecture rules in `AGENTS.md`.
1. Before finalizing, re-scan for impacted tests, contract surfaces, config
   validators, docs, and runtime mirrors affected by the scaffold.
1. Run verification commands from this skill (or closest working equivalents in this environment).

## Notes

- Treat this file as canonical for the runtime workflow and verification sequence.
