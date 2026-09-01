---
id: prompt.audit.project.new2.normalization
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
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - docs/04-reference/normalization/reference-identifiers.md
  - docs/04-reference/normalization/chembl-normalization-overview.md
  - src/bioetl/domain/normalization/_reference_id_normalizers.py
  - src/bioetl/domain/ports/data_normalization.py
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Identifier formats invented outside published policy
  - Locale/decimal heuristics without tests
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Raising debt budgets
tags: [audit, normalization, identifiers, domain, cycle, operator]
summary: Cyclic identifier/normalization audit — DOI, ChEMBL, UniProt, SMILES policies vs code, ALLOW_* true, early-stop
max_body_lines: 220
---

# Cyclic normalization / identifier audit

DOI, ChEMBL ID, UniProt, PubChem CID, SMILES, InChI — policy vs
`domain/normalization`. Не DQ Gold schema (см. dq-contracts).
Loop: `prompt.audit.orchestrator`. Library defaults: **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `src/bioetl/domain/normalization/ docs/04-reference/normalization/` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/norm-cycle-new2-<shortsha>` |

## Anchors

- `docs/04-reference/normalization/reference-identifiers.md`
- Provider overviews (ChEMBL, PubChem, UniProt, publications)
- Port: `domain/ports/data_normalization.py`
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. `run_id = <UTC>-norm-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
3. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Families** | Map identifier families in docs vs normalizer modules. |
| **B Enforce** | Regex/trim/NA policy vs tests. Undocumented heuristics. |
| **C Drift** | Docs claim without code; code without policy. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[norm][<REQ-id>][P#]`. |
| **E Fix** | Policy+code together; tests for format. |
| **F Validate** | Normalization unit tests. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.

## Success

- Family coverage matrix
- No undocumented identifier mutation
