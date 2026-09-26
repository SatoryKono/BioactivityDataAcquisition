---
applyTo: "src/bioetl/application/**"
---

# BioETL Application Layer (Copilot)

Canonical sources:

- `docs/00-project/RULES.md` §1–§2 (application orchestration, Medallion stages)
- ADR-026 (Composite Pipeline Pattern)
- ADR-044 / ADR-046 / ADR-047 (control plane / replay)
- `AGENTS.md`, `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## MUST

- Orchestrate use-cases through ports; keep business rules out of adapters.
- Preserve determinism, idempotency, and replay-safe control-plane semantics.
- Prefer existing services/helpers over new parallel orchestration paths.

## MUST NOT

- Construct concrete infrastructure clients outside composition root.
- Mutate Bronze semantics or skip checkpoint/ledger contracts.
- Increase tech-debt / hotspot budgets.
