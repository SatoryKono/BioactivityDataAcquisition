# План: источники данных и observability для Grafana BioETL

Status: proposed (plan-only; код в этой задаче не менялся)
Owner: @bioetl-observability + control-plane
Date: 2026-08-19
Pin: `origin/main` `21dcaa9368`
Does not replace: `DASHBOARD_REQUIREMENTS.md`, ADR-010, ADR-053,
`FORENSIC_ENDPOINT_TIMEOUT_SECONDS=12`, DASH-DATA-002 (`run_id` не Prom-label)

Основание: диагностика после panel-by-panel аудита семи дашбордов для
`chembl_assay` / `chembl_baseline` / backfill, run
`68c11d41-1d2f-5dc9-b041-9265bc485046` (1 000 Bronze, 1 000 Silver, 983 Gold
written, 17 contract exclusions, 0 quarantined, reconciliation delta 0).

## 0. Что изменилось относительно исходного текста

Исходный план писался на фоне live NaN и статического coverage. На текущем
`origin/main` часть **tracked** поверхностей уже сдвинута DASH-SCOPE
(`#9009` / `#9012` / `#9011` / `#9013`, squash `7857c349dc`). Live-контур
диагностики от этого **не** автоматически вылечился.

| Исходное утверждение | Факт на `21dcaa9368` | Следствие |
| --- | --- | --- |
| Tracked `bioetl_provider_current_status` ещё `(x*0)/(x*0)` | Tracked expr уже `universe * 0 + 3` + `bioetl_provider_current_status_info` | P0.4 = **deploy/reload/parity**, не переписывать rule |
| Coverage banner отсутствует | Static HTML «may sit outside TIME RANGE» на всех семи UID; HTTP `view=summary` уже считает `covers_selected_run` / `from_ms` / `to_ms` | P2 биндит существующую проекцию, не greenfield endpoint |
| `plan_for_manifest` глобальный | Подтверждено: всё ещё зовёт `_resolve_protected_refs()` (все manifests/checkpoints/lineage) + candidate `glob`/`rglob` | P0.1 остаётся P0 |
| `persist_contract_evidence` без production call sites | Подтверждено: writer есть, зовут только тесты | P0.2 остаётся P0 |
| Rehydrate сеет success counter | Подтверждено: `_seed_provider_universe` делает `increment_counter(bioetl_health_check_success_total)` | P1.1 остаётся P1 |
| `build_preflight_service` без monitor | Подтверждено: `HealthAggregator(...)` без `health_monitor=` | P1.2 остаётся P1 |
| `var-provider=unknown` только D0 | Hard-coded во **всех** nav-bus ссылках на Provider Health + Overview/Runtime handoff | P2 шире, чем «только Trust» |
| Forensic deadline 12 s | `FORENSIC_ENDPOINT_TIMEOUT_SECONDS = 12.0` | **Не поднимать**; чинить O(storage) |
| Prometheus rules path | Compose (ADR-010, optional) bind-mount `./grafana/prometheus-rules:/etc/prometheus/rules:ro` | Drift = другой процесс / нет reload / не этот compose |
| Существующие verifiers | `scripts/ops/observability/check_prometheus_rules_health.py`, `docker_runtime_preflight.py` promtool | Расширять, не форкать |

Не переоткрывать: `#8543`–`#8552`, `#8923`, `#8980`, `#9009` (DASH-SCOPE epic).
Не дублировать: `#8984` `#8985` `#8986` (fixture/render pack).

Запреты, которые план не нарушает:

- не повышать `FORENSIC_ENDPOINT_TIMEOUT_SECONDS`
- не класть `run_id` в Prometheus labels
- не `or vector(0)` на verdicts
- не повышать `first_screen_max_panels` / tech-debt budgets
- не делать monitoring Docker обязательным (ADR-010)

## 1. Подтверждённые источники (код)

### SRC-01 P0 — selected-run retention всё ещё глобальный

`ControlPlaneEvidenceService._bounded_retention_plan` зовёт
`plan_for_manifest`. Тот **всё равно** вызывает глобальный
`_resolve_protected_refs()` (`file_artifact_lifecycle_store.py:76-80`), который
через `collect_manifest_protections` / `collect_checkpoint_protections` /
`collect_lineage_protections` обходит **все** surface files.

Даже candidate set для одного манифеста не bounded:

- lineage: `fragments_root.glob("*.json")` + JSON parse
  (`_file_artifact_lifecycle_refs.py:135-137`)
- checkpoints: `checkpoint_root.rglob("*")`
  (`:148-152`)
- bronze: **безусловный** `bronze_root.rglob("*")` без фильтра по manifest
  (`:155-164`)

Это объясняет 504 `deadline_exceeded` и 7.61 s на «успешном» retry при 12 s
deadline. Лечить timeout нельзя.

### SRC-02 P0 — contract-evidence sidecar не пишется в production

`persist_contract_evidence()` существует
(`_raw_run_manifest_inspection.py:98-111`) и вызывается из unit-тестов.
Production application/composition call sites отсутствуют. Успешный run
остаётся `trust_status=INCOMPLETE`, потому что comparison/resume/lock не
записаны.

### SRC-03 P0 — live Prometheus ≠ tracked YAML

Tracked
`grafana/prometheus-rules/bioetl_observability.yml:669-670` уже:

```text
... or (bioetl_provider_health_check_provider_universe_15m * 0 + 3)
```

Live `/etc/prometheus/rules/...` на диагностическом стеке ещё содержал
`x*0 / x*0` → NaN. CI `promtool` зелёный, потому что проверяет **git**, не
загруженный процесс. Compose bind-mount theoretically syncs files; без
reload/не тот Prometheus — drift.

### SRC-04 P0 — rehydrate врёт current health

`current_metrics_rehydrate._seed_provider_universe` инкрементирует
`bioetl_health_check_success_total` для universe, **не** пишет
`bioetl_provider_health_status`. Также сеет `bioetl_pipeline_runs_total` и
stage counters. Health-server процесс выглядит «как будто probe прошёл».
`bioetl_control_plane_telemetry_missing_5m` смотрит
`count_over_time(manifest_writes_total[5m])` в
`bioetl_control_plane_current_status.yml` — CLI-события другого процесса.

### SRC-05 P1 — preflight не кормит ProviderHealthMonitor

`build_preflight_service()` создаёт `HealthAggregator` без
`health_monitor=`. Adapter path пишет counters/latency; canonical gauge
0/1/2 только из `ProviderHealthMonitor`.

### SRC-06 P1 — 68 панелей без instant series

Нужна классификация coverage, не массовая инструментизация. Часть семейств
event-optional.

### SRC-07 P2 — nav + static coverage

- Nav на D3 везде `var-provider=unknown`.
- Coverage copy статическая; HTTP `view=summary` уже умеет
  `covers_selected_run` / `coverage_offset` при `from`/`to`.

## 2. Целевая модель трёх полос

| Lane | Owner | Можно утверждать | Контракт |
| --- | --- | --- | --- |
| SELECTED RUN | Ops HTTP + manifest/report/ledger sidecars | identity, accounting, trust, retention, artifacts | `run_id` → bounded indexed reads; sidecar есть или typed absence |
| CURRENT | health server + gauges/recording rules | current provider/runtime/DQ | finite bounded values; freshness/reason; **не** historical run |
| RANGE | Prom counters/histograms | activity/trends в окне | empty = valid_empty **или** coverage_gap; не fabricate counters |

`run_id` остаётся HTTP-only.

## 3. Workstreams

### P0.1 Bounded retention plan (SRC-01)

Owner: Control Plane / Infrastructure. Depends: none.

1. `plan_for_manifest` **не** вызывает глобальный `_resolve_protected_refs`.
2. Manifest-scoped protections: только выбранный `RunManifest` + его
   sidecar/index.
3. Lineage: только `_by_manifest_id` index; иначе typed
   `lineage_index_missing`, без `glob("*.json")`.
4. Checkpoint: прямой path/index по `run_id`/`manifest_id`, без `rglob`.
5. Bronze: только identifier из манифеста; иначе bounded `not_recorded`,
   без обхода дерева.
6. Глобальный `plan()` для admin lifecycle **оставить** сканирующим — это
   другой use-case.

Acceptance:

- monkeypatch `Path.rglob` / unbounded `glob` в `plan_for_manifest` → 0 вызовов
- ≥5 000 unrelated files не меняют artifact count и не раздувают latency
- cold/warm retention-compliance < 1 s на fixture; < 12 s на local stack
- source failure → typed row, не blank table
- `FORENSIC_ENDPOINT_TIMEOUT_SECONDS` неизменен

### P0.2 Contract-evidence sidecar writer (SRC-02)

Owner: Application Control Plane / Composition. Independent of P0.1.

1. Application service пишет sidecar **ровно один раз** на manifest через
   composition-wired port. `persist_contract_evidence` остаётся infra helper.
2. Поля: `contract_comparison_status` + stable reason; `resume_contract` или
   explicit `resume_not_requested` при `launch_context.resume=false`;
   `lock_owner_id` или explicit reason.
3. Missing registry → UNKNOWN, не OK.
4. Исторические манифесты не переписывать; Grafana честно INCOMPLETE.

Acceptance: новый `chembl_assay` run создаёт
`<manifest>.contract-evidence.json`; `/ops/control-plane/manifest-validation`
без missing-sidecar ambiguity.

### P0.3 Retention panel 9416 error row (SRC-01 UI)

Owner: Interfaces / Grafana. Depends: P0.1.

`forensic_endpoint_error_v1` не ломать. Panel 9416 при 504 должен показать
строку: `endpoint`, `reason`, `retryable`, timestamp, refresh CTA.
`noValue` не маскирует datasource error как empty.

Сейчас description уже различает valid empty vs backend unavailable, но
Infinity table при HTTP 504 всё ещё blank.

### P0.4 Live rule deploy parity (SRC-03)

Owner: Operations / CI. Depends: none. **Первый deliverable.**

Tracked `grafana/prometheus-rules/*.yml` — единственный source. Не
переписывать fallback (уже `* 0 + 3`).

1. Idempotent deploy: copy/bind + `promtool check rules` + reload **после**
   validation + SHA-256 в логе.
2. Post-deploy verifier: `GET /api/v1/rules`, нормализация whitespace,
   sentinel suite vs git:
   `bioetl_provider_current_status`,
   `bioetl_provider_current_status_info`,
   `bioetl_control_plane_telemetry_missing_5m`,
   `bioetl_control_plane_current_status_trusted`, DQ status, L0 status.
3. Расширить `check_prometheus_rules_health.py` (сейчас lastError/missed
   iterations, **не** expr parity).
4. ADR-010: verifier optional, если Prometheus не запущен; CI static tests
   остаются, но **не** считаются proof live parity.

Acceptance: live expr содержит `* 0 + 3`, не `/`; absent health + universe →
finite `3`; BioETL groups без `lastError`; намеренный drift контейнера валит
verifier.

### P1.1 Split universe vs health (SRC-04)

Depends: P0.4.

1. Прекратить seed `bioetl_health_check_success_total` из run report.
2. Bounded `bioetl_provider_observed_universe` (gauge или recording) из
   latest persisted identity — **только** чтобы материализовать UNKNOWN=3.
3. Success counter — только реальные probes.
4. Freshness: stale → 3, не healthy. Cardinality: без timestamp labels
   (reason/source_state как в `_info`).

### P1.2 Wire ProviderHealthMonitor + persist (SRC-05)

Depends: P1.1.

1. `HealthAggregator(health_monitor=ProviderHealthMonitor(metrics=...))` в
   `build_preflight_service()`.
2. Persist compact record at preflight: provider, enum 0/1/2, observed_at,
   probe endpoint, optional reason.
3. Health server rehydrate gauge **только пока fresh**; иначе 3 +
   `missing_or_stale_health_status`.
4. Не ставить HEALTHY=2 потому что historical run success.
5. Startup health server **никогда** не инкрементирует
   `bioetl_health_check_success_total`.

### P1.3 Current control-plane facts (SRC-04/counters)

Depends: P0.2.

Не выводить current completeness из `count_over_time(*_total[5m])` другого
процесса. Durable facts: manifest present, ledger present, integrity pair,
checkpoint evidence, `last_observed_at` per `(pipeline, run_type)`.

`bioetl_control_plane_telemetry_missing_5m` потребляет эти facts (или
versioned replacement). Range counters не fabricate на startup.

### P1.4 Metric coverage class (SRC-06)

Depends: P1.1, P1.3.

Каждое dashboard-referenced family в
`observability_metric_declarations.yaml`:
`required_current` | `required_when_active` | `event_optional` |
`historical_only` | `deprecated`.

Panel empty-state: `valid_empty` | `coverage_gap` | `not_applicable`.

68 no-sample панелей **триажить**, не инструментировать вслепую.

### P2 Scope / navigation (SRC-07)

Depends: P0/P1 contracts.

1. Убрать static «may sit outside». Панель/chip на
   `GET .../pipeline-run-report?view=summary&from=${__from}&to=${__to}`:
   inside → «run is covered»; partial/outside → warning + offset;
   unknown/select_run → SELECT RUN.
2. Убрать `var-provider=unknown` из nav-bus и Overview/Runtime handoff.
   Нести `$provider` или provider из exact-run scope. Если reset неизбежен —
   явный copy, не silent Chembl→unknown.
3. Один test-context object для QA URL/screenshots; effective refresh из
   Grafana state (A4 `#9020` закрыт static text — здесь evaluated chip).

## 4. Порядок

| Seq | Deliverable | Почему |
| --- | --- | --- |
| 1 | P0.4 live rule parity | CURRENT Provider Health без правки run history |
| 2 | P0.1 + P0.3 | Forensic timeout и blank 9416 |
| 3 | P0.2 sidecar writer | Exact-run trust complete только при evidence |
| 4 | P1.1 + P1.2 | Historical identity ≠ current health |
| 5 | P1.3 | False telemetry gaps от process-local counters |
| 6 | P1.4 coverage class | 68 empty panels интерпретируемы |
| 7 | P2 nav + evaluated coverage | На стабильных контрактах |

P0.1 ∥ P0.4 ∥ P0.2 (P0.2 независим). P0.3 после P0.1. P1 после P0.4.
P2 после P1.

## 5. Verification

| Layer | Что |
| --- | --- |
| Unit | `plan_for_manifest` без global scan; sidecar semantics; monitor 0/1/2; finite 3 |
| Integration | rehydrate не fabricate success; rule expr `* 0 + 3`; empty-state declared |
| Runtime | `/api/v1/rules` + `/api/v1/query`; scrape up; raw `/metrics` == Prom |
| E2E | fresh local chembl_assay; restart health server; D0–D6 с exact `run_id` |
| Dashboard | first screen + collapsed rows; no blank 504; no NaN; provider scope preserved or explicit reset |
| Regression | panel-audit matrix: 0 query errors, 0 NaN status, explicit disposition for every empty panel |

Не считать DoD зелёный unit suite без live `/api/v1/rules` parity, если
Prometheus в сессии запущен.

## 6. Definition of Done

1. `retention-compliance` manifest-bounded, без global traversal, без
   normal-load `deadline_exceeded`. Timeout 12 s не поднят.
2. Новый manifest имеет truthful contract-evidence sidecar или typed
   unavailable; INCOMPLETE не из-за отсутствующего writer wiring.
3. Loaded Prom rules = tracked sentinel suite; finite unknown 3, не NaN.
4. Health-server не fabricate probe success; provider health из freshness-bounded evidence.
5. Current control-plane переживает restart на durable facts; range counters
   остаются event semantics.
6. Каждая empty panel: valid empty / coverage gap / N/A / typed source error.
7. Navigation preserves or explicitly resets provider/run; coverage warning
   считается из timestamps.
8. Static checks, unit/integration, runtime Prom/API verifiers и fresh
   seven-dashboard panel audit зелёные.

## 7. Suggested issue DAG (не созданы в этой задаче)

```text
P0.4  ∥  P0.1 → P0.3
         P0.2
              ↘
         P1.1 → P1.2
         P0.2 → P1.3
              ↘
              P1.4 → P2
```

Черновики issue-файлов можно вынести в
`reports/observability/remediation/20260819/issues-datasource/` по отдельной
команде.

## References (code)

- `src/bioetl/infrastructure/control_plane/file_artifact_lifecycle_store.py`
- `src/bioetl/infrastructure/control_plane/_file_artifact_lifecycle_refs.py`
- `src/bioetl/infrastructure/control_plane/_raw_run_manifest_inspection.py`
- `src/bioetl/application/observability/current_metrics_rehydrate.py`
- `src/bioetl/composition/factories/pipeline/_runner_assembly_support.py`
- `grafana/prometheus-rules/bioetl_observability.yml`
- `grafana/prometheus-rules/bioetl_control_plane_current_status.yml`
- `scripts/ops/observability/check_prometheus_rules_health.py`
- `src/bioetl/interfaces/http/_pipeline_run_report_table.py` (`view=summary`)
- `src/bioetl/interfaces/http/_forensic_request_budget.py`
