---
id: prompt.audit.project.new.telemetry
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
  - MONITORING
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
  - docs/00-project/RULES.md
  - docs/04-reference/observability/metrics-catalog.md
  - docs/03-guides/dashboards/metrics-readiness-matrix.md
  - grafana/prometheus-rules
  - grafana/dashboards
  - .codex/skills/observability-prometheus/SKILL.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Inventing Prometheus series so a panel looks full
  - Starting docker-compose.monitoring.yml without MONITORING=true
  - Putting run_id in Prometheus labels
  - Data FAIL from a screenshot (belongs to dashboards cycle)
  - Empty vs zero treated as the same alerting state
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
tags: [audit, observability, telemetry, metrics, prometheus, cycle, operator]
summary: Improved cyclic telemetry audit — instrumentation to recording rules, MONITORING fail-closed, early-stop
max_body_lines: 230
---

# Improved cyclic observability / data-plane audit

Улучшает `prompt.audit.cycle.telemetry` + контур
`prompt.observability.grafana-audit.data-integrity` (lineage only, не visual).
Skill: **observability-prometheus**. Visual/layout → `prompt.audit.project.new.dashboards`.

Library defaults: **`ALLOW_*=true`**, **`MONITORING=false`**.
Не стартовать `docker-compose.monitoring.yml` без явного OK оператора.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `src/bioetl/observability grafana/prometheus-rules grafana/prometheus.yml docs/04-reference/observability` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `MONITORING` | `false` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/telemetry-cycle-new-<shortsha>` |

## Anchors

- Catalog: `docs/04-reference/observability/metrics-catalog.md`
- Inventory: `python -m scripts.engineering.qa report-observability-metric-inventory --json`
- Rules: `grafana/prometheus-rules/` + `grafana/prometheus-rules/tests/`
- Health `/metrics` must not put `run_id` in Prometheus labels
- PROVEN finding MUST have `requirement_id`
- Windows: `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. Do **not** start monitoring unless `MONITORING=true` and operator approved.
3. `run_id = <UTC>-telemetry-new-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Lineage** | For shipped panels in SCOPE: instrumentation → scrape/export → recording rule → queryable series. Missing series ≠ invent names. |
| **B Rules** | Alert/recording rules vs catalog; unit tests under `grafana/prometheus-rules/tests/`. |
| **C Cardinality** | Review runtime cardinality reports when present. `run_id` label → P0/P1. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[telemetry][<REQ-id>][P#]`. |
| **E Fix** | Minimal metric/rule/docs. Do not “fill” dashboards with fake series. |
| **F Validate** | Re-run inventory/rule tests in SCOPE. Live scrape only if MONITORING=true. Close only on `origin/main` if ALLOW_CLOSE. |

If MONITORING=false, live gaps are `Not Verifiable` + blocker, not dashboard defects.

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1 и без new invented metrics → STOP.

## Success

- Lineage table for in-scope panels
- Rule tests recorded; no `run_id` Prom labels
- Monitoring stack not started unless authorized
