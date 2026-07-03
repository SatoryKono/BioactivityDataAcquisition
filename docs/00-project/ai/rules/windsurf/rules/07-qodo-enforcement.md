---
trigger: model_decision
description: "Qodo platform enforcement rules synced into Cursor guidance"
---

# Qodo Enforcement Rules

**Source:** Qodo platform `/rules/search` for `SatoryKono/BioactivityDataAcquisition`
**Synced:** 2026-07-03 (24 active rules)

These rules are integrated into thematic `.mdc` files (`00`–`06`). This file is the traceability index.

## Canonical Governance Links

- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`

## Qodo Platform Rules (24)

### Architecture

| Rule | Target file |
|------|-------------|
| Import port interfaces via `bioetl.domain.ports` facade | `00-architecture` |
| Define/abstract external deps as `*Port` Protocols in `bioetl.domain.ports` | `00-architecture` |
| Forbid I/O in domain-layer modules | `00-architecture` |
| Place dependency wiring and factories in composition layer | `00-architecture` |
| No side effects at import time in domain/application | `00-architecture` |
| Use structured logging via LoggerPort with structlog | `00-architecture` |

### Data Quality

| Rule | Target file |
|------|-------------|
| Validate Silver DataFrames with Pandera before write | `01-data-quality` |
| Validate Gold writes with strict Pandera (fail-closed) | `01-data-quality` |
| Store JSON-like fields as canonical JSON strings or NULL | `01-data-quality` |
| Preserve deterministic outputs (ordering, serialization, UTC) | `01-data-quality` |
| Avoid non-deterministic time and randomness in infrastructure | `01-data-quality` |

### Code Style

| Rule | Target file |
|------|-------------|
| Code must type-check cleanly with `mypy --strict` | `02-code-style` |

### Testing

| Rule | Target file |
|------|-------------|
| Enforce minimum 85% test coverage | `03-testing` |

### Agent Workflow

| Rule | Target file |
|------|-------------|
| Disallow hardcoded secrets, tokens, and credentials | `05-agent-workflow` |
| Never expose secrets in code, docs, configs, tests, or logs | `05-agent-workflow` |
| Do not increase technical debt budgets | `05-agent-workflow` |
| Require explicit approval before modifying `.env` files | `05-agent-workflow` |
| Refresh module coverage inventory hash on `src/bioetl` changes | `05-agent-workflow` |

## BioETL Local Extensions (not in current Qodo fetch)

| Rule | Target file |
|------|-------------|
| Require explicit type hints on public functions | `02-code-style` |
| Sanitize VCR cassettes from secrets before commit | `03-testing` |
| Ensure idempotent merge keyed by primary key | `01-data-quality` |
| Use atomic file writes (tmp then `os.replace`) | `01-data-quality` |
| Do not weaken `.env` secret-handling protections | `05-agent-workflow` |
| Schema/column/CLI changes need docs + changelog | `06-docs-standards` |

## Refresh

```bash
# Via Cursor skill: /qodo-get-rules
cp docs/00-project/ai/rules/cursor/*.mdc .cursor/rules/
uv run python scripts/ai/sync_windsurf_rules.py
```
