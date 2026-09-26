---
applyTo: "src/bioetl/infrastructure/**"
---

# BioETL Infrastructure Layer (Copilot)

Canonical sources:

- `docs/00-project/RULES.md` §1, §4–§5 (adapters, HTTP, retry)
- ADR-032 (`UnifiedHTTPClient`)
- ADR-017 / ADR-019 (observability)

## MUST

- Implement ports; keep business decisions in domain/application.
- Use UnifiedHTTPClient + sanctioned retry/rate-limit policy for external APIs.
- Use structured logging ports/adapters (no `print()`).

## MUST NOT

- Embed domain business rules in adapters.
- Introduce parallel HTTP client stacks without ADR.
- Log secrets, tokens, or full env maps.
