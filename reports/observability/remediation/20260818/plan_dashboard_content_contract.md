# Plan: contract-driven Grafana content and fill tests

Status: draft plan (not runtime SSOT)
Owner: @bioetl-observability
Date: 2026-08-18
Pin: `origin/main` after #8974 (`16a9e739`)
Normative hook: `docs/01-requirements/DASHBOARD_REQUIREMENTS.md` (delegated by `RULES.md` §3.2.3)
Does not replace: `dashboard-inventory.yaml`, `layout-budgets.yaml`, `selector-contracts.yaml`

## 1. Problem

The shipped seven-UID surface already has strong **structure** gates:

| Layer | What it already proves | Gap |
| --- | --- | --- |
| Inventory | UID, owner, `key_panels` id/title/type, selector vars | No role, scope, state model, fixture cases |
| Geometry | `DASH-FIT-001..005`, answer-panel map, first-window row caps | Answer panel is *present*, not that the first screen *answers* |
| State JSON | `noValue=UNKNOWN` on background verdict cards; synthetic-zero policy | No fixture that the panel *renders* UNKNOWN vs VALID EMPTY vs ERROR |
| Copy | Non-empty `description`; first-window `Monitor*` must not use `$__range`; verb titles | `test_panels_have_descriptions` is a skip-list heuristic |
| Audit matrix | title/type/datasource/query preview | No `role` / `tier` / `content_status` / fixture count |
| Trust HTTP fixtures | `tests/fixtures/grafana/control_plane_validation/` for 9413–9417 | Not wired as a general state×panel contract; Runtime/DQ/Explorer verdicts uncovered |

`DASH-FIRST-001` already requires `state × confidence × basis × next_action`. Tests currently lock only `DASH-FIT-003` (canonical answer panel is root + `y < 18`).

## 2. Principle (locked)

```
static contract  →  dashboard is described and points at allowed data
fixture contract →  every declared state has truthful payload + expected tokens
render contract  →  that content is visible/readable in a browser
```

- Static + fixture tests: fast, local-only, no `docker-compose.monitoring.yml`.
- Render/E2E: optional job on the supported monitoring host only (ADR-010).
- Tests bind to **ids, roles, fields, states** — not free-text regex over copy.
- New YAML **complements** inventory; it MUST NOT fork UID/owner/`key_panels` identity.

## 3. New normative IDs

Add to `DASHBOARD_REQUIREMENTS.md` (do not invent a parallel RULES section):

| ID | MUST |
| --- | --- |
| `DASH-CONTENT-001` | Every inventory `key_panel` and every `layout-budgets.yaml` answer panel MUST have a row in `panel-content-contract.yaml` with `role`, `tier`, `scope`, `evidence_basis`, `state_model`, `fixture_cases`. |
| `DASH-CONTENT-002` | Each dashboard `first_screen.required_roles` MUST be satisfied by root non-row panels with `gridPos.y < FIRST_WINDOW_Y`. A forensic/`tier>=3` panel MUST NOT be the only first-screen answer. |
| `DASH-CONTENT-003` | Declared `fixture_cases` MUST have a versioned payload under `tests/fixtures/grafana/panel_states/<uid>/<panel_id>/<case>.json` and expected visible tokens. Missing required evidence MUST NOT map to OK. |
| `DASH-CONTENT-004` | `scope: current` panels MUST NOT use `$__range`. `scope: range` copy MUST include `TIME RANGE`. `run_id` MUST NOT appear as a Prometheus label (extends `DASH-DATA-002` / `DASH-COPY-004`). |
| `DASH-CONTENT-005` | Contracted tables MUST declare `table_columns`, `hidden_columns`, `max_rows` (or bind to `layout-budgets.yaml` first-window caps), and distinct `empty_state` vs `error_state` copy tokens. |

P1/P2 IDs (`DASH-CONTENT-006` descriptions, `007` copy vocabulary, `008` visual-role, `009` nav a11y, `010` matrix completeness, `011` screenshot, `012` contrast) are reserved; do not add them until Stage 4–5.

## 4. Contract file

**Path:** `docs/03-guides/dashboards/contracts/panel-content-contract.yaml`

**Ownership:** `@bioetl-observability`. Loader lives in `tests/integration/_dashboard_content_contract.py` (pure parse + join to inventory / layout-budgets). Do not put loader logic in dashboard JSON.

### 4.1 Schema (v1)

```yaml
version: 1
owner: "@bioetl-observability"
roles:
  - scope_banner
  - verdict
  - confidence
  - next_action
  - stage_accounting
  - identity
  - explorer
  - forensic
scopes: [current, range, exact_run, global, browse]
evidence_bases:
  - prometheus_recording_rule
  - prometheus_instant
  - ops_http
  - static_html
state_tokens: [OK, WARN, CRIT, UNKNOWN, INCOMPLETE, ERROR, VALID_EMPTY]
fixture_case_ids:
  - ok
  - warn
  - crit
  - telemetry_absent
  - backend_error
  - valid_empty
  - selected_range_empty

dashboards:
  <uid>:
    first_screen:
      question: "<must equal DASHBOARD_REQUIREMENTS.md §7>"
      required_roles: [scope_banner, verdict, ...]
    panels:
      "<id>":
        role: verdict
        tier: 1
        scope: current
        evidence_basis: prometheus_recording_rule
        state_model: [OK, WARN, CRIT, UNKNOWN, INCOMPLETE]
        requires_no_data_copy: true
        requires_cta: true
        fixture_cases: [ok, warn, crit, telemetry_absent, backend_error]
        # tables only:
        table_columns: [parameter, value, percentage]
        hidden_columns: [row_status]
        max_rows: 4          # or $layout_budgets
        empty_state: VALID_EMPTY
        error_state: BACKEND_UNAVAILABLE
```

### 4.2 Join rules

| Field | Source of truth | Contract must |
| --- | --- | --- |
| uid / panel id / title | `dashboard-inventory.yaml` `key_panels` + shipped JSON | match id; title drift fails closed |
| answer panel id | `layout-budgets.yaml` `answer_panels` | be `role: verdict` or `next_action` and first-window |
| first-window `max_rows` | `layout-budgets.yaml` `first_window_summary_tables` | equal contract `max_rows` when both set |
| §7 question text | `DASHBOARD_REQUIREMENTS.md` | `first_screen.question` byte-equal (or a shared token map) |
| PromQL `$__range` | shipped JSON targets | forbidden when `scope: current` |
| `run_id` Prom label | shipped JSON expr | forbidden (`DASH-DATA-002`) |

### 4.3 Stage-1 enrollment (≤10 panels)

Start with answer-map + one confidence/accounting companion. Do **not** enroll all `key_panels` on day one.

| UID | id | role | scope | Why first |
| --- | --- | --- | --- | --- |
| `bioetl-control-plane-v1` | 9401 | verdict | current | FIT-003 answer |
| `bioetl-control-plane-v1` | 9400 | scope_banner | current | first-screen question |
| `bioetl-overview-v2` | 214 | verdict | current | FIT-003 |
| `bioetl-overview-v2` | 215 | next_action | current | paired answer |
| `bioetl-runtime` | 9401 | verdict | current | FIT-003 |
| `bioetl-runtime` | 9102 | confidence | current | telemetry gate |
| `bioetl-provider-health-v2` | 9101 | verdict | global | FIT-003 table |
| `bioetl-dq-v2` | 9401 | verdict | current | FIT-003 |
| `bioetl-incident-v1` | 2010 | verdict | current | FIT-003 |
| `bioetl-run-explorer-v1` | 9402 | identity | exact_run | FIT-003; 3010 is browse utility |

Stage 2 adds tables: Explorer `3010`, `9403`; Trust `9418`/`9416`; DQ `9102`.

## 5. Test map (what to add vs reuse)

| New test | Reuses / must not duplicate | Gate |
| --- | --- | --- |
| `tests/integration/test_dashboard_content_contract.py` | inventory loader; `answer_panels()`; `FIRST_WINDOW_Y` | P0 Stage 1 |
| `tests/integration/test_dashboard_state_fixture_contract.py` | Trust fixture generator patterns; `DASH-STATE-001/003/004` | P0 Stage 2 |
| `tests/integration/test_dashboard_scope_truthfulness.py` | `DASH-COPY-004`, first-window scope-banner test, PromQL scope report | P0 Stage 1 (thin) then thicken |
| `tests/integration/test_dashboard_table_content_contract.py` | `first_window_summary_tables`, organize/limit transforms | P0 Stage 3 |
| `tests/integration/test_dashboard_description_semantics.py` | replace *semantics* of `test_panels_have_descriptions` for enrolled roles only | P1 |
| `tests/integration/test_dashboard_copy_semantics.py` | `DASH-COPY-003/005/006`; design-system verbs | P1 |
| `tests/integration/test_dashboard_visual_role_contract.py` | migrate cases from `check-dashboard-visual-semantics` | P1 |
| `tests/integration/test_dashboard_content_matrix_completeness.py` | extend `report_dashboard_panel_audit_matrix.py` | P1 Stage 4 |
| `tests/e2e/test_dashboard_render_contract.py` | existing render/preflight scripts | P2 Stage 5 |
| `tests/integration/test_dashboard_navigation_accessibility.py` | nav bus JSON + optional browser | P1/P2 |

Keep `test_panels_have_descriptions` until Stage 4; then narrow it to non-enrolled leftover panels or delete once every data panel has a contract row.

## 6. Fixture layout

```
tests/fixtures/grafana/panel_states/<uid>/<panel_id>/<case>.json
tests/fixtures/grafana/panel_states/SCHEMA.md    # payload envelope only
```

Envelope (v1):

```json
{
  "contract": "panel_state_fixture_v1",
  "uid": "bioetl-runtime",
  "panel_id": 9401,
  "case": "telemetry_absent",
  "expected_state": "UNKNOWN",
  "expected_tokens": ["UNKNOWN"],
  "forbidden_tokens": ["OK"],
  "datasource": "prometheus",
  "payload": {}
}
```

- Prometheus cases: Prom API vector/scalar shape (`status=success`, empty `result` for absent).
- Ops HTTP cases: reuse `control_plane_validation` bodies where the endpoint already exists; do not fork Trust fixtures — **reference** them from the contract (`fixture_ref:`).
- `backend_error` MUST be distinct from `valid_empty` (HTTP 5xx / Infinity QUERY ERROR vs `rows=[]` + documented empty).
- Never encode `vector(0)` as a healthy verdict (`DASH-STATE-001`, `DASH-ZERO-001`).

Stage 2 minimum cases per enrolled verdict panel: `ok`, `telemetry_absent`, `backend_error`. Add `warn`/`crit`/`valid_empty` when the `state_model` includes them.

## 7. Implementation stages (PR DAG)

### PR1 — Contract skeleton + completeness (P0)

**Files**

- `docs/03-guides/dashboards/contracts/panel-content-contract.yaml` (Stage-1 10 panels)
- `docs/01-requirements/DASHBOARD_REQUIREMENTS.md` (`DASH-CONTENT-001/002/004`)
- `tests/integration/_dashboard_content_contract.py`
- `tests/integration/test_dashboard_content_contract.py`
- `tests/integration/test_dashboard_scope_truthfulness.py` (current vs `$__range` + `run_id` label only)
- `configs/quality/generated_artifact_routing.yaml` if a generated matrix is written
- `configs/quality/integration_vcr_policy.yaml` (new test paths)

**Done when:** every Stage-1 id has a complete row; first-screen `required_roles` resolve to first-window panels; CI green without Grafana.

### PR2 — State fixtures (P0)

**Files**

- `tests/fixtures/grafana/panel_states/**` for Runtime `9401`, Trust `9401`, DQ `9401`, Explorer `9402`
- `tests/integration/test_dashboard_state_fixture_contract.py`
- optional: thin interpreter that maps fixture payload → expected `noValue` / mapping text (no live Grafana)

**Done when:** each of those four panels has `ok` + `telemetry_absent` + `backend_error` (and `valid_empty` for `9402`).

### PR3 — Table content (P0)

**Files**

- Contract rows for Explorer `3010`, `9403`; Trust `9418`/`9416` if already first-window
- `tests/integration/test_dashboard_table_content_contract.py`
- join to `layout-budgets.yaml` caps

**Done when:** visible columns, hidden internals, `limit`/`topk`, and empty/error tokens are asserted from the contract.

### PR4 — Matrix completeness (P1)

**Files**

- `scripts/engineering/qa/report_dashboard_panel_audit_matrix.py` extra columns: `role`, `tier`, `scope`, `content_status`, `fixture_case_count`
- `tests/integration/test_dashboard_content_matrix_completeness.py`
- enroll remaining `key_panels` as `content_status: classified` (forensic may be `tier: 3` with empty fixture list)

**Done when:** a new shipped data panel without a contract row fails `--check`.

### PR5 — Descriptions / copy / visual-role (P1)

Migrate enrolled panels off `test_panels_have_descriptions` heuristics. Structured tokens only (`UNKNOWN`, `INCOMPLETE`, `TIME RANGE`, `SELECTED RUN`).

### PR6 — Render/a11y (P2, optional CI job)

`tests/e2e/test_dashboard_render_contract.py` + `tests/fixtures/grafana/render/`. Job `if: monitoring host`. No new local Docker requirement.

## 8. Anti-patterns (fail the review if present)

- Screenshot diff as the only gate.
- Global regex over `description` / HTML.
- Title-string skip lists (the current description test pattern).
- Duplicating inventory UID/title into a second SSOT without a join test.
- Raising `first_screen_max_panels`, FIT-001 viewport, or tech-debt budgets to make fixtures “fit”.
- `or vector(0)` on verdict fixtures.
- `run_id` Prometheus labels.
- Starting `docker-compose.monitoring.yml` for PR1–PR4.
- Bumping `control_plane_validation_evidence_v1` for display-only fields.

## 9. Suggested first backlog (this week)

1. PR1 contract for the 10 Stage-1 panels.
2. PR2 fixtures: UNKNOWN / INCOMPLETE / ERROR / VALID EMPTY on Trust+Runtime+DQ+Explorer answer surfaces.
3. PR3 table contract: Processed Records (`9403`) + Inspect Recent Runs (`3010`).
4. Stop. Do not start screenshot/a11y until 1–3 are green on `main`.

## 10. Verification commands (per PR)

```powershell
.\.venv-win\Scripts\python.exe -m pytest -q `
  tests/integration/test_dashboard_content_contract.py `
  tests/integration/test_dashboard_scope_truthfulness.py `
  tests/integration/test_dashboard_state_fixture_contract.py `
  tests/integration/test_dashboard_table_content_contract.py `
  tests/integration/test_dashboard_panel_audit_matrix_contract.py `
  tests/integration/test_dashboard_geometry_and_purpose_contracts.py `
  tests/integration/test_dashboard_first_window_containment.py
.\.venv-win\Scripts\python.exe -m scripts.engineering.qa report-dashboard-inventory --check --json
.\.venv-win\Scripts\python.exe -m scripts.engineering.qa report-dashboard-panel-audit-matrix --check
```

## 11. Open decisions (resolve in PR1, not later)

1. Is `first_screen.question` copied from `DASHBOARD_REQUIREMENTS.md` §7 or referenced by UID only? **Recommend UID + test that the §7 string is unchanged.**
2. Does `confidence` on Trust first screen mean `9401` (Prom current) or a dedicated telemetry card (`907`)? **Recommend `907` as confidence, `9401` as verdict.**
3. Are inventory `key_panels` that are *not* Stage-1 allowed to stay unclassified until PR4? **Yes — PR1 gate applies only to enrolled ids + answer map.**
4. Fixture interpreter: compare tokens in JSON mappings/`noValue` only (PR2), or also execute PromQL against a fake? **JSON/mappings only in PR2.**
