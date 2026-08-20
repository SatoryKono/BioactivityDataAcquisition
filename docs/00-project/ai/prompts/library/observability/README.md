______________________________________________________________________

Version: 1.2.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-08-20'

______________________________________________________________________

# Observability prompt folder

Operator-paste cards for BioETL Grafana / dashboard audits.
Not runtime SSOT. Precedence: `.codex/skills/observability-dashboard/` →
`AGENTS.md` → this folder.

Default for any card here: `MONITORING=false`, `LANGUAGE=ru`,
`ALLOW_ISSUE_WRITE=false`. Start `docker-compose.monitoring.yml` only when
the operator sets `MONITORING=true` and a live render is required.

Shared contract (DASH-* IDs, bands, §8 gates, ontology):
`fragments/dashboard-requirements-audit.md`. Do not also run
`prompt.audit.cycle.dashboards` as a second full pass on the same SHA.

## Sequential run (this folder)

Operator-paste orchestrator: `prompt.observability.sequential-run` (v1.1).
Run **once per checkout SHA**. Reuse one evidence pack. Do not invent
panels, UIDs, metrics, or live values. Dedupe against **closed** issues and
open fix PRs; do not open a third PR for the same root cause.

| Step | Card | Role | Skip when |
| ---: | --- | --- | --- |
| 0 | Shared inventory | `grafana/dashboards/*.json` + contracts | — |
| 1 | `prompt.observability.grafana-audit.master` | Evidence + unified backlog | — |
| 2 | `prompt.observability.grafana-audit.visual` | Palette / contrast / type | — |
| 3 | `prompt.observability.grafana-audit.layout` | Composition / IA / first screen | — |
| 4 | `prompt.observability.grafana-audit.data-integrity` | Lineage / queries / zero vs empty | live query optional |
| 5 | `prompt.observability.bi-dashboard-acceptance` | Visual / layout / data acceptance | — |
| 6 | `prompt.observability.dashboard-panel-audit` | 5 named phases, `CYCLE_COUNT=1` | — |
| 7 | `prompt.observability.dashboard-audit-cycle` | `N=1`, contours `density-area,density-scalar,fill,pipeline,fit` | write loops not authorized |
| 8 | `prompt.observability.grafana-audit.regression` | Baseline vs candidate | **no candidate change** |
| 9 | Final issue sweep | Close/BLOCKED vs `origin/main` | — |

`grafana-six/*` is **deprecated**. If an operator still pastes those cards,
map them and do **not** double-count findings:

| Deprecated | Successor |
| --- | --- |
| `grafana-six.evidence` | grafana-audit.master (evidence section) |
| `grafana-six.visual` | grafana-audit.visual |
| `grafana-six.layout` | grafana-audit.layout |
| `grafana-six.data` | grafana-audit.data-integrity |
| `grafana-six.consolidate` | grafana-audit.master backlog |
| `grafana-six.reverify` | grafana-audit.regression |
| `grafana-six.pack` | this README + grafana-audit.master |

## V5 residual pack (2026-08-18)

Full paste texts: `library/observability/dashboard-v5/`.
Do not reopen `#8944`–`#8948`. Default `MONITORING=false`.

| Id | Role |
| --- | --- |
| `prompt.observability.dashboard-v5.pack` | Route one leftover |
| `prompt.observability.dashboard-v5.implement` | Babysit `#8987` / optional R-D |
| `prompt.observability.dashboard-v5.closeout` | Close vs `origin/main` |
| `prompt.observability.dashboard-v5.audit-rf` | R-F light / 200% / NV |

## Focused cards (outside the numbered sequence)

- `prompt.observability.dashboard-operator-playbook` — для каждой панели:
  вопрос, связь с вопросом дашборда, маршрут оператора, 5–10 сценариев
  с выбором от значения (`STAY` / hop / CLI / bind). Артефакт в
  `reports/audit/observability-seq/`.
- `prompt.observability.dashboard-first-window-noscroll` — implement
  `DASH-FIT-004`: убрать внутренний scroll first-window `text`/`stat`/`table`
  на семи UID без overflow-clip и без роста `first_screen_max_panels`.
- `prompt.observability.dashboard-data-duplication` — по каждому UID 0–6:
  данные каждой панели, таксономия дублей внутри дашборда, план исключения
  без сноса `DASH-FIT-003` / `DASH-FIT-005`.
- `prompt.observability.dashboard-manual-validation` — focused/manual
  step for DASH-* rules that static pytest cannot prove (reflow, computed
  type, live FIT, render states). Default `MONITORING=false` → live rows
  are `Not Verifiable`, not defects. **Not** a second grafana-six pass;
  do not reopen `#8986`.
- `prompt.observability.dashboard-full-cycle` — unified **N=10** loop:
  (1) full audit of all seven UIDs (render, design, fill, panels, FIT,
  density, data, copy) → (2) GH issues per PROVEN root cause → (3)
  fix until close. STOP when step 2 creates **zero new** issues **and**
  no open issues with this `Cycle-run`. Do **not** also run
  `prompt.observability.sequential-run` or `prompt.audit.cycle.dashboards`
  as a second full pass on the same SHA.
- `prompt.observability.group-scalar-density-audit` — re-measure scalar
  information density per panel group vs first screen (`DASH-DENSITY-002`,
  REQUIREMENTS §5.4) and rank groups that must be made denser. Static (no
  monitoring); pairs with the `density` contour of step 7 and the survey
  `python -m scripts.engineering.qa report-dashboard-scalar-density`.

## Artifacts

```text
reports/audit/observability-seq/<utc>-obs-seq-<shortsha>/
  00-inventory.md
  01-grafana-audit-master.md
  …
  findings.json
  report.md
```

Per-card mirrors may also land under `reports/audit/grafana/` or
`reports/audit/grafana-panels/` when a card names that path.

## Guardrails

- Shipped JSON is structure SSOT. Screenshots do not prove data correctness.
- Distinguish: correct zero · expected empty · selector error · query error ·
  backend error · stale telemetry.
- Mark `FACT` / `INFERENCE` / `GAP` / `CONTRADICTION`.
- Live UI without `MONITORING=true` → `Not Verifiable`, not a dashboard defect.
- Do not raise debt budgets. Do not edit `.env`. Do not commit to `main`.
