---
applyTo: "tests/**"
---

# BioETL Tests (Copilot)

Canonical sources:

- `docs/00-project/RULES.md` §4.2 (testing)
- ADR-042
- `AGENTS.md` post-change validation expectations

## MUST

- Prefer focused unit tests; use architecture tests for governance invariants.
- Keep fixtures/VCR free of secrets.
- Assert behavior, not private implementation accidents.

## MUST NOT

- Weaken assertions solely to green CI.
- Skip architecture gates by raising budgets/exemptions.
- Introduce flaky time/network coupling without seams/fakes.
