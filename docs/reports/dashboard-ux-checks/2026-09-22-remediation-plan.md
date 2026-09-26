# План исправлений Grafana (GR-DB-CORR) — актуализация + пофайловый план

**Дата:** 2026-09-22  
**Статус:** рабочий план  
**Эпик:** #10554  
**SSOT:** `grafana/dashboards/*.json`  
**Открытые children:** #10570 (R01–R02), #10571 (ACCEPT), **#10602** (A-SCOPE), **#10603** (B-NAV), **#10604** (C-POLISH), **#10605** (E-OPS)  
**Закрыто недавно:** #10557, #10568 via #10599

## Канон нумерации

| # | Title | Файл |
|---|-------|------|
| 0 | Run Explorer | `grafana/dashboards/bioetl-run-explorer-v1.json` |
| 1 | Trust | `grafana/dashboards/bioetl-control-plane-v1.json` |
| 2 | Overview | `grafana/dashboards/bioetl-overview-v2.json` |
| 3 | Pipeline Diagnostics | `grafana/dashboards/bioetl-runtime.json` |
| 4 | Provider Health | `grafana/dashboards/bioetl-provider-health-v2.json` |
| 5 | Data Quality | `grafana/dashboards/bioetl-dq-v2.json` |
| 6 | Incident Workspace | `grafana/dashboards/bioetl-incident-v1.json` |

---

## Пофайловый план изменений

### PR-1 — ложные статусы / скоуп (Фаза A)

#### 1. `grafana/dashboards/bioetl-control-plane-v1.json`

| ID | Что менять | Где в файле | Как |
|----|------------|-------------|-----|
| **A1** | Default `$pipeline` | `templating.list[]` name=`pipeline`, `current.text/value` = `"unknown"` | Поставить `$__all` / `All` (как у `workflow`). Не хардкодить конкретный pipeline. |
| **A4** | Guard при `run_id=-` | Панели selected-run: **9418** Review Selected-Run Trust, **9421** Inspect Latest Complete Run, **9402** Review Run Summary, **9416** Retention, **9415** Lineage, **9413** Checkpoint Validation, **9414** Manifest Validation, **9417** Bounded Failure Reasons | Для Infinity/Ops targets: не слать запрос при `run_id=-` (Grafana `hide from` / conditional via variable, или empty-frame text). Уже есть `noValue: SELECT RUN` — дополнить, чтобы не было datasource error triangle. |
| **C3** | Nav chip «1. Trust» | `links[]` / text-nav panel (шина) | Текущий chip — текст/disabled, не active link на себя |

**Смежные тесты (обновить вместе):**
- `tests/integration/test_dashboard_scope_reset_tooltips.py` — URL с `unknown` в var-
- при смене default pipeline — любые ассерты `current.value == "unknown"` на Trust pipeline var (проверить grep)

#### 2. `grafana/dashboards/bioetl-runtime.json`

| ID | Что менять | Где | Как |
|----|------------|-----|-----|
| **A1** | Default `$pipeline` | `templating.list` name=`pipeline` → `"unknown"` | `$__all` / `All` |
| **A2** | `$provider_hint` | name=`provider_hint`, `hide=2`, `current=chembl` | Default пусто / `$__all` / `.*`; эвристика query_result согласовать с `$pipeline` (не фиксировать chembl) |
| **B3** | DataLink Prometheus | panel **9102** Monitor Metrics Coverage → `url: http://localhost:9090/targets` | Убрать **или** оставить (сейчас allowlist в structural invariants явно разрешает `http://localhost:9090/`). Предпочтение плана: убрать из first-screen / заменить на runbook-текст. Если убираем — поправить allowlist-тест только если ссылка исчезнет везде. |

**Смежные тесты (обязательно):**
- `tests/integration/test_pipeline_runtime_dashboard.py` строка ~136:  
  `assert ... provider_hint ... == "chembl"` → ожидание нового default  
- `tests/integration/test_dashboard_scope_refactor.py` — chip `provider_hint=`  
- `tests/integration/test_grafana_dashboard_metric_semantics.py` — `provider=~"$provider_hint"`

#### 3. `grafana/dashboards/bioetl-run-explorer-v1.json`

| ID | Что менять | Где | Как |
|----|------------|-----|-----|
| **A3** | Dual-status | panel **3010** Inspect Recent Runs (last 10) | Добавить колонку Evidence/Trust verdict **рядом** с processing status; не подменять success. Копирайт в description: processing ≠ trust. |
| **B1** | Slug в URL | Data link «Select this run» (~строка url `.../6-run-explorer?...`); panel link «Browse all pipelines» | Заменить `6-run-explorer` → `0-run-explorer` (или `/d/bioetl-run-explorer-v1?...` без slug). Сейчас: 2× `6-`, 1× `0-`. |
| **C1** | Высота Domains | panel **9451** Inspect Selected Run Domains, `gridPos.h=12` | Уменьшить h (напр. 7–8) с учётом first-window noscroll |
| **C2** | Мёртвый rename | transformations / `organize`: `evidence_completeness` → `Evidence` + filter exclude того же поля | Удалить rename и связанные index/exclude для мёртвого поля |
| **C4** | UUID truncate | column Run в **3010** | wrap или documented truncate — по продуктовому решению |
| **C5** | Колонка Workflow | **3010** (и связанные) | Скрыть при пустых значениях / убрать если всегда «—» |
| **B7** | Annotations | `annotations.list` сейчас `[]` | Добавить стандартный `Annotations & Alerts` как у Trust/Overview/Runtime |

**Смежные тесты:**
- `tests/integration/test_dashboard_first_window_containment.py` — Run Explorer first window
- `tests/integration/test_dashboard_vis_stream2_layout.py`
- `tests/integration/test_dashboard_units_decimals.py`
- links support: `tests/integration/_grafana_dashboard_links_support.py`

---

### PR-2 — навигация / копирайт (Фаза B)

#### 4. `grafana/dashboards/bioetl-overview-v2.json`

| ID | Что менять | Где | Как |
|----|------------|-----|-----|
| **B2** | DataLink title | panel **9601** Review Active Alerts → title `Open 2. Runtime (alert conditions)` | → `Open 3. Pipeline Diagnostics` (target UID уже `bioetl-runtime`) |

**Смежные тесты:**
- `tests/integration/test_dashboard_cross_scope_titles.py` — allowed titles для `(bioetl-overview-v2 → bioetl-runtime)` уже включают `"Open 3. Pipeline Diagnostics"` и `"Open 2. Runtime"`. После смены title оставить оба в allowlist **или** убрать устаревший `"Open 2. Runtime"` из списка.

#### 5. `grafana/dashboards/bioetl-dq-v2.json`

| ID | Что менять | Где | Как |
|----|------------|-----|-----|
| **B4** | «0. Control Plane» | descriptions панелей handoff (~lineage gaps / footer guidance) | Заменить на `` `1. Trust` `` / `bioetl-control-plane-v1` |
| **B5** | Дубль текста | `templating.list` name=`stage` → description | Убрать второе «Default selection is All stages.» |

#### 6. `grafana/dashboards/bioetl-incident-v1.json`

| ID | Что менять | Где | Как |
|----|------------|-----|-----|
| **B6** | Description vs layout | root `description` | Убрать утверждение, что current alerts только в collapsed; **2005** Monitor Current Alerts на y=13 (first-screen band). Collapsed: **2020** Review Alert Evidence |
| **B7** | Annotations | `annotations.list` = `[]` | Добавить `Annotations & Alerts` |

**Смежные тесты:**
- `tests/integration/test_dashboard_variable_dependencies.py` — provider fallback `unknown` (не ломать при правках description)

#### 7. Все `grafana/dashboards/bioetl-*.json` (пакет B8)

| ID | Что | Как |
|----|-----|-----|
| **B8** | Nav slug vs UID | В `links[]` / data links унифицировать path: `/d/<uid>/...` со slug = канонический номер title (`0-run-explorer` … `6-incident-workspace`) **или** без slug. Делать одним проходом после B1. |

**Тесты:** `_grafana_dashboard_links_support.py`, `test_dashboard_structural_invariants.py` (dangling UID).

---

### PR-3 — мелочь / preview (Фаза C)

| Файл | ID | Изменение |
|------|-----|-----------|
| `bioetl-run-explorer-v1.json` | C1–C5 | см. PR-1 (можно вынести сюда, если PR-1 слишком большой) |
| `bioetl-control-plane-v1.json` | C3 | chip Trust |
| Grafana UI only (не репо) | **C6** | Удалить `[GR-DB-CORR Preview]` копии; не создавать JSON в репо |

---

### Фаза D — issues без чистого JSON-only

| Issue | Файлы-кандидаты (после live confirm) | Примечание |
|-------|--------------------------------------|------------|
| **#10570** | `grafana/dashboards/bioetl-dq-v2.json` (panel queries с `$__interval`, soft/hard sums); возможно `prometheus/` recording/alert rules | Сначала reproduce на live Prometheus |
| **#10571** | матрица / evidence в `reports/observability/grafana/audit-*`, docs acceptance | Не закрывать по unit-тестам дашбордов |
| **#10554** | — | Закрыть после #10570+#10571 |

---

### Backend residual (не dashboard JSON; отдельные PR)

| ID | Область кода (ориентир) | Связь |
|----|-------------------------|-------|
| **E1** | Ops HTTP handlers `/ops/observability/*` — контракт `run_id=-` | A4 + Trust panels |
| **E2** | Trust evidence readers (retention/lineage/manifest/checkpoint) — статус UNAVAILABLE vs ERROR | Trust tables 9413–9417 |
| **E3** | catalog/manifest list p95 | перф |
| **E4** | filter-options 20s | **уже #10599** — не трогать без регрессии |

Точные пути API уточнять при старте E1/E2 (`src/bioetl/interfaces/http/` / application observability services) — не смешивать с PR-1/2 JSON.

---

## Карта «файл → все ID»

| Файл | ID работ |
|------|----------|
| `grafana/dashboards/bioetl-control-plane-v1.json` | A1, A4, C3 |
| `grafana/dashboards/bioetl-runtime.json` | A1, A2, B3 |
| `grafana/dashboards/bioetl-run-explorer-v1.json` | A3, B1, B7, C1, C2, C4, C5 |
| `grafana/dashboards/bioetl-overview-v2.json` | B2 |
| `grafana/dashboards/bioetl-dq-v2.json` | B4, B5 (+ later #10570) |
| `grafana/dashboards/bioetl-incident-v1.json` | B6, B7 |
| `grafana/dashboards/bioetl-provider-health-v2.json` | только B8 (nav slug) до live-аудита 4 |
| `tests/integration/test_pipeline_runtime_dashboard.py` | A2 |
| `tests/integration/test_dashboard_cross_scope_titles.py` | B2 |
| `tests/integration/test_dashboard_scope_refactor.py` | A2 |
| `tests/integration/test_dashboard_scope_reset_tooltips.py` | A1 |
| `tests/integration/_grafana_dashboard_links_support.py` | B1, B8 |
| `tests/integration/test_dashboard_structural_invariants.py` | B3 (если убираем :9090) |
| `tests/integration/test_dashboard_first_window_*.py` | A3, C1, B7 |
| `docs/03-guides/dashboards/design-system.md` / panel docs | при смене семантики A3 / nav titles |
| `docs/reports/dashboard-ux-checks/2026-09-21.md` | acceptance notes, не код |

---

## Порядок PR / issues

1. **#10602** PR-1: control-plane + runtime + run-explorer (A*) + тесты defaults  
2. **#10603** PR-2: overview + dq + incident + nav slug (B*)  
3. **#10604** PR-3: C* / preview cleanup  
4. **#10605** backend E1–E3 (параллельно с A4)  
5. **#10570** live → query/rules  
6. **#10571** матрица → **#10554**

## DoD на каждый dashboard-PR

```text
pytest tests/integration/test_dashboard_operator_readability.py
pytest tests/integration/test_dashboard_first_window_noscroll.py
```

+ профильные тесты из колонки «смежные» выше.  
Не заявлять полный audit PASS. Refs: `#10554` (+ `#10571` при dual-status).
