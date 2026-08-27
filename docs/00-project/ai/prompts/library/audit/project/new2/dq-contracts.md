---
id: prompt.audit.project.new2.dq-contracts
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N
  - SCOPE
  - MODE
  - LANGUAGE
  - AUDIT_MODE
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
  - BASE_BRANCH
  - REPO
  - WORK_BRANCH
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/project-requirements-audit.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/RULES.md
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - docs/02-architecture/decisions/ADR-027-dq-rules-externalization.md
  - docs/02-architecture/decisions/ADR-045-dq-contract-system.md
  - docs/02-architecture/decisions/ADR-018-gold-strict-validation.md
  - docs/04-reference/contracts/dq-contracts.md
  - src/bioetl/domain/schemas/chembl/publication_term.py
  - src/bioetl/infrastructure/validation/pandera_validator.py
  - src/bioetl/infrastructure/validation/contract_validator.py
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Column/type mismatch with column_order treated as warning
  - Weakening Pandera so invalid Gold passes
  - Export without QC sidecars / meta.yaml checksums
  - Empty form cycles
  - ALLOW_* true by library default
  - Raising debt budgets
tags: [audit, dq, pandera, contracts, gold, cycle, operator]
summary: Cyclic DQ/Pandera contract audit — schemas, column_order, QC sidecars, fail-closed ALLOW, early-stop
max_body_lines: 230
---

# Cyclic DQ / Pandera / Gold contract audit

ADR-027 / ADR-045 / ADR-018. Не YAML-иерархия (`prompt.audit.project.new.configs`).
Loop: `prompt.audit.orchestrator`. Library defaults: **`ALLOW_*=false`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `src/bioetl/domain/schemas/ src/bioetl/infrastructure/validation/ docs/04-reference/contracts/` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `ALLOW_PUSH` | `false` |
| `ALLOW_MERGE` | `false` |
| `ALLOW_CLOSE` | `false` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/dq-cycle-new2-<shortsha>` |

## Anchors

- Pandera in `domain/schemas/` as contract; runtime validator in infrastructure
- Gold JSON: `docs/04-reference/contracts/gold/`
- Export: sort keys, `column_order` match, QC sidecars, `meta.yaml` checksums
- NA/NULL, identifier formats — explicit policy
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. SCOPE exists; empty → STOP.
3. `run_id = <UTC>-dq-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | Schemas vs Gold JSON vs `dq-contracts.md`. Missing unique/PK. |
| **B Enforce** | Validator wiring; fail-closed on type/column_order mismatch. |
| **C Export/QC** | Sidecars + meta.yaml claims vs code/docs. Deterministic order. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[dq][<REQ-id>][P#]`. |
| **E Fix** | Schema/validator/docs. No silent column adds. |
| **F Validate** | Schema/contract tests in SCOPE. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1 → STOP.

## Success

- Schema↔Gold drift table
- No weakened Gold validation to greenwash
