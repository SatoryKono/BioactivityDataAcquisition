---
id: prompt.audit.project.new2.providers
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
  - PROVIDER
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
  - configs/providers/chembl.yaml
  - configs/README.md
  - .codex/skills/new-pipeline/SKILL.md
  - src/bioetl/infrastructure/adapters/http/client.py
  - docs/00-project/governance/04-extending-bioetl.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Config without matching adapter / entity YAML
  - ${ENV_VAR} in tracked provider YAML
  - New provider without skill/checklist
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Raising debt budgets
tags: [audit, providers, adapters, configs, cycle, operator]
summary: Cyclic provider catalog audit — YAML vs adapters vs entities, ALLOW_* true, early-stop
max_body_lines: 230
---

# Cyclic provider / entity catalog audit

Семь провайдеров (`chembl`, `pubchem`, `uniprot`, `pubmed`, `openalex`,
`crossref`, `semanticscholar`). Не общий YAML-цикл configs. Skill:
**new-pipeline**. Loop: `prompt.audit.orchestrator`.
Library defaults: **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `configs/providers/ configs/entities/ src/bioetl/infrastructure/adapters/` |
| `PROVIDER` | `all` or one id |
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
| `WORK_BRANCH` | `fix/providers-cycle-new2-<shortsha>` |

## Anchors

- Hierarchy: base → provider → entity → composite (`configs/README.md`)
- Extending: `docs/00-project/governance/04-extending-bioetl.md`
- Named env indirection only; no `${ENV_VAR}` in tracked YAML
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. If `PROVIDER!=all`, restrict SCOPE to that provider.
3. `run_id = <UTC>-providers-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Catalog** | List providers in YAML vs adapter packages vs entity files. |
| **B Parity** | Missing adapter, orphan YAML, composite without entities. |
| **C Secrets/HTTP** | Env names; reuse unified HTTP client (defer deep retry to http-clients card). |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[providers][<REQ-id>][P#]`. |
| **E Fix** | Smallest owner-file change. New pipelines via skill checklist. |
| **F Validate** | Config/adapter tests for touched providers. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1 → STOP.

## Success

- Provider matrix: yaml / adapter / entity / gap
- No secret interpolation in tracked YAML
