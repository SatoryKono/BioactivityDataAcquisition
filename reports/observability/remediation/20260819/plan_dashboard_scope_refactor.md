# План: scope / time / provider telemetry на семи shipped Grafana-дашбордах

Status: proposed (согласование telemetry + control-plane + dashboard UX)
Owner: @bioetl-observability
Date: 2026-08-19
Pin: `origin/main` `592bf60b74`
Does not replace: `DASHBOARD_REQUIREMENTS.md`, `panel-content-contract.yaml`,
`layout-budgets.yaml`, ADR-010/ADR-053

## 0. Что изменилось относительно исходного аудита

Исходный текст опирался на «шесть дашбордов» и «148 panels». На текущем
`origin/main` поверхность другая. План ниже — это тот же driver (не смешивать
CURRENT Prometheus с SELECTED RUN HTTP), пересчитанный на shipped JSON и уже
закрытые issues.

| Исходное утверждение | Факт на `592bf60b74` | Следствие |
| --- | --- | --- |
| Шесть дашбордов D1–D6 | Семь UID: **0. Trust** + Overview…Run Explorer | Trust входит в scope; нумерация D0–D6 |
| 148 panels | **236** panels (173 queryable, 63 text/row) | Не целиться в 148; не резать first-window ради числа |
| Scope не размечен | First-window copy уже требует CURRENT / SELECTED RUN / TIME RANGE (`#8923` closed; `test_dashboard_first_window_containment`) | Остаётся **per-query-panel** `scope_class` + coverage CTA, не повтор banner-epic |
| `run_id` в PromQL | Запрещён (`DASH-DATA-002`); fill-audit 2026-08-19: 173/173 без query error | Не открывать issue «убрать run_id из PromQL» |
| `pipeline_run_report` отсутствует | Есть **v1** (`configs/contracts/reports/pipeline_run_report.v1.json`) | C1 = расширение/проекция, не greenfield |
| Provider NaN | Recording rule `bioetl_provider_current_status` всё ещё синтезирует UNKNOWN через `(x*0)/(x*0)` | B1/B2 остаются P0 |
| Set range to run | В JSON/docs **нет** | A2 остаётся P0 |
| Hidden `$adapter` / `$pipeline_context` | Provider Health `hide=2`; Runtime `$provider_hint` `hide=2` | A3 остаётся P1 |
| JSON `refresh: 60s` | Задано на всех семи UID | A4 = UI/URL effective-refresh, не смена JSON default |
| First-window density | `first_screen_max_panels=8` data-bearing, `DASH-FIT-006` (`#8980` closed) | Phase 2 **не** режет first-window ниже бюджета; режет duplicate below-fold tables |
| Contract tests | Inventory, layout-budgets, content-contract v2, fill-error classifier | E1/E2 частично shipped; E3–E6 → существующие `#8984` `#8985` `#8986` |

Закрытые эпики, которые **не** переоткрывать: `#8543`–`#8552` (scope banners),
`#8923` (CURRENT/RANGE/SELECTED RUN naming), `#8927`/`#8929`/`#8930` (fill/truth),
`#8980` (Trust first-screen count).

Открытый тестовый контур, который план **переиспользует**, а не дублирует:

| Issue | Роль в этом плане |
| --- | --- |
| `#8984` | E3/E5 execution-bound fixture → browser |
| `#8985` | risk-based semantic coverage |
| `#8986` | SHA-bound render evidence on supported host |

## 1. Цель (без изменений по смыслу)

Каждый shipped dashboard однозначен по scope, компактен в first window и
проверяем по цепочке variable → query → data → transformation → visualization →
semantics.

- Prometheus: CURRENT и RANGE, low-cardinality.
- BioETL Ops HTTP: exact-run identity, accounting, funnel, artifacts.
- `run_id` не Prometheus label и не скрытая подстановка в PromQL.

Арифметика run-report (success, 1000 processed, 983 Gold, 17 contract exclusions)
не является предметом этого рефакторинга.

## 2. Приоритетные результаты

| Driver | Наблюдение | Риск | Целевой результат | Статус |
| --- | --- | --- | --- | --- |
| Historical run вне range | Run 17 Aug vs window now-12h 19 Aug | CURRENT читается как run verdict | Coverage banner + Set range to run | **open (A2)** |
| Provider current = NaN | D3 UNKNOWN, cause tables empty | Нет различия missing / stale / fail | Enum 0/1/2/3 + reason/freshness | **open (B1–B3)** |
| Hidden applied variables | `$adapter`, `$pipeline_context` hide=2 | Scope нельзя подтвердить | Read-only effective chips | **open (A3)** |
| Когнитивная плотность | 236 panels, collapsed drill-down | Регрессии ниже fold | Duplicate tables → master-detail; first-window уже ≤8 data-bearing | **open (D*)** |
| URL refresh vs UI | JSON 60s, UI может показать off | Ложная свежесть | Effective-refresh indicator + тест | **open (A4)** |

## 3. Целевая модель scope

Три взаимно исключающих lane — без изменений. Реализация:

- First-window **dashboard** banners уже есть.
- Недостаёт: `scope_class` на **каждой query-panel** (join к
  `panel-content-contract.yaml` `scope: current|selected_run|time_range|global`),
  compact badge, coverage chip, CTA Set range to run
  (`started_at-5m` … `completed_at+5m`, без silent range rewrite).

Рекомендация по решению из §9 исходника **сохраняется**: warning + кнопка, не
автосмена range.

## 4. Роли дашбордов (D0–D6)

| UID | Роль first window | Не делать в этом эпике |
| --- | --- | --- |
| `bioetl-control-plane-v1` (D0 Trust) | Replay/evidence trust; не fleet health | Не превращать в Overview |
| `bioetl-overview-v2` (D1) | Current fleet vs selected-run vs coverage vs first action | Не дублировать D6 forensic |
| `bioetl-runtime` (D2) | Current blocker + stage bottleneck | Global process/shutdown → collapsed ops |
| `bioetl-provider-health-v2` (D3) | Selected provider verdict + reason/freshness | Три blank fleet tables → один empty-state |
| `bioetl-dq-v2` (D4) | Current DQ vs selected-run exclusions | Свести duplicate reject hierarchy |
| `bioetl-incident-v1` (D5) | Ranked suspect + freshness; EMPTY ≠ run healthy | |
| `bioetl-run-explorer-v1` (D6) | Exact UUID forensic SSOT | Один Recent Runs table (limit 4/10/20) |

## 5. Workstreams после актуализации

### A — Semantic scope and time coverage

| ID | Изменение | Pri | Статус |
| --- | --- | --- | --- |
| A1 | `scope_class` + badge на всех query panels; join к content-contract `scope` | P0 | residual (dashboard-level banners shipped) |
| A2 | Selected-run coverage banner + Set range to run | P0 | not started |
| A3 | Effective-filter chips для hidden `$adapter`, `$pipeline_context`, `$provider_hint` | P1 | not started |
| A4 | Effective refresh + timezone indicator; URL `refresh=` covered тестом | P2 | not started |

### B — Provider telemetry contract

| ID | Изменение | Pri | Статус |
| --- | --- | --- | --- |
| B1 | `bioetl_provider_current_status` enum 0=OK,1=WARN,2=CRIT,3=UNKNOWN; запрет NaN в published current-status | P0 | recording rule ещё NaN-синтез |
| B2 | `bioetl_provider_current_status_info{provider,reason,last_success_at,last_attempt_at,source_state}` | P0 | not started |
| B3 | `bioetl_provider_telemetry_freshness_seconds` + stale threshold | P1 | 9104 — другой freshness marker; info-metric нет |
| B4 | Provider vs adapter в title/labels; `adapter=All` проверяем | P1 | `$adapter` hidden |

### C — Selected-run information architecture

| ID | Изменение | Pri | Статус |
| --- | --- | --- | --- |
| C1 | Compact projection поверх `pipeline_run_report_v1` (identity, times, funnel, reasons, DQ, provider, artifacts). v2 только если v1 нельзя расширить без breaking change | P0 | v1 exists |
| C2 | Один compact Selected Run Summary на D1/D2/D4/D5 (не на D0, там свой Trust HTTP) | P1 | shell 9402/9403 есть не везде как first-window answer |
| C3 | D6 Recent Runs: один table, default 10, selectable 4/20 | P2 | сейчас отдельные 3010/limit contracts |
| C4 | Table row → `/d/bioetl-run-explorer-v1` + panel anchor + variables | P1 | nav bus есть; row→anchor нет как контракт |

### D — Panel rationalisation

Не удалять first-window verdict cards. Цель — duplicate **below-fold** tables и
три blank empty-states (D3 fleet). Progressive deprecation после двух циклов.

### E — Automated contracts

Не плодить параллельный test pack. Довести:

- E1/E2: расширить content-contract `scope` до badge/assert (частично есть)
- E3–E5: `#8984` + `#8986`
- E6: `#8985` + cross-UID summary vs D6 после C2

## 6. Последовательность

0. Safety net: не трогать Prom instrumentation и layout в одном PR. E1/E2 до
   визуального merge. Full-profile provisioning остаётся.
1. Correctness: **B1/B2 + A1/A2**, затем **C1**.
2. First-window role pass D6 → D1 → D2 → D4 → D3 → D5 (D0 только coverage/chips).
3. Drill-down C4 + E3–E6 (`#8984`–`#8986`).
4. Decommission duplicates + operator guide.

Запрещено: поднимать `first_screen_max_panels`, FIT viewport, tech-debt budgets;
`run_id` Prometheus labels; `vector(0)` на verdict; Docker monitoring как
локальный default (ADR-010).

## 7. Definition of Done (актуализированный)

1. Ни одна panel не использует `run_id` в PromQL (уже enforced; регрессия = fail).
2. Каждая query-panel имеет `scope_class`; selected-run coverage виден.
3. Provider current status не публикуется как NaN; missing/stale/unknown различимы.
4. Hidden query variables отражены read-only chips.
5. Query error / no data / zero / UNKNOWN / VALID EMPTY различны.
6. Compact summaries D1/D2/D4/D5 совпадают с D6 по identity/timing/funnel.
7. CI: JSON/content-contract + `#8984` fixtures + `#8986` host render (opt-in).
8. First window проходит `test_dashboard_operator_readability.py`.

## 7.1 GitHub tracking

| ID | Issue |
| --- | --- |
| Epic | #9009 |
| A1/A2 | #9011 |
| B1/B2 | #9012 |
| C1/C2/C4 | #9013 |
| A3 | #9018 |
| D | #9019 |
| A4 | #9020 |
| E (existing) | #8984 #8985 #8986 |

DAG: `#9012 ∥ #9011 → #9013 → #9018 ∥ #9019 → #9020`.

## 8. Решения (рекомендации без изменения)

| Decision | Рекомендация |
| --- | --- |
| Historical run time | Warning + Set range to run; не менять range молча |
| Provider status source | Exporter/recording normalization + info metric; не control-plane bridge |
| Run summary | Thin HTTP projection от v1; v2 только при breaking schema |
| Hidden variables | Оставить hidden, показать effective values |
| Panel reduction | Progressive deprecation, не delete-first |
