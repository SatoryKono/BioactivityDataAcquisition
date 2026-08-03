---
applyTo: "src/bioetl/domain/**"
---

# BioETL Domain Layer (Copilot)

Canonical sources (read these; do not invent parallel rules):

- `docs/00-project/RULES.md` §1 (hexagonal boundaries, domain purity)
- `docs/00-project/NORMATIVE_SOURCES.md`
- ADR-048 (schema-contract representation in domain)
- `AGENTS.md` (runtime precedence, post-change validation)

## MUST

- Keep domain free of I/O, HTTP, DB, env access, and concrete logging.
- Prefer ports/interfaces over infrastructure adapters.
- Use typed value objects and explicit contracts; avoid broad `Any`.

## MUST NOT

- Introduce service locator / global mutable state.
- Increase technical-debt budgets or weaken architecture gates.
- Hardcode secrets or credentials.
- Bypass UnifiedHTTPClient or call providers from domain.
