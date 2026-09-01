---
id: prompt.audit.project.new2.control-plane
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
  - docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md
  - docs/02-architecture/decisions/ADR-046-checkpoint-vs-ledger-resume.md
  - docs/02-architecture/decisions/ADR-047-workflow-control-plane.md
  - docs/04-reference/contracts/run-manifest-ledger.md
  - docs/03-guides/workflows.md
  - src/bioetl/composition/control_plane_runtime.py
  - src/bioetl/application/services/control_plane/workflow/ledger_service.py
  - src/bioetl/application/services/control_plane/workflow/manifest_service.py
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Treating Prometheus dashboards as control-plane evidence
  - Resume that ignores ledger/checkpoint contract
  - Admin force without fencing/lock evidence
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Raising debt budgets
tags: [audit, control-plane, manifest, ledger, replay, cycle, operator]
summary: Cyclic control-plane audit — RunManifest/Ledger, resume/repair, ALLOW_* true, early-stop
max_body_lines: 230
---

# Cyclic control-plane audit

ADR-044 / ADR-046 / ADR-047. Не Grafana (`dashboards`) и не raw metrics
(`telemetry`). Loop: `prompt.audit.orchestrator`.
Library defaults: **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `src/bioetl/application/services/control_plane/ src/bioetl/composition/control_plane_runtime.py` |
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
| `WORK_BRANCH` | `fix/control-plane-cycle-new2-<shortsha>` |

## Anchors

- Contract: `docs/04-reference/contracts/run-manifest-ledger.md`
- CLI/ops: `docs/03-guides/workflows.md`, `docs/04-reference/cli.md`
- Composition seam: `control_plane_runtime.py`
- Checkpoint vs ledger resume (ADR-046)
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. SCOPE exists; empty → STOP.
3. `run_id = <UTC>-cp-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Surfaces** | Manifest, ledger, inspection, replay/resume, force/repair. Map CLI verbs. |
| **B Invariants** | Resume contract vs checkpoint; fencing/lock; no silent skip of required persistence. |
| **C Drift** | Docs/runbook claims vs code. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[control-plane][<REQ-id>][P#]`. |
| **E Fix** | Minimal service/composition change. |
| **F Validate** | Focused control-plane tests. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1 → STOP.

## Success

- Resume/repair claims evidenced in code
- No dashboard-only “control-plane PASS”
