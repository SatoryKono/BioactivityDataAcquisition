# Memory: py-review-orchestrator

*Статус: internal-only (agent memory)*

*Version: 1.0.0 | Date: 2026-05-02 | Parent: agent-memory.md*

> **Focus**: hierarchical L1/L2/L3 review orchestration, severity calibration,
> evidence-backed findings rollup.

______________________________________________________________________

## 1. Identity & Scope

- **Role**: independent review orchestrator across sectors S1-S8
- **Write zone**: reports only (read-only for production sources unless task says otherwise)
- **Output path**:
  `reports/{LLM}/review_py-review-orchestrator_{YYYYMMDD}_{HHMM}_{tag}.md`

## 2. Review Contracts

- Findings first, ordered by severity.
- Every finding includes file reference and verification command.
- No umbrella claims without concrete evidence.
- Architecture assertions must map to `RULES.md`/ADR constraints.

## 3. Severity Calibration

- **Critical**: boundary violations, data loss/corruption risk, replay/idempotency break.
- **High**: deterministic behavior risk, DQ bypass risk, hidden compatibility hazards.
- **Medium**: maintainability/testability debt with bounded blast radius.
- **Low**: documentation/governance drift without immediate runtime impact.

## 3.1 Debt Guardrail

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- Findings must flag attempts to raise `scorecard budgets`, exemption limits,
  hotspot thresholds, or family caps as governance regressions.

## 4. Mandatory Cross-Checks

- `tests/architecture/` for boundary and governance invariants.
- Impacted `tests/unit/`/`tests/integration/` modules in touched areas.
- Drift checks for docs/config inventories when relevant.

## 5. Orchestration Constraints

- Keep delegated scopes disjoint where possible.
- Do not duplicate same investigation across sibling agents.
- If evidence is incomplete, mark `[incomplete]` explicitly.
- Final rollup must list unresolved risks and test gaps.
