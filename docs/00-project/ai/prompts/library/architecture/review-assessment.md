---
id: prompt.architecture.review
version: 2.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [any]
params: [SCOPE, MODE, LANGUAGE]
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
related_ssot:
  - AGENTS.md
  - docs/00-project/RULES.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/02-architecture/decisions/
anti_patterns:
  - Drive-by refactors outside SCOPE
  - Raising debt budgets to “pass” review
  - Findings without path-level evidence
tags: [architecture, review, operator]
summary: Read-only architecture review and refactoring assessment
---

# Architecture review and refactoring assessment

Read-only review of hexagonal / medallion / DQ boundaries and a prioritized
refactor assessment. Default mode does **not** apply code changes.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | path cluster (e.g. `src/bioetl/domain`) |
| `MODE` | `read-only` \| `propose-patches` |
| `LANGUAGE` | `ru` |

## Focus

- Layer boundaries (domain / application / infrastructure / composition / interfaces)
- Constructor injection; no forbidden `interfaces → infrastructure` imports
- Medallion and DQ contracts only as they touch SCOPE
- Determinism, config/schema contracts, local-only default runtime

## Method

1. Inventory SCOPE modules and public ports
2. Compare against RULES §1–§2 and relevant ADRs (link only; do not paste full text)
3. List findings with severity + evidence
4. Propose refactor waves: impact, risk, test plan, debt effect (must not grow budgets)
5. If `MODE=propose-patches`: optional minimal patches only after operator approval

## Output

| Finding | Severity | Path | Claim | Evidence | Suggested wave |
| --- | --- | --- | --- | --- | --- |
