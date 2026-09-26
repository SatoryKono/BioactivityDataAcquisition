# Циклический аудит telemetry / data-plane

- **run_id:** `20260820T111418Z-telemetry-cycle-75e3921fda`
- **prompt:** `prompt.audit.cycle.telemetry` v1.0.0
- **pin:** `origin/main@d297d3d14b` (фактический base worktree: `origin/main@5339f83340`)
- **ветка:** `fix/audit-seq-d297d3d14b-telemetry`
- **HEAD (до cardinality refresh):** `75e3921fda`
- **N:** 5 / 5 (пустых циклов нет)
- **MODE:** full · **AUDIT_MODE:** full · **LANGUAGE:** ru
- **MONITORING:** false (стек Grafana/Prometheus **не** стартовал)
- **ALLOW_ISSUE_WRITE/PUSH/CLOSE:** true · **ALLOW_MERGE:** false
- **surface_score:** **2 / 3** (acceptable)
- **Легенда surface_score:** 3 good — checks reproducible, material risks closed, automation present; 2 acceptable — core mechanism correct, local non-critical gaps; 1 weak — material gaps; 0 unacceptable. Использован прямой 0–3, не mapping 0–5.
- **Issues:** [#9144](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9144), [#9145](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/9145)
- **P0:** нет (cap 1 не применяется)

## Executive summary

Data-plane путь `instrumentation → scrape/export → recording rule → queryable series` **существует и автоматизирован**. Inventory gate зелёный: 0 undeclared / 0 dead / 0 alias drift / 0 rules_without_registry. First-screen readiness matrix покрывает все 13 панелей (`Ready? yes`), Expected Empty задокументирован. `run_id` запрещён в Prometheus labels (`FORBIDDEN_PROMETHEUS_LABEL_NAMES`). NoOp tracing (ADR-022) резолвится в composition.

Материальные локальные пробелы (P2): 14/57 алертов DEFAULT_RULES_FILES без firing fixtures (после этого цикла было 20, закрыты 5 critical-path); `PrometheusDown` в `bioetl.yml` вне coverage gate; cardinality review на main был stale/dirty, live Prometheus unconfigured (ожидаемо при MONITORING=false).

Имена метрик **не изобретались**. Dashboard JSON не правился «чтобы панель выглядела полной».

## Inventory (фаза A)

Команда: `python -m scripts.engineering.qa report-observability-metric-inventory --json` / `--check --allow-local-cardinality-fallback`.

| Счётчик | Значение |
| --- | ---: |
| declared / registered | 295 |
| emitted / live | 181 |
| dashboarded | 253 |
| alerted | 126 |
| undeclared / emitted_without_declaration | 0 |
| dead / unused_declared | 0 |
| dashboarded_without_declaration | 0 |
| alerted_without_declaration | 0 |
| rules_without_registry | 0 |
| compatibility_alias_candidates | 0 |
| documented_only | 0 |
| runtime_cardinality_review_required | 0 |
| runtime_label_contract_violations | 0 |

Каталог: `docs/04-reference/observability/metrics-catalog.md`. Runtime registry: `REGISTERED_PROMETHEUS_METRIC_NAMES` в `scripts/engineering/qa/report_observability_metric_inventory.py`.

## Coverage matrix first-screen (фаза B)

Источник строк: `docs/03-guides/dashboards/metrics-readiness-matrix.md` (Last verified 2026-08-17). HTTP control-plane — валидный source, когда матрица так говорит.

| Panel / need | query / metric / rule | labels | ready? | blocker |
| --- | --- | --- | --- | --- |
| Overview Status | `bioetl_l0_status` (recording) | dashboard selectors | yes | live empty until trust-anchor samples (OBS-FILL-01 / #8930) |
| Overview First Action route | `bioetl_l0_next_action_route` (recording) | dashboard selectors | yes | — |
| Overview Inputs matrix | `bioetl_l0_input_status_selected` (recording) | dashboard selectors | yes | — |
| Runtime Status | `bioetl_runtime_current_status_trusted` (recording) | dashboard selectors | yes | — |
| Runtime Blockers | `bioetl_runtime_current_blocker_reason` (recording) | dashboard selectors | yes | empty when healthy = VALID EMPTY |
| Metrics Evidence | scrape/rule trust series on board | — | yes | operator wording only |
| Provider severity matrix | `bioetl_provider_current_status` (recording) | provider | yes | empty without provider traffic (VALID EMPTY) |
| Provider top causes | `bioetl_provider_current_cause` (recording) | cause | yes (rules) | needs failure events to populate |
| DQ Status | `bioetl_dq_current_status` (recording) | — | yes | — |
| DQ reasons | `bioetl_dq_current_reason` (recording) | reason | yes | — |
| Trust replay safety | control-plane recording + HTTP | — | yes | INCOMPLETE when evidence gap |
| Incident suspects | reuses provider/runtime/dq current rules | — | yes | thin board |
| Run identity / records | `/ops/control-plane/*` HTTP | n/a (not Prom labels) | yes | needs health server |

Scrape path (`grafana/prometheus.yml`): job `bioetl` → `bioetl:8000` `/metrics`, interval 30s; Pushgateway `pushgateway:9091`; Prometheus self-scrape. `up{job="bioetl"}=1` **не** доказывает data-plane population (комментарий в yml).

## Instrumentation (фаза C)

- Порты vs adapters: `MetricsPort` / `TracingPort` с fallback `NoOpMetrics` / `NoOpTracing` (`src/bioetl/domain/ports/noop/_tracing.py`, `src/bioetl/composition/observability_resolution.py`, ADR-022).
- `run_id` обязателен в **логах** (`UnifiedLogger`), запрещён в **Prometheus labels** (`prometheus_metric_label_policy_sets.py` lines 16–17). В `grafana/prometheus-rules/*.yml` вхождений `run_id` нет.
- Hyphenated metric names в observability Python: ложные срабатывания (`utf-8`, `abc-123`, `opentelemetry-exporter-otlp`), не имена серий.
- Alias drift: `compatibility_alias_candidates=0`, `alias_emitters={}`.
- SCOPE path `src/bioetl/observability` отсутствует; канон — `src/bioetl/infrastructure/observability` (TELE-005). Остальные SCOPE-пути существуют → не empty SCOPE STOP.

## Cardinality / rules (фаза D)

`collect_rule_test_coverage`:

| Metric | Value |
| --- | ---: |
| alert_definitions (DEFAULT_RULES_FILES) | 57 |
| tested_alerts / firing_alerts | 43 / 43 |
| MIN_TESTED_ALERTS | 43 (было 38; ratchet только с fixtures) |
| untested_alerts | 14 |
| record_definitions | 110 |
| directly_tested_records | 35 |
| MIN_DIRECTLY_TESTED_RECORDS | 28 |
| untested_control_plane_records | 0 |
| PrometheusDown (bioetl.yml, вне DEFAULT) | untested |

Этот цикл добавил firing fixtures (commit `75e3921fda`): `BioETLPipelineRunFailed`, `BioETLRecordFlowInvariantViolated`, `BioETLStageBacklogActive`, `BioETLLineageRefsMissing`, `BioETLDQValidationFailuresCritical`.

Cardinality: live Prometheus URL unconfigured (`BIOETL_OBSERVABILITY_PROMETHEUS_URL`). Mode `local_cardinality_fallback`. Thresholds не поднимались. `#9145` — refresh с clean tree.

## Issues / fix (фаза E)

- Открыты #9144 (untested alerts), #9145 (stale cardinality).
- Fix owner surface: `grafana/prometheus-rules/tests/bioetl_observability.test.yml` + ratchet `MIN_TESTED_ALERTS` 38→43 + unit string `below 43`.
- Dashboard JSON не редактировался.
- Новых `run_id` labels нет.
- Tech-debt budgets не менялись.

## Validate (фаза F)

- `tests/unit/scripts/qa/test_check_prometheus_rules.py` — 9 passed (после fixtures).
- Inventory `--check --allow-local-cardinality-fallback` — exit 0.
- Delta vs origin/main@5339f83340: **resolved** 5 critical-path untested alerts; **unchanged** residual 14 + PrometheusDown + first-screen record tests; **new** TELE-005 SCOPE alias; **regressed** нет.

## Focus checklist

- [x] No invented metric names
- [x] Every first-screen panel has a readiness row
- [x] Expected Empty documented
- [x] `run_id` absent from Prometheus labels
- [x] Recording rules covered by repo tests **or explicit gap** (TELE-004)
- [x] Cardinality review attached / residual #9145
- [x] Monitoring stack not started
- [x] Dashboard JSON not used as a substitute for missing series

## Stop conditions

Не сработали: series не изобретались; MONITORING=false соблюдён; секретов в labels/rules нет; SCOPE не пустой.

## Post-change

- Runtime trees `.codex/.junie/.devin` не менялись → mirror check skipped.
- `src/bioetl/**/*.py` не менялся → module-coverage inventory skipped.
- Touched: prometheus rule tests + `check_prometheus_rules.py` MIN_TESTED_ALERTS + cardinality JSON + audit reports.

## Closeout notes

ALLOW_MERGE=false → PR без merge. ALLOW_CLOSE=true, но закрытие #9144/#9145 только после evidence на `origin/main` (остаточный 14 и dirty-flag).
