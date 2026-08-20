---
id: prompt.observability.sequential-run
version: 1.2.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - REPO
  - BASE
  - WORK_BRANCH
  - SCOPE
  - LANGUAGE
  - MONITORING
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_STEP
  - REQUIRE_GH_TRACKING
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/finding-schema.md
  - fragments/audit-scale.md
  - fragments/dashboard-requirements-audit.md
  - fragments/reports-output.md
related_ssot:
  - AGENTS.md
  - docs/01-requirements/DASHBOARD_REQUIREMENTS.md
  - docs/03-guides/dashboards/design-system.md
  - docs/03-guides/dashboards/verdict-ontology.md
  - docs/03-guides/dashboards/operator-ux-v2.md
  - grafana/dashboards
  - .codex/skills/observability-dashboard/SKILL.md
anti_patterns:
  - Running grafana-six/* as a second kit
  - Recreating closed issues that already have an open fix PR
  - Opening a third PR that duplicates an existing observability fix branch
  - Treating MONITORING=false live gaps as dashboard defects
  - Closing issues against unmerged PR heads as if they were on origin/main
  - Inventing DASH-* IDs that already exist in DASHBOARD_REQUIREMENTS.md
tags: [observability, dashboard, grafana, audit, sequential, operator]
summary: Sequential observability folder run — unique cards, issue/close gates, no full duplicates
max_body_lines: 280
---

# BioETL — последовательный запуск library/observability (v1.1)

Не runtime SSOT. Precedence: `.codex/skills/observability-dashboard/` →
`AGENTS.md` → `docs/01-requirements/DASHBOARD_REQUIREMENTS.md` → карточки папки.
Язык ответа: `{{LANGUAGE}}`. Технические литералы не переводить.

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE` | `origin/main` |
| `WORK_BRANCH` | `fix/observability-seq-<shortsha>` (never main) |
| `SCOPE` | `grafana/dashboards` |
| `LANGUAGE` | `ru` |
| `MONITORING` | `false` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `false` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_STEP` | `8` |
| `REQUIRE_GH_TRACKING` | `true` |

## TASK / MODE

TASK: исполнить уникальные карточки папки по порядку; после карточки без
нативного create/close — ISSUE GATE + CLOSEOUT GATE; в конце sweep.
MODE: implement. Не commit/push в `main`. Чужой dirty WIP — worktree.

## Жёсткие запреты

- Не запускать `grafana-six/*`.
- Не выдумывать UID/panel/metric/SLA/live values. Shipped JSON = structure SSOT.
- Не поднимать бюджеты техдолга. Не трогать `.env`.
- Не стартовать `docker-compose.monitoring.yml` при `MONITORING=false`.
- Скриншот не доказывает данные.
- Различать: valid zero · Expected Empty · selector error · query error ·
  backend error · stale telemetry.
- FACT / INFERENCE / GAP / CONTRADICTION. Issues только из PROVEN.
- Один issue на root cause / panel-cluster.
- Windows: только `.\.venv-win\Scripts\python.exe`.

## Пропуск полных дубликатов

| Deprecated | Преемник |
| --- | --- |
| `grafana-six.evidence` / `.consolidate` / `.pack` | master + этот оркестратор |
| `grafana-six.visual` | `grafana-audit.visual` |
| `grafana-six.layout` | `grafana-audit.layout` |
| `grafana-six.data` | `grafana-audit.data-integrity` |
| `grafana-six.reverify` | `grafana-audit.regression` |

Пересечения (исполнять, дедупить `uid+panel_id+requirement_id+root_cause`):
master vs specialists; BI-V/L/D vs grafana-audit; cycle (step 7) не повторяет
`render,visual,layout,data` — только `density-area,density-scalar,fill,pipeline,fit`.

## Уроки прогона 2026-08-14 (обязательны)

1. **Dedupe шире open issues.** Искать closed issues + open PRs за 14 дней
   (`allValue`, `color-background`, inventory, CB mappings). Не плодить
   второй тикет и третий PR.
2. **Inventory CONTRADICTION.** `dashboard-inventory.yaml` считает leaf;
   `report-dashboard-inventory --check` считает leaf+row. Не «чинить» оба
   числа в разные стороны. Один formula на прогон.
3. **`check-dashboard-visual-semantics` PASS ≠ нет visual дефектов.**
   Table-wide `color-background` и `allValue=$__all` на main проходили
   этот гейт. Смотри JSON напрямую + `DASH-AUTO-*` ниже.
4. **Closeout vs `origin/main`.** Issue закрывать как DONE только если
   acceptance виден на `origin/main` **или** оператор явно принял PR-head
   как evidence. Иначе `BLOCKED` + ссылка на PR. Уже закрытые не reopen.
5. **r2 без уникальных коммитов** не пушить. Candidate для regression —
   существующие fix PR, не пустая ветка.

## Каркас шага (1–8)

A. Прочитать карточку + includes. Read-only карточка не правит JSON во время аудита.
B. Dedupe по ledger + `gh issue list --state all` + open PRs.
C. **ISSUE GATE** только если нет native create
   (`dashboard-panel-audit` при `REQUIRE_GH_TRACKING=true`,
   `dashboard-audit-cycle` при `ALLOW_ISSUE_WRITE=true`).
   Иначе ≤ `MAX_ISSUES_PER_STEP` на PROVEN P0–P2 (P3 — только если блокирует роль).
D. **CLOSEOUT GATE** только если нет native close. Fix на `WORK_BRANCH`,
   не дублируя чужой open PR. `ALLOW_MERGE=false` по умолчанию.
E. `NO_ACTIONABLE_FINDINGS` → не выдумывать работу.
F. В ledger обязателен исход шага, даже `issues=0`.

## Последовательность

| Step | Card | Notes |
| ---: | --- | --- |
| 0 | Shared inventory | 7 UID; leaf **и** leaf+row; не создавать issues |
| 1 | `grafana-audit.master` | затем wrapper issues/close |
| 2 | `grafana-audit.visual` | wrapper |
| 3 | `grafana-audit.layout` | wrapper |
| 4 | `grafana-audit.data-integrity` | live query только при `MONITORING=true` |
| 5 | `bi-dashboard-acceptance` | `DEPTH=detailed` если `MONITORING=false` |
| 6 | `dashboard-panel-audit` | native 3–5; `CYCLE_COUNT=1` |
| 7 | `dashboard-audit-cycle` | `N=1`, `CONTOURS=density-area,density-scalar,fill,pipeline,fit` |
| 8 | `grafana-audit.regression` | только если есть candidate ≠ BASE |
| 9 | Final sweep | все issue# из ledger |

Статические гейты (step 0/7, не вместо карточек). Полный список — fragment
§8 / REQUIREMENTS §8. Minimum:

```text
python -m scripts.engineering.qa report-dashboard-inventory --check --json
python -m scripts.engineering.qa check-dashboard-visual-semantics
python -m scripts.engineering.qa check-dashboard-performance-budgets
python -m scripts.engineering.qa report-dashboard-scalar-density --check
```

`check-dashboard-visual-semantics` PASS ≠ нет visual-дефектов.
Не запускать `prompt.audit.cycle.dashboards` вторым полным проходом на том же SHA.

Focused/manual (вне шагов 1–8, не второй grafana-six):
`prompt.observability.dashboard-manual-validation` — DASH-REFLOW-001,
computed `DASH-TYPOGRAPHY-001`, live `DASH-FIT-004`, `DASH-RENDER-001`,
operator `DASH-FIRST-001`, UI `DASH-STATE-002`, contrast `DASH-COLOR-001`.
При `MONITORING=false` live-строки = `Not Verifiable`. Не reopen `#8986`.

## Артефакты

`reports/audit/observability-seq/<UTC>-obs-seq-<shortsha>/`
`00-inventory.md` … `09-final-sweep.md`, `ledger.jsonl`, `findings.json`, `report.md`.

## Success

- grafana-six не запускался
- 8 карточек executed или SKIP с причиной
- у шагов 1–8 есть issue/close исход в ledger
- нет открытых issues **этого** прогона без BLOCKED
- нет commit в main, нет правок `.env`

## Appendix — DASH-AUTO (proposals; not SSOT)

Do **not** invent IDs that already exist. Prefer REQUIREMENTS IDs:

| Proposal | Prefer SSOT |
| --- | --- |
| `DASH-AUTO-003` (action-verb title) | `DASH-COPY-003` |
| `DASH-AUTO-004` (description) | `DASH-COPY-002` |
| `DASH-AUTO-005` (no `$__range` on Monitor*) | `DASH-COPY-004` |
| `DASH-AUTO-007` (unique panel id) | `DASH-META-002` |

Remaining proposals (still not SSOT) — cheap JSON checks on steps 2/3/4/7:

| ID | Check (JSON) |
| --- | --- |
| `DASH-AUTO-001` | includeAll PromQL var → `allValue` is `.*`, not `$__all`/null |
| `DASH-AUTO-002` | table `defaults.cellOptions` ≠ `color-background` (override-only) |
| `DASH-AUTO-006` | range/track panel has `$__range` or range wording |
| `DASH-AUTO-008` | `gridPos`: `w>0`, `h>0`, `x>=0`, `x+w<=24`, no top-level overlap |
| `DASH-AUTO-009` | no unexplained top-level `y` gap > 1 |
| `DASH-AUTO-010` | no placeholder titles (`Panel Title`, `TODO`, empty) |
| `DASH-AUTO-011` | datasource type ∈ prometheus / infinity / grafana |
| `DASH-AUTO-012` | domain-enum stats (CB, raw health) have text mappings |
| `DASH-AUTO-013` | fail-closed status stats set `noValue` + null→UNKNOWN |
| `DASH-AUTO-014` | dashboard links include `${__url_time_range}` or from/to |
| `DASH-AUTO-015` | first-window text panel body ≤ 800 chars |
| `DASH-AUTO-016` | First Action / CTA ≤ 4 rows or ≤ 4 data links |
| `DASH-AUTO-017` | inventory `panel_count` formula is one (leaf XOR leaf+row) and matches |
| `DASH-AUTO-018` | timeseries tooltip mode matches role (multi/desc vs single) |
