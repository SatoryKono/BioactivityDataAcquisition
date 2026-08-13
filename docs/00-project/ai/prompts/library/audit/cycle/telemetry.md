---
id: prompt.audit.cycle.telemetry
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
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/RULES.md
  - docs/04-reference/observability/metrics-catalog.md
  - docs/03-guides/dashboards/metrics-readiness-matrix.md
  - grafana/prometheus-rules
  - grafana/dashboards
  - .codex/skills/observability-prometheus/SKILL.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing Prometheus series so a panel looks full
  - Starting docker-compose.monitoring.yml without MONITORING=true
  - Putting run_id in Prometheus labels
  - Data FAIL from a screenshot (that belongs to dashboards cycle)
  - Empty vs zero treated as the same alerting state
  - Empty form cycles
tags: [audit, observability, telemetry, metrics, prometheus, cycle, operator]
summary: Cyclic audit of observability instrumentation and dashboard data feed
max_body_lines: 260
---

# Cyclic observability / dashboard-feed audit

N-итерационный аудит **наблюдаемости и сбора данных для наполнения дашбордов**.
Это **data-plane**, не визуал. Цель: у каждой shipped-панели есть доказуемый путь

`instrumentation → scrape/export → recording rule → queryable series`.

Не изобретать metric names. Плотность, типографика, render — это
`prompt.audit.cycle.dashboards`.

Skill: `observability-prometheus`. Loop shell: `prompt.audit.orchestrator`.
Default **`N=10`**, **`MODE=full`**, **`MONITORING=false`**, все **`ALLOW_*=true`**.
Пустые циклы запрещены. ADR-010: monitoring stack не стартовать без явного OK.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `src/bioetl/infrastructure/observability src/bioetl/observability grafana/prometheus-rules grafana/prometheus.yml grafana/provisioning docs/04-reference/observability docs/03-guides/dashboards/metrics-readiness-matrix.md reports/observability` |
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

## BioETL anchors

- ADR-017 / ADR-019 / ADR-022 (NoOp tracing); RULES §3.2
- Catalog: `docs/04-reference/observability/metrics-catalog.md`
- Inventory: `python -m scripts.engineering.qa report-observability-metric-inventory --json`
- Rules: `grafana/prometheus-rules/bioetl.yml`,
  `bioetl_observability.yml`, `bioetl_control_plane_current_status.yml`
- Rule tests: `grafana/prometheus-rules/tests/`
- Readiness: `docs/03-guides/dashboards/metrics-readiness-matrix.md`
- Cardinality: `reports/observability/runtime_cardinality_*.json`
- Health `/metrics` must not put `run_id` in Prometheus labels
- Windows: `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA; branch. Foreign dirty work → worktree.
2. Confirm SCOPE paths exist; empty SCOPE → STOP.
3. Do **not** start `docker-compose.monitoring.yml` unless `MONITORING=true`
   and the operator approved UI/scrape work.
4. `run_id = <UTC>-telemetry-cycle-<shortsha>`
5. Artifacts: `reports/audit-runs/<run_id>/` + mirror `reports/audit/telemetry/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | Registered names vs catalog vs recording rules vs dashboard PromQL. Use the inventory command when present. Do not invent series. |
| **B Coverage matrix** | Table `panel \| query \| metric/rule \| labels \| ready? \| blocker`. Expected Empty ≠ missing series. HTTP control-plane sources are valid when the readiness matrix says so. |
| **C Instrumentation** | Ports vs adapters (ADR-017/019). NoOp tracing path (ADR-022). Histogram / counter / gauge misuse. Retired hyphenated names / alias drift. |
| **D Cardinality / rules** | Label explosion. `promtool` + repo rule tests when available. Empty vs zero are different alerting states. |
| **E Issues / Fix** | Fix the **owner** surface (code, rule, or catalog). Do not edit dashboard JSON “to look full” without series evidence. No new `run_id` labels. |
| **F Validate** | Re-run inventory / rule tests on the touched set. Delta: resolved / unchanged / regressed / new. |

## Focus checklist (each cycle)

- [ ] No invented metric names
- [ ] Every first-screen panel has a readiness row
- [ ] Expected Empty documented (healthy empty ≠ defect)
- [ ] `run_id` absent from Prometheus labels
- [ ] Recording rules covered by repo tests or an explicit gap
- [ ] Cardinality review attached or residual tracked
- [ ] Monitoring stack not started unless MONITORING=true
- [ ] Dashboard JSON not used as a substitute for missing series

## Stop

Invent a series “so the panel fills” → P0 method break.
Start monitoring without `MONITORING=true` → STOP.
Secret/token in metric labels or rules → P0.
Empty SCOPE → STOP.

## Success

- Coverage matrix + `findings.json` + `report.md` under the run dir
- Touched rules/instrumentation re-checked
- Readiness matrix not silently diverged from shipped queries
- `surface_score` 0–3; cap at 1 if any P0 remains

## Related

- Skill: `.codex/skills/observability-prometheus/SKILL.md`
- Visual follow-up: `prompt.audit.cycle.dashboards`
- Closeout: `prompt.closeout.grok`
- Previous: `prompt.audit.cycle.architecture` · Next: `prompt.audit.cycle.dashboards`
