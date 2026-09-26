---
applyTo: "src/bioetl/composition/**"
---

# BioETL Composition Root (Copilot)

Canonical sources:

- `docs/00-project/RULES.md` §1 (Composition Root is the only concrete DI site)
- `AGENTS.md`

## MUST

- Perform concrete dependency wiring only here.
- Keep factories/builders explicit and testable.
- Prefer reusing existing registration helpers over new side registries.

## MUST NOT

- Hide service-locator style globals.
- Move business logic into composition.
- Increase tech-debt budgets to bypass architecture tests.
