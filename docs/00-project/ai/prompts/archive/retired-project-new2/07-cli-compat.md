---
id: prompt.audit.project.new2.cli-compat
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
  - docs/04-reference/cli.md
  - src/bioetl/interfaces/cli/main.py
  - src/bioetl/__main__.py
  - configs/quality/config_compatibility_registry.yaml
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Silent public CLI/API/schema breaks without migration note
  - Reintroducing retired shims as canonical
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Raising debt budgets
tags: [audit, cli, compatibility, entrypoints, cycle, operator]
summary: Cyclic public CLI/HTTP/entrypoint compatibility audit — freeze, shims, ALLOW_* true, early-stop
max_body_lines: 220
---

# Cyclic CLI / public surface compatibility audit

Публичный CLI и HTTP boundary. Не control-plane internals (см. new2.control-plane).
Loop: `prompt.audit.orchestrator`. Library defaults: **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `src/bioetl/interfaces/ docs/04-reference/cli.md` |
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
| `WORK_BRANCH` | `fix/cli-compat-cycle-new2-<shortsha>` |

## Anchors

- Dispatch: `interfaces/cli/main.py`, `python -m bioetl`
- Operator docs: `docs/04-reference/cli.md`
- Compatibility: `configs/quality/config_compatibility_registry.yaml`
- Breaking change → migration note + version policy (RULES §8)
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. `run_id = <UTC>-cli-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
3. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | Commands, flags, HTTP health/readiness. Compare to cli.md. |
| **B Freeze** | Removed/renamed flags without migration. Retired shims revived. |
| **C Compat registry** | Expired/sunset aliases vs live CLI. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[cli][<REQ-id>][P#]`. |
| **E Fix** | Docs or compatibility path; no silent drops. |
| **F Validate** | CLI/help tests in SCOPE. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.

## Success

- CLI↔docs drift table
- No silent public break
