# BioETL Instructions for GitHub Copilot

Use this file as a strict operating profile for code suggestions in this repository.

## Canonical Sources

- `docs/00-project/RULES.md` (project constitution, RFC2119 requirements)
- `docs/01-requirements/REQUIREMENTS.md` (functional/non-functional requirements)
- ADRs in `docs/02-architecture/decisions/`
- `AGENTS.md` (assistant workflow constraints)
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

If guidance conflicts, prioritize canonical sources over this file.
For AI runtime behavior conflicts, follow the runtime-source-first precedence
defined in `AGENTS.md`.

## AI Runtime Notes

- `.codex/**` is the tracked runtime source of truth on `main`.
- `.gemini/settings.json` may exist as a machine-local config surface, but a
  tracked `.gemini/agents/**` or `.gemini/skills/**` tree is not part of the
  current `main` checkout unless added and verified in the same change.
- `docs/00-project/ai/**` is a mirror/guidance layer, not the runtime behavior source.
- Do not rely on `.claude/**` as a canonical behavior source for Codex/Gemini work.

## Architecture Guardrails (MUST)

### Hexagonal import boundaries

- `domain` must not import `application` or `infrastructure`.
- `application` must not import `infrastructure`.
- `infrastructure` may import domain ports/types/exceptions.
- Ports must be imported via `bioetl.domain.ports` facade.

### Domain purity

- No I/O in domain (`httpx`, `requests`, `open()`, DB clients, `structlog`).
- No side effects at module import time in domain/application.

### Dependency injection

- Use constructor injection.
- Do not instantiate concrete adapters in domain/application classes.
- Keep wiring/factories in `src/bioetl/composition/`.

### Medallion constraints

- Bronze: raw immutable ingestion artifacts.
- Silver: Delta Lake only (no raw parquet fallback).
- Gold: curated business-level outputs.

## Anti-Patterns (MUST NOT Suggest)

- Layer boundary violations for quick fixes.
- Service locator pattern.
- Hardcoded secrets, tokens, or credentials.
- `print()` for runtime logging (use logger ports/structlog adapters).
- Blocking I/O inside async code.
- Replacing strict typing with broad `Any` to silence type errors.

## Hallucination Prevention (MUST)

- Do not invent files, modules, classes, commands, or Make targets.
- Before referencing a path/command/API, verify it exists in the repo context.
- If uncertain, state uncertainty and suggest verification steps.
- Keep code changes minimal and evidence-based; avoid speculative refactors.

## Suggestion Quality Checklist

- Includes type annotations for public interfaces.
- Preserves architecture constraints and naming conventions.
- Adds/updates tests when behavior changes.
- Uses memory plus repo search to identify related tests, docs, contracts, and
  configs before narrowing the validation scope.
- Mentions required verification commands (`make lint`, `make test`, architecture tests).
- Includes migration notes when introducing breaking changes.
