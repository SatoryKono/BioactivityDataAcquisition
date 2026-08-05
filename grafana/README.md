# BioETL Мониторинг: Prometheus + Grafana

**Версия документа:** 2.4.0
**Дата обновления:** 2026-07-28
**Статус:** Opt-in local adjunct (ADR-010) — not part of the default release bundle
**Совместимость:** BioETL v6.x (current main), Grafana 12, Prometheus 3.x

> **Removed 2026-07-23:** Loki, Promtail, Tempo, Quarantine Explorer UI
> (`bioetl quarantine serve` / Infinity “Quarantine Explorer” / Silver Reject Explorer dashboard).
> Domain Medallion quarantine write-path is unchanged. Identity panels now use
> **BioETL Ops HTTP** → main health server `:8000`. See
> `docs/05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md`.
>
> Monitoring stack is **opt-in only** (`make docker-start-monitoring`).
>
> **Dashboards: 7 JSON** — primary `bioetl-control-plane-v1`, `bioetl-overview-v2`,
> `bioetl-runtime`, `bioetl-provider-health-v2`, `bioetl-dq-v2`, plus
> `bioetl-incident-v1` and `bioetl-run-explorer-v1` (Dashboard System 2.0 / #6800).
> Retired: workflow/alerts merged into Runtime/Overview bands.
>
> **Dashboard System 2.0 track:** `docs/03-guides/dashboards/operator-ux-v2.md`.
>
> **Optional Scenes shadow path:** `grafana/plugins/bioetl-scenes-app` provides
> six read-only task routes under ADR-053. It is disabled by default; the seven
> JSON UIDs remain authoritative and are the tested rollback surface. See
> `docs/03-guides/dashboards/scenes-dual-path.md`.

______________________________________________________________________


## Shipped dashboard surface (2026-07-28)

**Seven** dashboards under `grafana/dashboards/` (portfolio cap ≤7):

0. `bioetl-control-plane-v1` — Trust / Control Plane Explorer
1. `bioetl-overview-v2` — Overview / Fleet Command Center
2. `bioetl-runtime` — Pipeline Diagnostics (includes retired Workflow band evidence)
3. `bioetl-provider-health-v2` — Provider Health / Provider Explorer
4. `bioetl-dq-v2` — Data Quality / Data Trust Explorer
5. `bioetl-incident-v1` — Incident Workspace
6. `bioetl-run-explorer-v1` — Run Explorer

Retired (do not reintroduce without architecture review): Workflow Overview, Alerts & SLO, Silver Reject Explorer, Loki/Tempo Explore-only surfaces.

Render/audit gates fail closed on blank screenshots and `renderedPanelCount=0` (#6686).
Deployed Grafana JSON must match repo after stripping volatile `id` / `version` / `pluginVersion` fields (#6690).

Navigation bus panel (id=1000) HTML/links refresh:

```bash
python scripts/ops/observability/grafana/render_nav_bus.py
```

## Содержание

1. [Архитектура мониторинга](#1-%D0%B0%D1%80%D1%85%D0%B8%D1%82%D0%B5%D0%BA%D1%82%D1%83%D1%80%D0%B0-%D0%BC%D0%BE%D0%BD%D0%B8%D1%82%D0%BE%D1%80%D0%B8%D0%BD%D0%B3%D0%B0)
1. [Цепочка данных: от кода до графика](#2-%D1%86%D0%B5%D0%BF%D0%BE%D1%87%D0%BA%D0%B0-%D0%B4%D0%B0%D0%BD%D0%BD%D1%8B%D1%85-%D0%BE%D1%82-%D0%BA%D0%BE%D0%B4%D0%B0-%D0%B4%D0%BE-%D0%B3%D1%80%D0%B0%D1%84%D0%B8%D0%BA%D0%B0)
1. [Быстрый запуск](#3-%D0%B1%D1%8B%D1%81%D1%82%D1%80%D1%8B%D0%B9-%D0%B7%D0%B0%D0%BF%D1%83%D1%81%D0%BA)
1. [Конфигурация инфраструктуры](#4-%D0%BA%D0%BE%D0%BD%D1%84%D0%B8%D0%B3%D1%83%D1%80%D0%B0%D1%86%D0%B8%D1%8F-%D0%B8%D0%BD%D1%84%D1%80%D0%B0%D1%81%D1%82%D1%80%D1%83%D0%BA%D1%82%D1%83%D1%80%D1%8B)
1. [Полный каталог метрик BioETL](#5-%D0%BF%D0%BE%D0%BB%D0%BD%D1%8B%D0%B9-%D0%BA%D0%B0%D1%82%D0%B0%D0%BB%D0%BE%D0%B3-%D0%BC%D0%B5%D1%82%D1%80%D0%B8%D0%BA-bioetl)
1. [Переменные фильтрации (Template Variables)](#6-%D0%BF%D0%B5%D1%80%D0%B5%D0%BC%D0%B5%D0%BD%D0%BD%D1%8B%D0%B5-%D1%84%D0%B8%D0%BB%D1%8C%D1%82%D1%80%D0%B0%D1%86%D0%B8%D0%B8-template-variables)
1. [Архивная заметка: legacy v1 dashboard surfaces](#8-%D0%B0%D1%80%D1%85%D0%B8%D0%B2%D0%BD%D0%B0%D1%8F-%D0%B7%D0%B0%D0%BC%D0%B5%D1%82%D0%BA%D0%B0-legacy-v1-dashboard-surfaces)
1. [Дашборд: 1. Overview](#9-дашборд-1-overview)
   13.1. [Дашборд: 2. Runtime](#131-%D0%B4%D0%B0%D1%88%D0%B1%D0%BE%D1%80%D0%B4-2-runtime)
1. [Дашборд: 3. Provider Health](#13-%D0%B4%D0%B0%D1%88%D0%B1%D0%BE%D1%80%D0%B4-3-provider-health)
1. [Дашборд: 4. Data Quality](#11-%D0%B4%D0%B0%D1%88%D0%B1%D0%BE%D1%80%D0%B4-4-data-quality)
1. [Дашборд: Silver Reject Explorer (REMOVED)](#12-дашборд-silver-reject-explorer)
1. [Справочник PromQL-паттернов](#14-%D1%81%D0%BF%D1%80%D0%B0%D0%B2%D0%BE%D1%87%D0%BD%D0%B8%D0%BA-promql-%D0%BF%D0%B0%D1%82%D1%82%D0%B5%D1%80%D0%BD%D0%BE%D0%B2)
1. [Устранение неполадок](#15-%D1%83%D1%81%D1%82%D1%80%D0%B0%D0%BD%D0%B5%D0%BD%D0%B8%D0%B5-%D0%BD%D0%B5%D0%BF%D0%BE%D0%BB%D0%B0%D0%B4%D0%BE%D0%BA)
1. [Архитектурные решения и обоснования](#16-%D0%B0%D1%80%D1%85%D0%B8%D1%82%D0%B5%D0%BA%D1%82%D1%83%D1%80%D0%BD%D1%8B%D0%B5-%D1%80%D0%B5%D1%88%D0%B5%D0%BD%D0%B8%D1%8F-%D0%B8-%D0%BE%D0%B1%D0%BE%D1%81%D0%BD%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D1%8F)
1. [Подробный разбор типов метрик Prometheus](#17-%D0%BF%D0%BE%D0%B4%D1%80%D0%BE%D0%B1%D0%BD%D1%8B%D0%B9-%D1%80%D0%B0%D0%B7%D0%B1%D0%BE%D1%80-%D1%82%D0%B8%D0%BF%D0%BE%D0%B2-%D0%BC%D0%B5%D1%82%D1%80%D0%B8%D0%BA-prometheus)
1. [Medallion Architecture и метрики](#18-medallion-architecture-%D0%B8-%D0%BC%D0%B5%D1%82%D1%80%D0%B8%D0%BA%D0%B8)
1. [Circuit Breaker и мониторинг провайдеров](#19-circuit-breaker-%D0%B8-%D0%BC%D0%BE%D0%BD%D0%B8%D1%82%D0%BE%D1%80%D0%B8%D0%BD%D0%B3-%D0%BF%D1%80%D0%BE%D0%B2%D0%B0%D0%B9%D0%B4%D0%B5%D1%80%D0%BE%D0%B2)
1. [Data Quality Monitor (DQMonitorPort)](#20-data-quality-monitor-dqmonitorport)
1. [Rate Limiting и его мониторинг](#21-rate-limiting-%D0%B8-%D0%B5%D0%B3%D0%BE-%D0%BC%D0%BE%D0%BD%D0%B8%D1%82%D0%BE%D1%80%D0%B8%D0%BD%D0%B3)
1. [Рекомендации по созданию пользовательских дашбордов](#22-%D1%80%D0%B5%D0%BA%D0%BE%D0%BC%D0%B5%D0%BD%D0%B4%D0%B0%D1%86%D0%B8%D0%B8-%D0%BF%D0%BE-%D1%81%D0%BE%D0%B7%D0%B4%D0%B0%D0%BD%D0%B8%D1%8E-%D0%BF%D0%BE%D0%BB%D1%8C%D0%B7%D0%BE%D0%B2%D0%B0%D1%82%D0%B5%D0%BB%D1%8C%D1%81%D0%BA%D0%B8%D1%85-%D0%B4%D0%B0%D1%88%D0%B1%D0%BE%D1%80%D0%B4%D0%BE%D0%B2)
1. [FAQ (Часто задаваемые вопросы)](#23-faq-%D1%87%D0%B0%D1%81%D1%82%D0%BE-%D0%B7%D0%B0%D0%B4%D0%B0%D0%B2%D0%B0%D0%B5%D0%BC%D1%8B%D0%B5-%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%D1%8B)
1. [Alerting (Настройка оповещений)](#24-alerting-%D0%BD%D0%B0%D1%81%D1%82%D1%80%D0%BE%D0%B9%D0%BA%D0%B0-%D0%BE%D0%BF%D0%BE%D0%B2%D0%B5%D1%89%D0%B5%D0%BD%D0%B8%D0%B9)
1. [Глоссарий](#25-%D0%B3%D0%BB%D0%BE%D1%81%D1%81%D0%B0%D1%80%D0%B8%D0%B9)
1. [Сводная таблица дашбордов](#26-%D1%81%D0%B2%D0%BE%D0%B4%D0%BD%D0%B0%D1%8F-%D1%82%D0%B0%D0%B1%D0%BB%D0%B8%D1%86%D0%B0-%D0%B4%D0%B0%D1%88%D0%B1%D0%BE%D1%80%D0%B4%D0%BE%D0%B2)
1. [Metric lifecycle reference boundary](#27-metric-lifecycle-reference-boundary)
1. [Безопасность и production-конфигурация](#28-%D0%B1%D0%B5%D0%B7%D0%BE%D0%BF%D0%B0%D1%81%D0%BD%D0%BE%D1%81%D1%82%D1%8C-%D0%B8-production-%D0%BA%D0%BE%D0%BD%D1%84%D0%B8%D0%B3%D1%83%D1%80%D0%B0%D1%86%D0%B8%D1%8F)
1. [Интеграция с CI/CD](#29-%D0%B8%D0%BD%D1%82%D0%B5%D0%B3%D1%80%D0%B0%D1%86%D0%B8%D1%8F-%D1%81-cicd)

______________________________________________________________________

> Примечание: shipped pack = **7 JSON** (Control Plane, Overview, Runtime,
> Provider Health, Data Quality, Incident, Run Explorer). Workflow Overview,
> Alerts & SLO, Silver Reject Explorer, Loki/Tempo Explore-only surfaces
> **removed** (see top-of-file callout and §8 / §12 archival notes).
> Исторические v1 walkthroughs below are archival only — treat panel tables as
> non-authoritative vs `grafana/dashboards/*.json`.
>
> Роль этого документа: setup/reference для monitoring stack.
> Для operator quick-start используйте сначала
> `docs/03-guides/dashboards/monitoring-index.md`,
> `docs/03-guides/dashboards/dashboard-v2-usage.md` и
> `docs/05-operations/01-monitoring-guide.md`.
>
> Для reproducible dashboard evidence shipped ops-tooling now exposes:
> `python -m scripts.ops rerender-grafana` for screenshots. It renders from
> repo-local dashboard JSON, uses explicit Grafana auth for render-sensitive
> probes, and automatically falls back to the repo-local Playwright renderer
> when the render API fails or times out.
> Reproducible evidence passes explicit `--theme dark|light`, `--width`, and
> `--height`; the Playwright manifest records requested and actual theme and
> viewport. Closure runs cover `1600px` and responsive `1024px` in both themes.
> The canonical audit matrix command is
> `python -m scripts.ops render-grafana-matrix`. It captures 1366×768,
> 1440×900, and 1920×1080 first viewports in Dark and Light, one expanded
> full-surface group, a repeated 1440×900 Dark group for geometry consistency,
> and verified 2560×1440/3840×2160 kiosk groups in both themes. Browser
> manifests record the requested and actual theme, viewport, kiosk state,
> 100% zoom, panel terminal states, horizontal overflow, and stable panel
> geometry. Live values and timestamps are excluded from consistency
> comparison.
> Playwright mode additionally requires the local `playwright` npm dependency,
> downloaded browser runtime, and the usual headless Chromium shared libraries
> (`libnspr4`, `libnss3`, `libasound2`/`libasound2t64`, etc.) on the host.
> The Linux bootstrap checks the full supported Chromium library surface
> (`libatk-bridge`, `libcups`, `libdrm`, `libgbm`, `libxkbcommon`, X11
> compositing libs, and related NSS/NSPR/audio libs) before attempting capture,
> and prints the corresponding apt package set when the host is incomplete.
> When root/sudo is unavailable, the Linux bootstrap downloads the missing
> `.deb` packages, extracts them under
> `.cache/grafana-screenshot-runtime/root`, and the render tooling
> automatically adds that library directory to `LD_LIBRARY_PATH`.
> To bootstrap that runtime on a fresh host, use
> `bash scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.sh`.
> The bootstrap now forces repo-local devDependency installation
> (`npm ci --include=dev` when `package-lock.json` is present, with production
> flags disabled) before downloading Chromium, so audit hosts do not silently
> skip the `playwright` package under production-like npm defaults. If the
> repo worktree itself is not writable enough for `node_modules` refresh,
> the shell bootstrap falls back to an isolated tool-cache install and exports
> `BIOETL_PLAYWRIGHT_NODE_MODULES`/`NODE_PATH` for the rerender tooling.
> On Windows PowerShell use
> `powershell -ExecutionPolicy Bypass -File scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.ps1`.
> The PowerShell bootstrap now downloads a portable Node.js LTS toolchain
> from the official Node.js distribution site when `node`/`npm` are not on
> `PATH`, so a global Node installation is no longer required on Windows.
> It also uses the active `python` command or the repo-local
> `.venv-win\Scripts\python.exe`, so a global `uv` install is not required.
> For local screenshot smoke, set Grafana credentials from the supported runtime
> env only: `GF_SECURITY_ADMIN_PASSWORD` / `GRAFANA_PASSWORD` (and optional
> `GRAFANA_USERNAME` / `GF_SECURITY_ADMIN_USER`). Prefer `GRAFANA_PASSWORD` for
> the password that already exists on the Grafana volume — `GF_SECURITY_ADMIN_PASSWORD`
> is first-boot only and may not match a long-lived volume. Do not commit or
> document a default password; preflight fails closed when auth material is missing.
> When host Chromium launch is flaky (common on Windows GDrive/WSL `/mnt` paths),
> use the Docker Playwright capture path:
> `bash scripts/ops/observability/grafana/capture_grafana_screenshots_docker.sh`.
> To render every shipped dashboard after bootstrap on Windows, use
> `powershell -ExecutionPolicy Bypass -File scripts/ops/observability/grafana/render_all_grafana_screenshots.ps1`.
> That helper also reuses or auto-downloads the same portable Node.js LTS
> toolchain when `node` is not present in the current PowerShell `PATH`.
> Shipped forensic/detail rows are collapsed by default. Full-audit Playwright
> mode can expand them, scroll through the page, and materialize lazy panels
> before capture without changing the shipped progressive-disclosure layout.
> Grafana Render API screenshots remain valid render/semantic evidence, but
> a full-surface UX audit must
> have `expanded-row-capture: ok` in
> `python -m scripts.ops check-grafana-audit-preflight` and use the Playwright
> screenshot path.
> Full-page capture now uses a separate screenshot budget
> (`GRAFANA_SCREENSHOT_CAPTURE_TIMEOUT_MS`, default `max(page_timeout, 180000)`),
> because long dashboards such as `0. Control Plane` may finish loading well
> before Playwright finishes writing the final PNG.
> The Playwright fallback also waits `GRAFANA_SCREENSHOT_SETTLE_MS` before
> materializing/capturing dashboards (default `12000`) so Grafana's virtualized
> grid has time to paint operator panels after variables and rows settle.
> `python -m scripts.ops audit-live-grafana` remains the reviewed live
> datasource/frame audit. It now starts from the curated semantically sensitive
> checks and then expands coverage from shipped dashboard JSON so every
> executable Prometheus, HTTP, Loki, and Tempo handoff target gets an evidence
> row or an explicit blocked/expected-empty classification.
> It polls Loki `/ready` within a governed total `15s` readiness/query budget.
> Loki lookback is bounded to at most one hour: Runtime panels `#250` and `#251`
> use `query_range`, while instant aggregation panel `#257` uses `/query`.
> Sparse logs are not treated as a datasource outage, but all three panels are
> required semantic evidence and backend unavailability therefore blocks the
> gate. Missing DQ freshness samples are reported as
> `telemetry_missing`: the corresponding panels render `UNKNOWN`, never a false
> healthy zero.
> `python -m scripts.ops check-grafana-audit-preflight` is the fast readiness
> gate for full dashboard audits: it verifies Grafana, explicit
> `frontend/settings` render auth, Prometheus, Playwright browser/runtime
> availability, canonical BioETL Ops HTTP health probes (`/health/live`
> before `/health`), and whether local screenshot artifacts are missing or
> stale relative to shipped dashboard JSON. The retired Quarantine Explorer
> HTTP/UI surface is reported as `not_applicable`, not as a backend failure;
> domain quarantine write/storage is unchanged. If its retired dashboard UID is
> ever shipped again, preflight restores the fail-closed health probe.
> Playwright also validates required non-row panel terminal states. Healthy,
> explicit error, and valid-empty are terminal; blank, loading, or an error
> marker combined with `No data` fail the capture. Screenshot preflight verifies
> the manifest's actual theme/viewport and terminal-state result.
> `python -m scripts.ops run-grafana-audit-cycle` is the canonical full audit
> workflow. It reports two independent release outcomes in
> `reports/observability/grafana/dashboard-release-gates.json`:
> `dashboard_semantic_gate` covers datasource/backend readiness and the reviewed
> live panel audit, while `dashboard_render_gate` covers render auth,
> Playwright/expanded-row capture, screenshots, and the render manifest. The
> semantic audit runs before screenshot refresh, but both gates always record
> their own terminal result: a browser-host failure does not hide PromQL,
> LogQL, HTTP, or datasource evidence, and a semantic failure does not skip a
> viable screenshot/manifest check. The final render preflight uses
> `--skip-semantic-checks`, so Prometheus or BioETL Ops HTTP availability
> cannot contaminate the browser verdict.
> A release occurrence is cryptographically traceable rather than path-only:
> the semantic report, render manifest, and gate receipt share one
> `occurrence_id`; the receipt records commit/tree identity, SHA-256, terminal
> status, and dashboard/panel scope for both source artifacts. Render panel scope
> is read from `terminalStateValidation.panelStates`; UID-only, missing, or
> cross-occurrence evidence fails closed. Unit tests with a temporary screenshot
> directory also write their gate beside that directory and cannot overwrite the
> canonical repository report.
>
> Default CI runs a token-free semantic policy/fixture gate and uploads the
> `dashboard-semantic-policy` artifact. That artifact includes metric inventory,
> JSON/provisioning, selector/variable-reference, panel-contract drift,
> registry/runtime/docs bidirectionality, datasource-boundary, and no-data
> evidence. Browser rendering is host-only and manual
> via `.github/workflows/dashboard-render-host.yml`; that workflow uploads the
> semantic source, render source, and combined receipt independently. Local
> review may run either path, default CI blocks on semantic policy, and release
> requires both live gates from the same supported-host occurrence. Unknown
> semantic classifications fail closed to explicit review.
>
> Semantic severity is fail-closed and panel-attributable in the live audit
> artifact. `query_invalid` blocks. `datasource_unavailable` and
> `blocked_backend_unavailable` block required panels. `empty_result` and
> `unknown_result` require explicit review. `zero_result` and `expected_empty`
> pass. `telemetry_missing` passes only for an explicitly reviewed UID/panel
> contract (currently DQ freshness panels `bioetl-dq-v2#8` and `#101`, which
> render `UNKNOWN`). Each decision records dashboard UID, panel ID, datasource
> kind, required/optional status, original classification, canonical
> classification, and gate decision.
> Normal runtime files under `reports/logs/` are scraped by Promtail as
> `{job="bioetl"}`, matching Runtime panels `#250`, `#251`, and `#257`.
> Audit-only logs keep the separate `{job="bioetl-audit"}` boundary.
>
> If the
> discovery pass times out, the cycle falls back to the last successful
> `reports/observability/grafana/live-panel-audit.json` subset before failing
> hard. By default the cycle also force-refreshes the detached Quarantine
> Explorer backend before audit so stale route handlers from an older process
> are not silently reused; `--no-refresh-observability-backend` keeps the
> previous reuse-first behavior. If the backend on `8000` cannot be refreshed
> in place, the cycle can retry on a free localhost fallback port and use that
> port for preflight and live audit. If that fresh fallback backend also fails
> to become ready, the cycle degrades to the existing health-reachable backend
> on `8000` instead of aborting before screenshot refresh. Detached backend
> readiness now waits for both `/health` and required audit capability routes,
> with a longer startup budget for slower Windows hosts. By default it also
> reuses or auto-starts the detached
> `bioetl quarantine serve` backend on port `8000` before the first preflight,
> so `BioETL Ops HTTP`-backed panels can be validated without a separate
> manual backend bootstrap step.
> The detached backend reads Prometheus through `BIOETL_PROMETHEUS_URL` when
> set. Use the URL that is reachable from the backend process, not from the
> Grafana container: host/WSL backends usually use `http://127.0.0.1:9090`,
> while Docker-adjacent backends may need `http://host.docker.internal:9090`.
> `localhost:9090` is therefore only correct for topologies where Prometheus is
> actually bound on the same network namespace as `bioetl quarantine serve`.
>
> Operator state vocabulary is explicit: `OK/WARN/CRIT`, trust-gate
> `INCOMPLETE`, no-verdict `UNKNOWN`, explicit `ERROR`, and neutral terminal
> `VALID EMPTY` / `TELEMETRY ABSENT` / `N/A`. `LOADING` is transient only;
> accepted screenshots cannot contain a blank or still-loading required panel.

## 1. Архитектура мониторинга

### 1.1 Обзор

Система мониторинга BioETL построена по модели Pull (Prometheus scraping) и состоит из трёх компонентов, работающих в связке:

```
┌──────────────────────────────────────────────────────────────────┐
│                      BioETL Application                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Domain Layer (Ports)                                    │    │
│  │  ┌───────────┐  ┌────────────┐  ┌──────────────────┐   │    │
│  │  │MetricsPort│  │TracingPort │  │DQMonitorPort     │   │    │
│  │  │ (Protocol)│  │ (Protocol) │  │ (Protocol)       │   │    │
│  │  └─────┬─────┘  └──────┬─────┘  └────────┬─────────┘   │    │
│  └────────┼───────────────┼──────────────────┼─────────────┘    │
│           │               │                  │                   │
│  ┌────────┼───────────────┼──────────────────┼─────────────┐    │
│  │  Infrastructure Layer (Adapters)                         │    │
│  │  ┌─────┴──────────┐ ┌──┴──────────┐ ┌────┴───────────┐ │    │
│  │  │Prometheus      │ │NoOpTracing  │ │DataQuality     │ │    │
│  │  │Metrics         │ │             │ │Monitor         │ │    │
│  │  │(prometheus_    │ │(ADR-022)    │ │(anomaly.py)    │ │    │
│  │  │ client lib)    │ │             │ │                │ │    │
│  │  └─────┬──────────┘ └─────────────┘ └────────────────┘ │    │
│  └────────┼────────────────────────────────────────────────┘    │
│           │                                                      │
│  ┌────────┴────────────────────────────────────────────────┐    │
│  │  Metrics HTTP Server (server.py)                         │    │
│  │  prometheus_client.start_http_server(port=8000)          │    │
│  │  Формат: text/plain; version=0.0.4 (Prometheus exposition)│   │
│  └────────┬────────────────────────────────────────────────┘    │
└───────────┼──────────────────────────────────────────────────────┘
            │
            │  HTTP GET /metrics (каждые 30 секунд)
            │
┌───────────┴──────────────────────────────────────────────────────┐
│  Prometheus Server (порт 9090)                                   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  TSDB (Time-Series Database)                              │    │
│  │  - Хранит все time series с timestamps                    │    │
│  │  - Retention: по умолчанию 15 дней                        │    │
│  │  - Persistent volume: prometheus-data                     │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Конфигурация: grafana/prometheus.yml                            │
│  - global scrape_interval: 15s                                   │
│  - bioetl job scrape_interval: 30s                               │
│  - bioetl target: bioetl:8000 (canonical compose network)        │
│  - host override (optional): host.docker.internal:8000           │
└───────────┬──────────────────────────────────────────────────────┘
            │
            │  PromQL запросы (HTTP API)
            │
┌───────────┴──────────────────────────────────────────────────────┐
│  Grafana Server (порт 3000)                                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Provisioning (автоматическая загрузка)                    │    │
│  │  - Datasources: Prometheus + BioETL Ops HTTP (:8000) │    │
│  │  - Dashboards: 7 JSON files (bioetl.yaml)                │    │
│  │  - Обновление каждые 30 секунд                            │    │
│  │  - allowUiUpdates: false для production dashboard-as-code  │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Дашборды (shipped, bus 0..6):                                   │
│  - 0. Trust / Control Plane (bioetl-control-plane-v1)            │
│  - 1. Overview (bioetl-overview-v2)                              │
│  - 2. Pipeline Diagnostics / Runtime (bioetl-runtime)            │
│  - 3. Provider Health (bioetl-provider-health-v2)                │
│  - 4. Data Quality (bioetl-dq-v2)                                │
│  - 5. Incident Workspace (bioetl-incident-v1)                    │
│  - 6. Run Explorer (bioetl-run-explorer-v1)                      │
│  - Retired: workflow-overview, alerts-slo, silver-reject-explorer│
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Принципы проектирования

Observability-подсистема BioETL следует принципам Hexagonal Architecture (ADR-017):

- **MetricsPort** (Protocol) определён в domain-слое (`src/bioetl/domain/ports/observability/metrics.py`). Это canonical package-based контракт, не знающий о конкретной реализации. MetricsPort предоставляет методы `observe_histogram()`, `increment_counter()`, `set_gauge()` и `close()`.

- **PrometheusMetrics** (Adapter) реализует MetricsPort в infrastructure-слое (`src/bioetl/infrastructure/observability/prometheus_metrics.py`). Использует библиотеку `prometheus_client` для создания и экспорта метрик.

- **NoOpMetrics** — Null Object реализация MetricsPort (`src/bioetl/domain/ports/noop/_metrics.py`). Используется когда метрики отключены (`BIOETL_METRICS_ENABLED=false`). Все вызовы становятся no-op без каких-либо побочных эффектов.

- **Composition Root** собирает зависимости в `src/bioetl/composition/bootstrap/runtime/observability.py`. Функция `bootstrap_metrics_port(settings)` создаёт PrometheusMetrics или NoOpMetrics в зависимости от настроек. Функция `maybe_start_metrics_server(settings)` запускает HTTP-сервер для экспорта метрик.

Такая архитектура обеспечивает:

- Application и Domain код не зависит от Prometheus.
- Переключение на другой бэкенд (StatsD, CloudWatch) требует только новый Adapter и изменение wiring в Composition Root.
- В тестах можно подставить NoOpMetrics или мок, не трогая бизнес-логику.

### 1.3 Файловая структура

```
grafana/
├── README.md                          # Этот документ
├── prometheus.yml                     # Конфигурация Prometheus scraper
├── provisioning/
│   ├── datasources-core/
│   │   ├── prometheus.yml             # Datasource: Prometheus → Grafana
│   │   └── bioetl-ops-http.yml        # Datasource: BioETL Ops HTTP (Infinity)
│   ├── datasources-tracing/           # removed 2026-07-23 (no Loki/Tempo ship)
│   └── dashboards/
│       └── bioetl.yaml                # Dashboard provisioning config
└── dashboards/
    ├── bioetl-control-plane-v1.json   # 0. Trust / Control Plane
    ├── bioetl-overview-v2.json        # 1. Overview (+ collapsed Alert/SLO triage)
    ├── bioetl-runtime.json            # 2. Pipeline Diagnostics (workflow band)
    ├── bioetl-provider-health-v2.json # 3. Provider Health (v2)
    ├── bioetl-dq-v2.json              # 4. Data Quality (v2)
    ├── bioetl-incident-v1.json        # 5. Incident Workspace
    └── bioetl-run-explorer-v1.json    # 6. Run Explorer (Ops HTTP identity)

docker-compose.monitoring.yml          # Opt-in: Prometheus + Pushgateway + Grafana + renderer

src/bioetl/
├── domain/ports/observability/        # MetricsPort, TracingPort, LoggerPort, DQMonitorPort (Protocols)
├── domain/ports/noop/                 # NoOpMetrics and other null-object ports
└── infrastructure/observability/
    ├── metrics.py                     # Runtime-export surface for Prometheus metric objects
    ├── metrics_definitions.py         # Compatibility aggregate export surface
    ├── _metrics_defs_*.py             # Canonical grouped metric definitions
    ├── prometheus_metric_registries.py # Canonical COUNTERS/GAUGES/HISTOGRAMS inventory
    ├── prometheus_metric_label_dispatch.py # Bounded label dispatch and validation
    ├── prometheus_metric_label_policy_sets.py # Label allow/deny policy sets
    ├── prometheus_metrics.py          # PrometheusMetrics adapter (реализация MetricsPort)
    ├── server.py                      # HTTP-сервер для /metrics endpoint
    └── anomaly/                       # DataQualityMonitor implementation family
```

______________________________________________________________________

## 2. Цепочка данных: от кода до графика

### 2.1 Шаг 1: Определение метрик в коде

Шипуемые метрики определяются в модульных файлах `src/bioetl/infrastructure/observability/_metrics_defs_*.py` и собираются в registry-backed inventory через `src/bioetl/infrastructure/observability/prometheus_metric_registries.py`. Модуль `src/bioetl/infrastructure/observability/metrics.py` остаётся runtime-export surface для готовых Prometheus objects, а `metrics_definitions.py` — compatibility/aggregate export surface. Каждая метрика имеет:

- **Имя** (с префиксом `bioetl_`) — глобально уникальный идентификатор в формате Prometheus.
- **Описание** — человекочитаемое описание метрики.
- **Labels** (лейблы) — набор ключей для мультидименсиональной фильтрации.
- **Тип** — Counter (монотонно растёт), Histogram (распределение значений), Gauge (произвольное значение).

Пример определения Counter-метрики:

```python
# src/bioetl/infrastructure/observability/metrics.py

RECORDS_PROCESSED_TOTAL = Counter(
    "bioetl_records_processed_total",  # Имя в Prometheus
    "Total number of records processed",  # Описание
    ["pipeline", "stage", "run_type"],  # Labels
)
```

Пример определения Histogram-метрики с пользовательскими бакетами:

```python
ADAPTER_REQUEST_DURATION_SECONDS = Histogram(
    "bioetl_adapter_request_duration_seconds",
    "Duration of adapter API requests in seconds",
    ["provider", "endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)
```

### 2.2 Шаг 2: Запись значений через MetricsPort

Application-код использует MetricsPort (Protocol) для записи метрик. Вот как это выглядит в пайплайне:

```python
# Где-то в application-слое (упрощённо):

# Инкремент counter
self._metrics.increment_counter(
    "records_processed_total",
    value=batch_size,
    labels={"pipeline": "chembl", "stage": "bronze", "run_type": "incremental"},
)

# Запись длительности в histogram
self._metrics.observe_histogram(
    "pipeline_duration_seconds",
    value=elapsed_seconds,
    labels={
        "pipeline": "chembl",
        "stage": "fetch",
        "status": "success",
        "run_type": "incremental",
    },
)

# Установка gauge
self._metrics.set_gauge(
    "circuit_breaker_state",
    value=0,  # 0=closed
    labels={"adapter": "chembl"},
)
```

`PrometheusMetrics` (adapter) маппит строковое имя метрики на соответствующий Prometheus-объект через словари `HISTOGRAMS`, `COUNTERS`, `GAUGES`:

```python
# src/bioetl/infrastructure/observability/prometheus_metrics.py


class PrometheusMetrics(MetricsPort):
    def increment_counter(self, name: str, value: int, labels: dict[str, str]) -> None:
        if name in COUNTERS:
            COUNTERS[name].labels(**labels).inc(value)
```

### 2.3 Шаг 3: Экспорт через HTTP-сервер

При запуске пайплайна `server.py` поднимает HTTP-сервер на порту 8000 (настраивается через `BIOETL_METRICS_PORT`):

```python
# src/bioetl/infrastructure/observability/server.py
from prometheus_client import start_http_server

def start_metrics_server(port: int = 8000, addr: str = "0.0.0.0", ...) -> bool:
    start_http_server(port, addr=addr)
```

Сервер отдаёт метрики в формате Prometheus exposition (`text/plain; version=0.0.4`). Пример ответа на `GET http://localhost:8000/metrics`:

```
# HELP bioetl_records_processed_total Total number of records processed by the pipeline
# TYPE bioetl_records_processed_total counter
bioetl_records_processed_total{pipeline="chembl",stage="bronze",run_type="incremental"} 15420.0
bioetl_records_processed_total{pipeline="chembl",stage="silver",run_type="incremental"} 15380.0
bioetl_records_processed_total{pipeline="chembl",stage="gold",run_type="incremental"} 15102.0
bioetl_records_processed_total{pipeline="chembl",stage="filtered_out",run_type="incremental"} 40.0
bioetl_dq_records_quarantined_total{pipeline="chembl",error_type="schema_violation",run_type="incremental"} 278.0

# HELP bioetl_pipeline_duration_seconds Duration of pipeline runs in seconds
# TYPE bioetl_pipeline_duration_seconds histogram
bioetl_pipeline_duration_seconds_bucket{le="0.005",pipeline="chembl",stage="fetch",status="success",run_type="incremental"} 0.0
bioetl_pipeline_duration_seconds_bucket{le="0.01",pipeline="chembl",stage="fetch",status="success",run_type="incremental"} 0.0
...
bioetl_pipeline_duration_seconds_sum{pipeline="chembl",stage="fetch",status="success",run_type="incremental"} 127.45
bioetl_pipeline_duration_seconds_count{pipeline="chembl",stage="fetch",status="success",run_type="incremental"} 3.0
```

Особенности HTTP-сервера:

- Запускается в daemon-потоке (не блокирует основной процесс).
- Thread-safe: `prometheus_client` гарантирует потокобезопасность.
- Если порт занят (`EADDRINUSE`), поведение зависит от `fail_fast`: при `true` бросает `MetricsServerError`, при `false` тихо продолжает работу без метрик.
- Поддерживает retry с экспоненциальным backoff (до 3 попыток по умолчанию).
- Идемпотентный запуск: второй вызов `start_metrics_server()` — no-op.

### 2.4 Шаг 4: Prometheus scraping

Canonical local-only topology scrapes BioETL over the monitoring compose network
at `bioetl:8000` every **30s** (`grafana/prometheus.yml`). Global Prometheus
defaults remain 15s for other jobs.

```yaml
# grafana/prometheus.yml (canonical defaults)
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'bioetl'
    scrape_interval: 30s
    static_configs:
      - targets: ['bioetl:8000']
    metrics_path: /metrics
```

**Host override (optional, not the default):** when BioETL metrics run on the
Docker host instead of the `bioetl` service, operators may temporarily point the
job at `host.docker.internal:8000`. On Windows/macOS that DNS works out of the
box; on Linux it may need `--add-host=host.docker.internal:host-gateway`.
Document any host override explicitly so it is not confused with the shipped
compose-network default.

Prometheus сохраняет каждый скрейп как набор time series (метрика + labels + timestamp + value) в локальную TSDB. Данные хранятся в Docker volume `prometheus-data` и переживают перезапуск контейнера.

### 2.5 Шаг 5: Grafana visualization

Grafana подключается к Prometheus как datasource и выполняет PromQL-запросы для визуализации данных:

```yaml
# grafana/provisioning/datasources-core/prometheus.yml
datasources:
  - name: Prometheus
    type: prometheus
    uid: prometheus
    access: proxy
    url: http://prometheus:9090    # Внутри Docker network
    isDefault: true
    editable: true
    jsonData:
      timeInterval: 15s
```

### Datasource configuration standard for shipped dashboards

Для shipped Prometheus **panel** datasource references в
`grafana/dashboards/*.json` используйте только явный object format:

```json
"datasource": {
  "type": "prometheus",
  "uid": "prometheus"
}
```

Правила для текущего repo contract:

- не использовать `${DS_PROMETHEUS}` в shipped dashboard JSON
- не полагаться на string panel datasource `"Prometheus"` там, где панель
  обращается к provisioned Prometheus datasource
- считать `grafana/provisioning/datasources-core/prometheus.yml` источником
  истины для provisioned UID (`prometheus`)
- template-variable datasource fields в legacy dashboards могут оставаться
  строковыми, но при целевых правках допускается и canonical object format
  `{ "type": "prometheus", "uid": "prometheus" }`

Валидация этого контракта выполняется существующим Grafana integration suite,
включая `tests/integration/test_grafana_config.py`.

Дашборды провизионируются автоматически при старте Grafana:

```yaml
# grafana/provisioning/dashboards/bioetl.yaml
providers:
  - name: 'BioETL'
    orgId: 1
    folder: 'BioETL'
    folderUid: 'bioetl'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30       # Проверяет изменения каждые 30 сек
    allowUiUpdates: false           # Production source of truth is Git JSON
    options:
      path: /var/lib/grafana/dashboards   # Mount point из docker-compose
```

______________________________________________________________________

## 3. Быстрый запуск

### 3.1 Запуск стека мониторинга

```bash
# Запуск базового стека метрик
make monitoring-up

# Или напрямую:
docker compose -f docker-compose.monitoring.yml up -d

# Запуск расширенного профиля с трассировкой и лог-корреляцией
make monitoring-tracing-up

# Или напрямую:
BIOETL_ENABLE_TRACING_DATASOURCES=true \
  docker compose -f docker-compose.monitoring.yml --profile tracing up -d

# Проверка статуса контейнеров
docker compose -f docker-compose.monitoring.yml ps

# Live smoke для Grafana datasource provisioning в двух режимах
python3 scripts/ops/observability/grafana/live_tracing_mode_smoke.py --mode both

# Просмотр логов
make monitoring-logs

# Остановка
make monitoring-down
```

### 3.2 Запуск пайплайна с метриками

```bash
# Убедитесь, что в .env:
# BIOETL_METRICS_ENABLED=true
# BIOETL_METRICS_PORT=8000
# BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED=true

# Запуск пайплайна
make run-local
# или: bioetl run --pipeline chembl-activity
```

### 3.3 Проверка работоспособности

```bash
# 1. Проверить, что Prometheus scrapes BioETL (canonical target: bioetl:8000)
curl -sS 'http://localhost:9090/api/v1/targets' | python -c "import sys,json; ts=json.load(sys.stdin)['data']['activeTargets']; print([(t['labels'].get('job'), t['health']) for t in ts if t['labels'].get('job')=='bioetl'])"
# Host-side /metrics is only available if the BioETL metrics port is published.
# Inside the monitoring compose network the scrape URL is http://bioetl:8000/metrics:
# docker exec bioetl curl -sS http://127.0.0.1:8000/metrics | grep bioetl_ | head

# 2. Проверить Prometheus targets
# Открыть http://localhost:9090/targets — job=bioetl должен быть "UP"

# 3. Открыть Grafana
# http://localhost:3000 (`admin`; runtime password via GRAFANA_PASSWORD /
# GF_SECURITY_ADMIN_PASSWORD — first-boot only for the Grafana volume)
# Перейти: Home → Dashboards → BioETL → выбрать дашборд
```

### 3.4 Переменные окружения

| Переменная                                     | Значение по умолчанию | Описание                                                |
| ---------------------------------------------- | --------------------- | ------------------------------------------------------- |
| `BIOETL_METRICS_ENABLED`                       | `true`                | Включить/выключить сбор метрик                          |
| `BIOETL_METRICS_PORT`                          | `8000`                | Порт HTTP-сервера метрик                                |
| `BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED` | `true`                | Запускать ли HTTP-сервер                                |
| `BIOETL_OBSERVABILITY__METRICS_FAIL_FAST`      | `false`               | Падать при ошибке запуска сервера                       |
| `BIOETL_OBSERVABILITY__METRICS_RETRY_COUNT`    | `3`                   | Количество попыток запуска (1-10)                       |
| `BIOETL_OBSERVABILITY__METRICS_RETRY_DELAY`    | `1.0`                 | Задержка между попытками (0.1-10.0 с)                   |
| `GF_SECURITY_ADMIN_PASSWORD`                   | обязательная          | Пароль admin **только при первом** создании Grafana volume; позже audit tools use `GRAFANA_PASSWORD` for the live instance password |
| `GRAFANA_PASSWORD`                             | runtime               | Live audit/render password for the running Grafana instance (may differ from the first-boot env once the volume exists) |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN`                | optional              | Preferred machine auth for render/audit when basic auth is undesirable |
| `GF_RENDERING_RENDERER_TOKEN`                  | обязательная          | Общий secret для Grafana и renderer `AUTH_TOKEN`; задаётся локально до запуска |
| `GRAFANA_IMAGE_RENDERER_GOMEMLIMIT`            | `2GiB`                | Go memory soft limit for the remote image renderer      |
| `GRAFANA_IMAGE_RENDERER_READINESS_TIMEOUT`     | `120s`                | Maximum wait for heavy dashboard pages before the remote renderer returns a timeout |
| `BIOETL_ENABLE_TRACING_DATASOURCES`            | `auto`                | Авто-подключать Loki/Tempo datasource в Grafana provisioning по live reachability (`true`/`false` override доступны) |
| `BIOETL_OBSERVABILITY__TRACING_ENABLED`        | `false`               | Включить OpenTelemetry spans и log-trace correlation    |
| `BIOETL_OBSERVABILITY__DQ_MONITOR_ENABLED`     | `true`                | Включить DQ anomaly monitor для всех pipeline runs       |

______________________________________________________________________

## 4. Конфигурация инфраструктуры

### 4.1 Docker Compose (`docker-compose.monitoring.yml`)

Базовый стек состоит из трёх сервисов, объединённых в bridge-сеть `monitoring`:

**Prometheus:**

- Supported series: `3.13.x`; the deterministic QA image is
  `prom/prometheus:v3.13.1`. The compose pin must remain in the same major/minor
  series as QA `promtool`.
- Container: `bioetl-prometheus`
- Порт: `9090:9090`
- Volumes:
  - `./grafana/prometheus.yml` → `/etc/prometheus/prometheus.yml` (конфигурация, read-only)
  - `prometheus-data` → `/prometheus` (persistent TSDB данные)
- Restart: `unless-stopped`

**Grafana:**

- Image: `grafana/grafana:12.0.0`
- Container: `bioetl-grafana`
- Порт: `3000:3000`
- Volumes:
  - `grafana-data` → `/var/lib/grafana` (persistent данные Grafana)
  - `./grafana/provisioning/datasources-core` → bootstrap-источник обязательных datasource
  - `./grafana/provisioning/datasources-tracing` → bootstrap-источник tracing datasource
  - `./grafana/provisioning/dashboards` → `/etc/grafana/provisioning/dashboards` (read-only)
  - `./grafana/dashboards` → `/var/lib/grafana/dashboards` (read-only, JSON-дашборды)
- Restart: `unless-stopped`

**Metrics emission topology (AUD-OBS-20260727 / #6731):**

| Path | Endpoint / job | Role |
| --- | --- | --- |
| Health scrape | `job=bioetl` → health `:8000/metrics` | Process **liveness** + in-process Prometheus registry exposition (`bioetl_health_server_scrape_up=1`). |
| Pushgateway | `job=pushgateway` / push `job=bioetl` | **Canonical batch terminal bridge** for short-lived CLI runs. |
| Process metrics server | ephemeral during runs when enabled | Optional mid-run scrape; not the long-lived compose default. |

- `up{job="bioetl"}=1` alone does **not** prove data-plane population. After a run,
  verify `increase(bioetl_pipeline_runs_total[…])` (or Pushgateway residual) and Ops
  HTTP identity/accounting shells.
- Control-plane identity (`run_id`, manifests) stays on Ops HTTP / ledger / CLI — never
  as Prometheus labels.

**Pushgateway:**

- Supported series: `1.11.x`; validate the deployed patch version through
  `pushgateway_build_info`.
- Container: `bioetl-pushgateway`
- Порт: `9091:9091`
- Restart: `unless-stopped`
- Default stack retains Pushgateway only as a short-lived batch bridge for
  bounded aggregate snapshots.
- Runtime publication uses replace-style `push_to_gateway` semantics, not
  additive `pushadd_to_gateway`, so a later snapshot replaces the previous
  snapshot for the same grouping key.
- Cleanup uses `delete_metrics_from_gateway` / `delete_from_gateway` with the
  same bounded grouping key.
- Allowed Pushgateway grouping labels are only `pipeline` and `run_type`;
  `run_id`, `record_id`, `payload_hash`, raw paths/URLs, and other forensic
  anchors remain in manifest/ledger/CLI/explorer surfaces, not Prometheus.
- CLI publishes via `publish_metrics_safely` after `bioetl run` / workflow completion
  (`best_effort_on_run_completion`).

### Optional log/trace backends (BYO — not shipping)

Loki, Promtail, Tempo, and Quarantine Explorer UI were **removed from the
shipping monitoring surface on 2026-07-23**. Do not document or provision them
as required BioETL local adjuncts.

- Use structured application logs on disk / process stdout and Prometheus
  metrics for default operator forensics.
- External log/trace backends remain **bring-your-own**; empty Grafana Explore
  for Loki/Tempo is expected on the default stack.
- Historical narrative about a compose `tracing` profile is **obsolete** —
  see `docs/05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md`.

### 4.2 Сетевая топология

```
Docker Network: monitoring (bridge) — canonical local topology
├── bioetl            → :8000 (/metrics)     [scraped every 30s]
├── bioetl-prometheus → :9090                [scrapes bioetl:8000]
├── bioetl-pushgateway → :9091
├── bioetl-grafana    → :3000                [queries prometheus:9090]
└── (removed) loki / promtail / tempo containers

Host override (optional):
└── BioETL App on host → localhost:8000
    Prometheus may scrape host.docker.internal:8000 only when operators
    intentionally replace the canonical bioetl:8000 job target.
```

Внутри Docker-сети Grafana обращается к Prometheus по имени сервиса `prometheus` (порт 9090). По умолчанию Prometheus скрейпит BioETL-приложение по compose-service DNS `bioetl:8000` (интервал 30s).

### 4.3 URL и порты

| Компонент          | URL                                | Порт | Назначение                              |
| ------------------ | ---------------------------------- | ---- | --------------------------------------- |
| BioETL Metrics     | `http://localhost:8000/metrics`    | 8000 | Prometheus exposition format            |
| Prometheus UI      | `http://localhost:9090`            | 9090 | Query interface, target status          |
| Prometheus Targets | `http://localhost:9090/targets`    | 9090 | Статус scrape targets                   |
| Prometheus API     | `http://localhost:9090/api/v1/...` | 9090 | HTTP API для PromQL                     |
| Pushgateway        | `http://localhost:9091`            | 9091 | Push endpoint для ad-hoc/ephemeral jobs |
| Grafana UI         | `http://localhost:3000`            | 3000 | Дашборды; password from `GF_SECURITY_ADMIN_PASSWORD` |
| Grafana Explore    | `http://localhost:3000/explore`    | 3000 | Ad-hoc PromQL (Prometheus only on default stack) |
| Grafana Dashboards | `http://localhost:3000/dashboards` | 3000 | Список дашбордов                        |
| Loki / Tempo / OTLP | —                                 | —    | **Not shipping** (removed 2026-07-23); BYO only |

______________________________________________________________________

## 5. Полный каталог метрик BioETL

Все canonical metric families определены в `src/bioetl/infrastructure/observability/_metrics_defs_*.py` и опубликованы через `src/bioetl/infrastructure/observability/prometheus_metric_registries.py`. `src/bioetl/infrastructure/observability/metrics.py` является runtime-export surface для Prometheus objects.

Каждая метрика автоматически получает префикс `bioetl_` от Prometheus. Для Histogram-метрик Prometheus автоматически создаёт суффиксы: `_bucket` (бакеты распределения), `_sum` (сумма всех наблюдений), `_count` (количество наблюдений), `_created` (timestamp создания). Для Counter-метрик автоматически создаётся `_total` суффикс и `_created` timestamp.

### 5.1 Pipeline Metrics (основные метрики пайплайна)

| Метрика                            | Тип       | Labels                                    | Описание                                                                                 |
| ---------------------------------- | --------- | ----------------------------------------- | ---------------------------------------------------------------------------------------- |
| `bioetl_pipeline_duration_seconds` | Histogram | `pipeline`, `stage`, `status`, `run_type` | Длительность выполнения стадий пайплайна в секундах. Status: success/failure.            |
| `bioetl_records_processed_total`   | Counter   | `pipeline`, `stage`, `run_type`           | Суммарное количество обработанных записей. Stage: bronze, silver, gold, quarantined.     |
| `bioetl_errors_total`              | Counter   | `pipeline`, `stage`, `error_code`         | Суммарное количество ошибок. Error_code — машиночитаемый код ошибки.                     |
| `bioetl_batch_size_records`        | Histogram | `pipeline`, `stage`                       | Распределение размеров батчей (количество записей). Buckets: 100, 500, 1K, 5K, 10K, 50K. |
| `bioetl_pipeline_runs_total`       | Counter   | `pipeline`, `run_type`, `status`          | Количество запусков пайплайна. Run_type: incremental, backfill, rebuild.                 |
| `bioetl_phase_duration_seconds`    | Histogram | `pipeline`, `phase`, `status`             | Длительность фаз жизненного цикла пайплайна (fetch, transform, load).                    |

### 5.2 Input Filter Metrics

| Метрика                                   | Тип     | Labels                    | Описание                                             |
| ----------------------------------------- | ------- | ------------------------- | ---------------------------------------------------- |
| `bioetl_filter_ids_loaded_total`          | Counter | `pipeline`, `source_kind` | Количество уникальных ID, загруженных из фильтра.    |
| `bioetl_filter_ids_duplicates_total`      | Counter | `pipeline`, `source_kind` | Количество дубликатов, найденных в фильтре.          |
| `bioetl_filter_combinations_loaded_total` | Counter | `pipeline`, `source_kind` | Количество загруженных комбинаций из мульти-фильтра. |

### 5.3 Data Quality Metrics

| Метрика                                 | Тип       | Labels                                                      | Описание                                                                                                                     |
| --------------------------------------- | --------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `bioetl_dq_records_quarantined_total`   | Counter   | `pipeline`, `error_type`, `run_type`                        | Количество записей, отправленных на карантин из-за проблем качества.                                                         |
| `bioetl_dq_validation_score`            | Gauge     | `pipeline`, `entity`                                        | Entity-level оценка качества данных (0.0-1.0, где 1.0 = все записи валидны).                                                 |
| `bioetl_dq_validation_record_count`     | Gauge     | `pipeline`, `entity`                                        | Record count для последнего entity-level DQ snapshot; используется для volume-weighted aggregate score.                      |
| `bioetl_data_freshness_seconds`         | Gauge     | `pipeline`, `entity`                                        | Unix timestamp последнего успешного ingestion для pipeline/entity; lag считается как `time() - metric`.                      |
| `bioetl_dq_anomaly_detected`            | Counter   | `pipeline`, `metric`, `severity`, `anomaly_type`            | Количество обнаруженных аномалий качества данных.                                                                            |
| `bioetl_dq_check_duration_ms`           | Histogram | `pipeline`                                                  | Длительность проверок качества данных в миллисекундах.                                                                       |
| `bioetl_dq_baseline_updated`            | Counter   | `pipeline`, `metric`                                        | Количество обновлений baseline для DQ монитора.                                                                              |
| `bioetl_dq_baseline_samples`            | Gauge     | `pipeline`, `metric`                                        | Текущее количество samples в baseline DQ.                                                                                    |
| `bioetl_dq_soft_threshold_exceeded`     | Counter   | `pipeline`                                                  | Количество превышений мягкого порога DQ.                                                                                     |
| `bioetl_silver_filter_rejections_total` | Counter   | `pipeline`, `run_type`, `reason_code`, `rule_type`, `field` | Bounded operator summary для Silver rejects по structured labels; raw `message` и unconstrained field text сюда не попадают. |

### 5.4 Circuit Breaker Metrics

| Метрика                                | Тип     | Labels    | Описание                                                                                         |
| -------------------------------------- | ------- | --------- | ------------------------------------------------------------------------------------------------ |
| `bioetl_circuit_breaker_state`         | Gauge   | `adapter` | Текущее состояние circuit breaker: 0=closed (здоров), 1=half-open (проверка), 2=open (отключён). |
| `bioetl_circuit_breaker_trips_total`   | Counter | `adapter` | Количество срабатываний (переходов в open).                                                      |
| `bioetl_circuit_breaker_success_total` | Counter | `adapter` | Количество успешных вызовов через circuit breaker.                                               |
| `bioetl_circuit_breaker_failure_total` | Counter | `adapter` | Количество неуспешных вызовов через circuit breaker.                                             |

### 5.5 Health Check Metrics

| Метрика                                | Тип       | Labels                  | Описание                                                               |
| -------------------------------------- | --------- | ----------------------- | ---------------------------------------------------------------------- |
| `bioetl_pipeline_health_check_passed`  | Gauge     | `pipeline`, `component` | Статус health check компонента (1=passed, 0=failed).                   |
| `bioetl_infrastructure_validated`      | Gauge     | `pipeline`              | Статус валидации инфраструктуры (1=validated, 0=not).                  |
| `bioetl_health_check_duration_seconds` | Histogram | `pipeline`              | Длительность health check операций в секундах.                         |
| `bioetl_health_check_status`           | Gauge     | `component`             | Статус здоровья компонента: 0=unknown, 1=healthy, 2=degraded.          |
| `bioetl_health_check_latency_seconds`  | Histogram | `provider`              | Латентность health check в секундах.                                   |
| `bioetl_health_check_success_total`    | Counter   | `provider`              | Количество health check с результатом `HEALTHY`.                       |
| `bioetl_health_check_degraded_total`   | Counter   | `provider`              | Количество health check с результатом `DEGRADED`.                      |
| `bioetl_health_check_failures_total`   | Counter   | `provider`              | Количество health check с результатом `UNHEALTHY` или probe-exception. |

### 5.6 Adapter / HTTP Metrics

| Метрика                                    | Тип       | Labels                             | Описание                                                          |
| ------------------------------------------ | --------- | ---------------------------------- | ----------------------------------------------------------------- |
| `bioetl_adapter_request_duration_seconds`  | Histogram | `provider`, `endpoint`             | Длительность API-запросов адаптера в секундах. Buckets: 0.05-30s. |
| `bioetl_adapter_requests_total`            | Counter   | `provider`, `endpoint`, `status`   | Количество API-запросов адаптера.                                 |
| `bioetl_adapter_batch_size`                | Histogram | `provider`, `endpoint`             | Распределение размеров ответов адаптера.                          |
| `bioetl_adapter_dropped_duplicates_total`  | Counter   | `provider`, `entity_type`          | Количество дубликатов, удалённых адаптером.                       |
| `bioetl_data_source_retries_total`         | Counter   | `provider`, `operation`            | Количество retry-попыток для data source.                         |
| `bioetl_data_source_retry_exhausted_total` | Counter   | `provider`, `operation`            | Количество исчерпанных retry-попыток.                             |
| `bioetl_http_request_duration_seconds`     | Histogram | `provider`, `method`, `status`     | Длительность HTTP-запросов в секундах.                            |
| `bioetl_http_retries_total`                | Counter   | `provider`, `method`               | Количество HTTP retry-попыток.                                    |
| `bioetl_http_request_errors_total`         | Counter   | `provider`, `method`, `error_type` | Количество HTTP-ошибок.                                           |
| `bioetl_provider_health_status`            | Gauge     | `provider`                         | Статус здоровья провайдера: 0=unhealthy, 1=degraded, 2=healthy.   |
| `bioetl_rate_limiter_tokens_available`     | Gauge     | `provider`                         | Текущее количество доступных токенов в rate limiter.              |
| `bioetl_rate_limiter_wait_seconds`         | Histogram | `provider`                         | Время ожидания в rate limiter.                                    |

### 5.7 Transformer Metrics

| Метрика                             | Тип       | Labels                                  | Описание                                      |
| ----------------------------------- | --------- | --------------------------------------- | --------------------------------------------- |
| `bioetl_transform_duration_seconds` | Histogram | `provider`, `entity_type`               | Длительность трансформации данных в секундах. |
| `bioetl_transform_errors_total`     | Counter   | `provider`, `entity_type`, `error_type` | Количество ошибок трансформации.              |

### 5.8 Storage Metrics

| Метрика                                   | Тип       | Labels               | Описание                                           |
| ----------------------------------------- | --------- | -------------------- | -------------------------------------------------- |
| `bioetl_vacuum_files_removed_total`       | Counter   | `table`, `layer`     | Количество файлов, удалённых vacuum-операциями.    |
| `bioetl_storage_optimization_total`       | Counter   | `pipeline`, `status` | Количество операций оптимизации хранилища.         |
| `bioetl_bronze_write_duration_seconds`    | Histogram | `provider`, `entity` | Длительность записи в Bronze-слой.                 |
| `bioetl_bronze_records_written_total`     | Counter   | `provider`, `entity` | Количество записей, записанных в Bronze.           |
| `bioetl_bronze_bytes_written_total`       | Counter   | `provider`, `entity` | Количество байт, записанных в Bronze (compressed). |
| `bioetl_policy_violations_total`          | Counter   | `layer`, `mode`      | Количество нарушений write policy.                 |
| `bioetl_silver_validation_failures_total` | Counter   | `table`, `pipeline`  | Количество ошибок валидации Silver schema.         |

### 5.9 Shutdown Metrics

| Метрика                     | Тип     | Labels   | Описание                         |
| --------------------------- | ------- | -------- | -------------------------------- |
| `bioetl_shutdown_initiated` | Counter | `reason` | Количество инициаций завершения. |
| `bioetl_shutdown_completed` | Counter | `reason` | Количество завершённых shutdown. |

______________________________________________________________________

## 6. Переменные фильтрации (Template Variables)

Primary dashboards `0..5` используют общий operator context shell:
`$workflow`, `$pipeline`, `$run_type`, `$run_id`. Role-specific variables
(`$stage`, `$provider`, `$status`, `$step_status`, `$step_kind`,
`$pipeline_context`, `$adapter`) добавляются поверх shell. Переменные
отображаются как выпадающие списки в верхней части дашборда.

Navigation: all seven shipped
dashboards render the same theme-safe bus `0..6`, followed by `Silver Reject
bus `0..6` only. The current item is visibly
disabled, links wrap at `1024px`, and no dashboard has an omission exception.

`$run_id` в primary dashboards остаётся HTTP-backed local identity selector
для панели `ID`; он не используется в Prometheus label filtering и не
становится Prometheus-backed cross-dashboard filter. Между primary dashboards
он передаётся как exact HTTP identity context.
Его option list строится через `/ops/control-plane/filter-options` с текущими
`workflow/pipeline/run_type`, а coherent tuple для будущей selector-shell
интеграции отдаёт `/ops/control-plane/selector-context`. Native Grafana
variables не умеют безопасно auto-write sibling selectors без custom shell.
Dashboard-to-dashboard links поэтому явно передают общий shell
`workflow/pipeline/run_type`, preserved identity `run_id` для primary targets
и target-specific bounded vars через `var-*`, без `includeVars=true`.
`bioetl-workflow-overview` дополнительно использует hidden exact-run handoff
vars (`$workflow_context`, `$pipeline_context_exact`, `$run_type_context_exact`,
`$provider_context_exact`) через
`/ops/control-plane/filter-options?exact_run_only=1`, чтобы selected `run_id`
мог сузить downstream handoff без переписывания видимых sibling selectors.
Для local-only pilot rollout repo also ships an optional unsigned panel plugin
under `grafana/plugins/bioetl-selectorshell-panel`; it can call
`/ops/control-plane/selector-context` and write visible sibling selectors as one
transaction, but shipped dashboard JSON does not depend on that plugin by
default.

### 6.0 Shared context shell

| Variable | Primary dashboards | Source | Semantics |
| --- | --- | --- | --- |
| `$workflow` | `0..6` | `label_values(bioetl_workflow_universe, workflow)` for query-backed dashboards; Alerts uses a textbox. | Context/evidence unless a panel documents truthful current-status intersection. The universe includes terminal workflow outcomes and started workflows published through `bioetl_workflow_expected`. |
| `$pipeline` | `0..6` | Dashboard-bounded Prometheus universe: Overview/DQ/Provider/Workflow/Alerts use `bioetl_overview_pipeline_run_type_universe`; Runtime uses `bioetl_runtime_pipeline_run_type_universe`; Control Plane uses `bioetl_control_plane_run_type_universe`. | Canonical pipeline context; Overview may default to `All`, non-Overview dashboards fail-close to `unknown`. Planned workflow child pipelines appear after `bioetl_workflow_pipeline_expected` is published. |
| `$run_type` | `0..6` | Same bounded universe as `$pipeline` for the dashboard role. | Multi-select Include All. Overview default `All`; other boards default `backfill`. Never `unknown`. |
| `$run_id` | `0..6` | BioETL Ops HTTP `/ops/control-plane/filter-options?dimension=run_id...&workflow=${workflow}&pipeline=${pipeline}&run_type=${run_type:csv}` | Preserved HTTP identity context for `ID`/details panels; no Include All; default `-`; options start-time desc (`sort=0`); never a Prometheus label. |

`$workflow` stays single-select with Include All across primary dashboards,
including `bioetl-workflow-overview`, so one coherent workflow shell value is
preserved during handoff while aggregate `All` scope remains available.

Common context panels on primary dashboards outside Overview:

| Panel | ID | Contract |
| --- | ---:| --- |
| `Inspect Scope & Evidence` | `9400` | Visible operator question plus plain-language evidence-scope definitions; selector details stay in the panel tooltip/description. |
| `Status` | `9401` | Role-specific compact status; no Prometheus `$run_id` filtering. |
| `ID` | `9402` | BioETL Ops HTTP identity table for `pipeline/run_type/run_id`. |
| `Processed Records` | `9403` | Current Bronze -> Silver -> Gold accounting table from `/ops/observability/processed-records`; exact `$run_id` scopes resolve from RunLedger evidence, while aggregate scopes use `bioetl_processed_records_*` recording rules. `Inspect Processed Records` displays `parameter` and `value` only; `Review Processed Records` also displays `percentage`. Zero-valued outcome rows remain visible and missing accounting series are UNKNOWN/no-data, not OK. |
| `Identity Data Unavailable` | `9410` | Control Plane-only neutral fallback text shown below the identity table when the selected scope returns no visible rows. |
| `Record Counts Unavailable` | `9411` | Control Plane-only neutral fallback text shown below the accounting table when the selected scope returns no visible rows. |

All seven shipped dashboards enforce one question/scope/evidence readability contract based
on `4. Data Quality`: orange `4px` accent, `16px` body (12 pt equivalent),
`18px` operator question (13.5 pt equivalent), `line-height:1.35`, normal
wrapping, and a four-grid-row first-screen panel. Run Explorer preserves
stable panel `id=1` as `Inspect Run Selection & Evidence`. Selector values remain in
Grafana controls and panel descriptions instead of expanding into
clipping-prone on-canvas strings.

`0. Control Plane` adds Control Plane-only identity evidence panels outside the
shared shell. Panels `9404..9409` call
`/ops/control-plane/identity-evidence` for overview anchors, P1/P2 evidence,
identity gaps, checkpoint anchor compare, and copy-friendly full-value
handoffs. Each row exposes `source_type`, `source_quality`, `drilldown_type`,
and `drilldown_target` so Grafana can route to manifest, ledger, effective
config, contract, snapshot, checkpoint, lineage, and artifact evidence. This
endpoint is the approved surface for `run_id`, `manifest_id`,
execution/config/contract hashes, input snapshot IDs, replay parentage,
composite identity, lineage, and artifact refs; none of those values may be
added as Prometheus labels.

The local health server resolves `/ops/observability/processed-records` from
RunLedger when an exact `run_id` is provided. Without exact `run_id`, it falls
back to Prometheus via `BIOETL_PROMETHEUS_URL` when set. Without an explicit
setting it tries `http://localhost:9090`, then the Docker-local fallbacks
`http://prometheus:9090` and `http://host.docker.internal:9090`.
For detached dashboard audits this is a backend reachability contract, not a
Grafana datasource contract: set `BIOETL_PROMETHEUS_URL` to the Prometheus URL
reachable by the `bioetl quarantine serve` process that owns HTTP panels such
as `ID`, `Processed Records`, and checkpoint freshness. In mixed Docker plus
host/WSL setups, prefer an explicit value over assuming `localhost:9090`.

### 6.1 `$pipeline`

- **Определение:** dashboard-bounded query family. Overview/DQ/Provider/Workflow/Alerts
  use `bioetl_overview_pipeline_run_type_universe`; Runtime uses
  `bioetl_runtime_pipeline_run_type_universe`; Control Plane uses
  `bioetl_control_plane_run_type_universe`.
- **Тип:** Query (автоматическое обнаружение значений)
- **Multi-select:** Нет
- **Include All:** Да только для `bioetl-overview-v2`/snapshot Overview; в
  остальных primary dashboards остаётся fail-closed single-select policy.
- **Default:** для `bioetl-overview-v2` используется `All`, чтобы landing page
  показывал актуальный L0 state без пустого `unknown` scope. Для остальных
  pipeline-centric dashboards default остаётся `unknown`, если исходный
  dashboard не имеет pipeline context.
- **Refresh:** При загрузке дашборда
- **Возможные значения:** `chembl`, `pubmed`, `pubchem`, `uniprot` и другие pipeline-идентификаторы, зарегистрированные в системе.
- **Применение:** Фильтрует метрики по имени пайплайна. Используется практически во всех PromQL-запросах.

### 6.2 `$run_type`

- **Определение:** same dashboard-bounded query family as `$pipeline`, filtered
  by selected `$pipeline`.
- **Тип:** Query (каскадная зависимость от `$pipeline`)
- **Multi-select:** Да
- **Include All:** Да
- **Default:** `All`. Cross-dashboard links MUST NOT pass `run_type=unknown`;
  missing run-type context is represented as `Run Type=All`.
- **Refresh:** При загрузке дашборда
- **Возможные значения:**
  - `incremental` — инкрементальное обновление данных (только новые записи).
  - `backfill` — ретроспективное заполнение данных за прошлые периоды.
  - `rebuild` — полная пересборка данных с нуля.
- **Применение:** Фильтрует метрики по типу запуска. Доступен только на метриках, имеющих label `run_type` (основные pipeline-метрики).

- **`$stage`** (`bioetl-dq-v2`, `bioetl-runtime`):
  `label_values(bioetl_records_processed_total{pipeline=~"$pipeline",run_type=~"$run_type"}, stage)`.
  Для `bioetl-runtime` stage values приходят из
  `bioetl_pipeline_stage_expected{pipeline=~"$pipeline"}`, чтобы expected-stage
  diagnostics оставались доступны даже до record emission. Это bounded stage
  breakdown filter, а не forensic selector.

- **`0. Control Plane`** uses the shared context shell and adds
  control-plane-specific trust panels for manifest/ledger/checkpoint/replay/lineage.
  `Review First Recovery Action` occupies the rightmost shared-shell slot
  beside `ID` and `Processed Records`, while the four compact trust cards remain
  directly below the shared context shell.
  Headline `Status` reads `bioetl_control_plane_current_status_trusted`:
  `0=OK`, `1=WARN`, `2=CRIT`, `3=INCOMPLETE`, `null=UNKNOWN`. Replay/resume
  approval requires complete replay-safety, checkpoint freshness/presence, and
  required telemetry evidence; `Monitor Telemetry Coverage` must be `0`.
  `Review Terminal Run Outcomes`
  stays below fold as selected-range terminal ledger evidence, while exact `run_id` /
  `manifest_id`, config/contract hashes, artifact refs, replay parentage,
  composite identity, and checkpoint anchor compare are surfaced by
  `/ops/control-plane/identity-evidence` plus run-manifest inspection, not
  Prometheus labels. `Monitor Checkpoint Age` is also now
  HTTP-backed through `/ops/control-plane/checkpoint-freshness`, so it reads
  persisted checkpoint metadata instead of relying on short-lived scrape
  presence. When that endpoint returns `status=UNKNOWN` with `age_seconds=null`,
  the panel is behaving as designed: the stack has no persisted checkpoint
  evidence for the selected scope yet, which is a no-evidence state rather than
  a broken datasource. For exact run
  `b51986c6-870b-4457-aa70-baedac2710ad`, local evidence includes manifest
  `3c803630-4652-40d0-8f8d-f26b2fb1bdd9`, terminal success ledger evidence,
  and immutable checkpoint history under
  `data/output/checkpoints/.history/by_manifest/3c803630-4652-40d0-8f8d-f26b2fb1bdd9.json`;
  current panel `892` is therefore classified as checkpoint evidence present,
  not `Expected Empty` and not a current product defect. Future audits should
  classify an exact-run checkpoint gap as `Expected Empty` only when both the
  run manifest/ledger exist and immutable checkpoint history is absent for that
  run; if checkpoint history exists and panel `892` still returns
  `UNKNOWN`/`MISSING`, classify it as a product defect in the checkpoint
  freshness read path. GLOBAL
  read-path и checkpoint-operator panels не несут pipeline/run_type labels,
  поэтому не фильтруются по этим переменным.

- **`1. Overview`** uses the frozen Overview v3 baseline and remains
  Prometheus-first для L0 current-status panels, но exact `run_id` selector
  теперь берётся через HTTP helper
  `/ops/control-plane/filter-options` из persisted run-manifest catalog,
  scoped by current `$pipeline/$run_type`. Grafana `All` values нормализуются
  в unbounded control-plane scope, поэтому `Run Type=All` не должен quietly
  опустошать selector. Это control-plane-backed selector, а не Prometheus
  label, поэтому high-cardinality `run_id` не возвращается в metric surface.
  Panel `ID` в этом dashboard теперь также использует control-plane HTTP
  helper и показывает компактный двухколоночный identity summary: `Run ID`,
  `Manifest ID`, `Provider.Entity`, `Contract`, `Execution`, replay capability
  and mode, checkpoint anchors, optional composite run identity, and identity
  health. Exact selected `run_id` wins, concrete pipeline scope may fall back to
  the latest persisted manifest, aggregate `Pipeline=All` scope without exact
  `run_id` must not guess one manifest identity.

- **`5. Workflow`** exposes the shared context shell plus `$status` через
  `label_values(bioetl_workflow_runs_total, status)`, а также `$step_status` и
  `$step_kind` через `bioetl_workflow_step_events_total`. `First Action`
  now occupies the rightmost shared-shell slot beside `ID` and `Processed Records`
  and also carries the selected-range-only interpretation contract for this
  dashboard after the removal of the separate `Workflow Scope` banner.
  `$workflow` remains single-select with Include All here as well; workflow
  evidence can aggregate to `All`, but operator handoff still preserves one
  exact workflow shell value whenever a concrete workflow is selected.
  Shipped workflow panels aggregate per-run published series with
  `max_over_time(...)`, because workflow jobs are short-lived and must remain
  queryable after the CLI process exits. `$pipeline/$run_type/$run_id` are
  context/identity aids unless a panel documents truthful intersection
  semantics.

- **`Provider Health`** exposes the shared context shell plus single-select
  `$provider`, hidden `$pipeline_context` и hidden detail-only `$adapter`.
  `$provider` remains the current-status selector. Переходы из pipeline-scoped dashboards
  сохраняют `$pipeline_context=$pipeline` и fail-close'ятся к
  `$provider=unknown`, если source dashboard не может доказать валидный
  provider value; при обратном переходе `$pipeline_context` восстанавливает
  исходный pipeline. Если source dashboard не имеет adapter context, handoff не
  передаёт `adapter`, и target dashboard сам раскрывает fallback `All adapters`.

**Каскадная зависимость:** Значения `$run_type` зависят от выбранного `$pipeline`. При смене пайплайна список доступных run types автоматически обновляется.

Canonical unified variable reference: `docs/03-guides/dashboards/variable-reference.md`.
Canonical selector taxonomy and shipped selector registry:
`docs/03-guides/dashboards/contracts/selector-contracts.yaml`.
Narrative selector architecture:
`docs/03-guides/dashboards/selector-architecture.md`.

**Какие метрики поддерживают `run_type`:**

- `bioetl_records_processed_total` (pipeline, stage, **run_type**)
- `bioetl_pipeline_duration_seconds` (pipeline, stage, status, **run_type**)
- `bioetl_dq_records_quarantined_total` (pipeline, error_type, **run_type**)
- `bioetl_pipeline_runs_total` (pipeline, **run_type**, status)

**Какие метрики НЕ поддерживают `run_type`:**

- `bioetl_errors_total` — фильтруется только по `pipeline`
- `bioetl_batch_size_records` — фильтруется только по `pipeline`
- `bioetl_data_freshness_seconds` — фильтруется только по `pipeline`
- `bioetl_filter_ids_*` — фильтруется только по `pipeline`
- `bioetl_adapter_request_duration_seconds` — фильтруется по `provider`
- `bioetl_http_request_errors_total` — фильтруется по `provider`

## 8. Архивная заметка: legacy v1 dashboard surfaces

v1 dashboards (`bioetl-overview.json`, `bioetl-dq.json`, `bioetl-provider-health.json`)
сохраняются только как historical reference для сравнения evolution surface и старых
скриншотов/обсуждений. Они не считаются operator entrypoints и не входят в текущий
shipped pack. Active operator routing starts at
`docs/03-guides/dashboards/monitoring-index.md`; JSON truth for shipped panels is
`grafana/dashboards/*.json`.

______________________________________________________________________

## 9. Дашборд: 1. Overview

**Файл:** `grafana/dashboards/bioetl-overview-v2.json`
**UID:** `bioetl-overview-v2`
**Refresh:** 30 секунд
**Time range:** Последние 12 часов
**Назначение:** L0 answer-first surface using the frozen Overview v3 baseline. Primary question: what is currently broken or degraded in BioETL, and where should the operator drill down first?

### Панели

| ID  | Название                       | Тип        | PromQL                                                                                                                       | Описание                                                                                                                                                                         |
| --- | ------------------------------ | ---------- | ---------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 99  | Inspect Scope & Evidence       | Text       | n/a                                                                                                                          | Primary question and plain-language definitions for current, selected-run, time-range, and unknown evidence.                                                                    |
| 214 | Status                         | Stat       | `max(bioetl_l0_status{pipeline=~"$pipeline",run_type=~"$run_type"})`                                                         | `UNKNOWN`/`OK`/`WARN`/`CRIT`; null/no-series remain `UNKNOWN` via explicit null mapping. Panel-level links duplicate the canonical Runtime / Control Plane / Data Quality / Provider Health / Workflow handoff. |
| 215 | Review First Action           | Table      | `topk(4, bioetl_l0_next_action_route{pipeline=~"$pipeline",run_type=~"$run_type"} or NO_ROUTE label_replace(vector(0)…))` | Up to four urgency-ordered routes; columns Action (primary color-text CTA, short labels, row link via `action_dashboard_uid`) → Priority (short badge `RUNTIME`/`CP`/… with color-background) → Why → Pipeline. Missing scope → `NR`/`NO_ROUTE`. Ladder: Runtime > Control Plane > Gold Lifecycle > DQ > Provider > Workflow > Monitor. Secondary panel links: Runtime / Control Plane / DQ / Provider (provider fail-closes `provider=unknown` + `pipeline_context`). |
| 9300 | ID                            | Table      | HTTP `/ops/control-plane/identity-table?...&run_id=${run_id}`                                                                | Compact two-column identity summary: run/manifest IDs, Provider.Entity version, contract schema, execution flags, replay capability/mode, checkpoint anchors, optional composite run, and identity health. Exact selected `run_id` wins; no Prometheus `run_id`. |
| 9301 | Processed Records             | Table      | HTTP `/ops/observability/processed-records?pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}`                                  | Current compact Bronze/Silver/Gold accounting evidence. Exact `run_id` scopes read RunLedger artifact/metrics evidence; aggregate scopes use recording rules. Shows all configured rows, including zero values, with space-grouped, left-padded, right-aligned `value` plus canonical formatted `percentage`; internal `row_status` is hidden, and reconciliation status, subtotal, and delta rows stay out of the compact table; no `$__range` and no Prometheus `run_id`. |
| 9002 | Inputs                        | Table      | `max by (input) (bioetl_l0_input_status_selected{pipeline=~"$pipeline",run_type=~"$run_type"})`                              | Compact L0 input summary: one worst-status row per operator input so the first screen fits without scroll while preserving selected-scope UNKNOWN rows.                       |
| 9003 | Runtime                       | Table      | `max by (pipeline) (bioetl_l1_runtime_blocker_status{pipeline=~"$pipeline",run_type=~"$run_type"})`                         | Compact current runtime blocker summary: worst current status per pipeline across the selected run-type scope.                                                                  |
| 9004 | Data Quality                  | Table      | `max by (pipeline) (bioetl_l1_dq_status{pipeline=~"$pipeline",run_type=~"$run_type"})`                                      | Compact selected-scope DQ summary: worst current status per pipeline across the selected run-type scope.                                                                        |
| 9005 | Data Validation               | Table      | `max by (pipeline) (bioetl_l1_gold_lifecycle_status{pipeline=~"$pipeline",run_type=~"$run_type"})`                           | Compact current data-validation lifecycle summary: worst current lifecycle status per pipeline across the selected run-type scope. Exact lifecycle-state detail remains in deeper surfaces; contract-excluded Gold records are terminal OK evidence, not missing Gold. |
| 9006 | Control Plane                 | Table      | `max by (pipeline) (bioetl_l1_control_plane_current_status{pipeline=~"$pipeline",run_type=~"$run_type"})`                   | Compact current control-plane summary: worst current status per pipeline across the selected run-type scope.                                                                    |
| 9007 | Provider                      | Table      | `bioetl_l1_provider_global_status`                                                                                            | Global provider health across pipelines; intentionally not filtered by `$pipeline/$run_type`.                                                                                   |
| 9013 | Workflow                      | Table      | `max by (pipeline) (bioetl_l1_workflow_global_status{pipeline=~"$pipeline",pipeline!="test_pipe"} or ... alias-normalized fallback ...)` | Compact selected workflow/pipeline summary: worst current workflow status per matching pipeline without unrelated pipeline leakage. Backed by the latest bounded terminal workflow signal, not cumulative workflow counters; `run_type`/`run_id` stay handoff context only. |
| 9018 | Runtime Blockers Trend        | Timeseries | `bioetl_l1_runtime_blocker_status{pipeline=~"$pipeline",run_type=~"$run_type"}`                                              | Selected-range L1 runtime evidence below the current verdict path; does not determine L0 `Status` or `Next Action`; no-data/gaps are diagnostic; handoff `Open Runtime`.         |
| 9019 | DQ Status Trend               | State timeline | `bioetl_l1_dq_status{pipeline=~"$pipeline",run_type=~"$run_type"}`                                                         | Selected-range L1 Data Quality evidence below the current verdict path; renders discrete OK/WARN/CRIT/UNKNOWN states instead of numeric ticks; does not determine L0 `Status` or `Next Action`; no-data/gaps are diagnostic; handoff `Open Data Quality`. |
| 9020 | Gold Lifecycle Trend          | Timeseries | `bioetl_l1_gold_lifecycle_status{pipeline=~"$pipeline",run_type=~"$run_type"}`                                                | Selected-range L1 data-validation lifecycle evidence below the current verdict path; includes `lifecycle_state`, including `terminal_contract_excluded` for Gold records excluded by contract; handoffs `Open Runtime` and `Open Control Plane`. |
| 9010 | Historical Failures | Table | `sum by (pipeline, run_type) (increase(bioetl_pipeline_runs_total{status="failed",...}[$__range]))`                         | Selected-range historical failure evidence only; zero matching rows is not proof of current OK; handoff `Open Runtime`.                                                          |
| 9011 | Recent Terminal Runs | Table | `sum by (pipeline, status) (increase(bioetl_pipeline_runs_total{status!="success",...}[$__range]))`                          | Selected-range non-success terminal-run evidence only; no terminal rows is not proof of current OK; handoffs `Open Control Plane` and `Open Runtime`.                            |
| 9012/9021 | Diagnostics & Docs (Logs / Traces / Raw Metrics) / Diagnostics Navigation | Row/Text | n/a                                                                                                       | Collapsed diagnostics row is populated again with raw-metric routing guidance and dashboard navigation pointers.                                                                |
| 9600/9601 | Alert/SLO Triage / Triage Alert State | Row/Table | `ALERTS{alertstate=~"firing|pending"}` | Collapsed immediately after the bounded first path; expands to show Prometheus `ALERTS` firing/pending state without reimplementing alert rules in dashboard queries. |

**Используемые метрики:** `bioetl_pipeline_runs_total`, `bioetl_records_processed_total`,
`bioetl_stage_backlog_records`, `bioetl_stage_lag_seconds`,
`bioetl_dq_validation_failures_total`, `bioetl_dq_records_quarantined_total`,
control-plane metrics, provider health metrics и `bioetl_workflow_runs_total`.

**Drilldown (live bus 0–6):** Trust/Control Plane → Overview → Runtime →
Provider → DQ → Incident → Run Explorer. Navigation panel `id=1000` is the
shipped bus; do not reintroduce Workflow/Alerts/Silver/Loki/Tempo Explore as
portfolio boards. Panel `dataLinks` and runbook CTAs are authoritative in JSON
under `grafana/dashboards/`.

**Silver Rejects triage (post-Explorer removal):**

1. Start on Overview or Runtime for reject-rate signals.
1. Use Data Quality for bounded Pareto/field breakdowns.
1. Record-level forensics: `bioetl quarantine inspect --pipeline ...`
   (resolve/replay via CLI, not a dedicated Explorer dashboard).

______________________________________________________________________

## 11. Дашборд: 4. Data Quality

**Файл:** `grafana/dashboards/bioetl-dq-v2.json`
**UID:** `bioetl-dq-v2`
**Refresh:** 30 секунд
**Time range:** Последние 12 часов
**Назначение:** L2 Data Quality incident dashboard. Первый экран отвечает:
DQ сейчас `OK`/`WARN`/`CRIT`/`UNKNOWN`, какая threshold/reason state
активна и какое первое действие выполнить; selected-range flow/score/quarantine
панели являются evidence ниже first screen.

**Фильтрация:** shared context shell `$workflow/$pipeline/$run_type/$run_id`
plus `$stage`. `run_id` feeds only the local `ID` panel; current DQ status does
not use it as a Prometheus label.

### Панели

| ID  | Название                                     | Тип        | PromQL                                                                                                                                 | Описание                                                                                                                                                                   |
| --- | -------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 9100 | Monitor DQ Current Status                   | Stat       | `max(bioetl_dq_current_status{pipeline=~"$pipeline"})`                                                                                | Pipeline-wide current DQ state: `0=OK`, `1=WARN`, `2=CRIT`, `null=UNKNOWN`; disabled/noop DQ monitoring contributes WARN rather than unconditional green. Selected-range evidence ниже не меняет этот first-screen статус. |
| 9101 | Now · DQ Threshold State                  | Stat       | `max(bioetl_dq_current_reason{severity=...})` + explicit `OK` fallback                                                                | Bounded current threshold summary: warning reasons map to WARN, hard reasons map to CRIT, explicit current OK stays `0=OK`.                                                |
| 9102 | Now · DQ Current Reasons                  | Table      | `topk(5, bioetl_dq_current_reason{pipeline=~"$pipeline"} > 0)`                                                                        | Current DQ reasons table with `severity` and `action_target`; `CRIT` can come from quarantine/validation blockers even when `filtered_out=0`.                             |
| 9103 | Review: First Action                         | Text      | n/a                                                                                                                                    | CTA block sits in the same shared-shell row as `ID` and `Processed Records` (`w=8`, `h=10`). Review current status and reasons first; if `filtered_out=0`, inspect quarantine, validation failures, and blocked records before assuming reject-path only. |
| 1   | Track Range Evidence: Bronze -> Silver -> Gold | Timeseries | `sum by (pipeline, stage) (max_over_time(bioetl_records_processed_total{pipeline=~"$pipeline", run_type=~"$run_type"}[$__interval]))` | Full-width selected-range evidence panel that now sits below the compact current-context band; не определяет current DQ status.                                            |
| 2   | Monitor: Data Quality Score (Volume-weighted) | Stat      | `sum(last_over_time(score[7d]) * last_over_time(record_count[7d])) / clamp_min(sum(last_over_time(record_count[7d])), 1)`                 | Latest retained seven-day DQ snapshot на базе `bioetl_dq_validation_score` и `bioetl_dq_validation_record_count`; без retained samples остаётся `UNKNOWN`, а не ложным `0`.   |
| 3   | Track: Source Records in Range (Bronze)      | Stat       | `round(sum(max_over_time(bioetl_records_processed_total{...stage="bronze"}[$__range])) or vector(0))`                                  | Суммарный Bronze input для pushed-counter evidence внутри активного Grafana окна; это bounded range evidence, а не latest-value snapshot.                                   |
| 4   | Track: Clean Records in Range (Gold)         | Stat       | `round(sum(max_over_time(bioetl_records_processed_total{...stage="gold"}[$__range])) or vector(0))`                                    | Суммарный Gold output для pushed-counter evidence внутри активного Grafana окна; это bounded range evidence, а не latest-value snapshot.                                    |
| 5   | Monitor: Worst-Entity DQ Score               | Stat      | `min(last_over_time(bioetl_dq_validation_score{pipeline=~"$pipeline"}[7d]))`                                                           | Худший latest-retained DQ score за семь дней. При отсутствии samples panel remains `UNKNOWN`, not synthetic `0`. |
| 8   | Time Range · Worst Freshness Age (hours; SLA 24/72) | Gauge | `max(clamp_min(time() - max_over_time(bioetl_data_freshness_seconds{pipeline=~"$pipeline"}[$__range]), 0)) / 3600` | TIME RANGE freshness age in hours; WARN `>=24h`, CRIT `>=72h`, null `UNKNOWN`. Query, unit, title, and thresholds use hours. |
| 6   | Range · Records Quarantined          | Stat       | `round(sum(max_over_time(bioetl_dq_records_quarantined_total{...}[$__range])) or vector(0))`                                           | Selected-range quarantine evidence; non-zero here can explain current DQ pressure even when Silver structural rejects remain zero.                                           |
| 7   | Track: Silver Validation Failures in Range   | Stat       | `round(sum(max_over_time(bioetl_silver_validation_failures_total{pipeline=~"$pipeline", run_type=~"$run_type"}[$__range])) or vector(0))` | Visible selected-range validation blocker count; non-zero can drive current `CRIT` even when `filtered_out=0`.                                                               |
| 117 | Range · Silver Filter Rejects        | Stat       | `round(sum(max_over_time(bioetl_records_processed_total{...stage="filtered_out"}[$__range])) or vector(0))`                             | Отдельный счётчик Silver structural rejects внутри выбранного временного окна; не заменяет `Range · Records Quarantined` или Gold reject panels.                    |
| 118 | Inspect: Silver Filter Rejects by Pipeline   | Bar gauge  | `sum by (pipeline) (max_over_time(bioetl_records_processed_total{...stage="filtered_out"}[$__range]))`                                  | Scope/distribution panel over the stage-total `filtered_out` counter. Explorer handoff preserves only `pipeline`/`run_type`; it does not synthesize a `reason_code`. No data remains an honest empty-state, not a fake `pipeline=no_events` row. |
| 156 | Inspect: Gold Reject Outcomes by Pipeline    | Bar gauge  | `bioetl_processed_records_gold_quarantined_current` + `bioetl_processed_records_gold_excluded_by_contract_current` over `$__range`       | Separate Gold contract/semantic reject surface. It does not read `FILTERED_OUT_SILVER` and does not use CLI silver-filter-only path.                                      |
| 121 | Inspect: Top Silver Reject Reasons (Pareto) | Bar gauge  | `topk(10, sum by (reason_code) (increase(bioetl_silver_filter_rejections_total{...}[$__range])))`                                      | Bounded top-10 summary по `reason_code`; each bar is aggregate-only; use CLI `bioetl quarantine inspect` scoped by `pipeline`/`run_type`/`reason_code`. No data remains empty-state instead of a synthetic `reason_code=none` bucket. |
| 122 | Inspect: Top Silver Reject Fields            | Bar gauge  | `topk(10, sum by (field) (increase(bioetl_silver_filter_rejections_total{...}[$__range])))`                                            | Bounded top-10 summary по `field`; each bar is aggregate-only; use CLI `bioetl quarantine inspect` scoped by `pipeline`/`run_type`/`field`. No data remains empty-state instead of a synthetic `field=none` bucket. |
| 152 | Monitor: Silver Filter Reject Accounting Mismatch | Stat  | `round(sum(max_over_time(bioetl_silver_filter_reject_total_mismatch_15m{...}[$__range])))`                                              | Reconciliation guard между stage-total `filtered_out` surface и bounded breakdown metric. `0` = healthy, non-zero = расследовать drift, `No data` = recording rule не публикуется. |
| 9   | Inspect: Quarantine by Error Type            | Bar gauge  | `sum by (error_type) (max_over_time(bioetl_dq_records_quarantined_total{...}[$__range]))`                                              | Horizontal category-comparison surface for quarantine triage. Shipped as `bargauge`, not `piechart`, because operator comparison of error families matters more than slice composition. No data remains an honest empty-state instead of synthetic `error_type=none`. |
| 101 | Review: Latest Successful Data Timestamp     | Stat       | `max(max_over_time(bioetl_data_freshness_seconds{pipeline=~"$pipeline"}[$__range]))`                                                    | Последний observed ingestion timestamp внутри выбранного pipeline scope за выбранный Grafana range; остаётся в first-screen supporting band и сохраняет UNKNOWN, если freshness samples в range отсутствуют. |

**Используемые метрики:** `records_processed_total`, `data_freshness_seconds`.

Важно: shipped DQ surface теперь явно различает два потока.

- DQ quarantine = `bioetl_dq_records_quarantined_total`
- Silver structural rejects = `bioetl_records_processed_total{stage="filtered_out"}`;
  `FILTERED_OUT_SILVER` remains a compatibility alias only for these rows.
- Gold contract/semantic rejects = `bioetl_processed_records_gold_quarantined_current`
  and `bioetl_processed_records_gold_excluded_by_contract_current`; inspect the
  Gold reject panel/processed-records surfaces, not CLI silver-filter-only path.
- blocked-share impact = `(filtered_out + quarantined) / bronze` inside the
  selected pipeline/run_type window

Для Pushgateway-published final counters shipped dashboards use
`max_over_time(...[$__range])` instead of `increase(...[$__range])`. A completed
BioETL run may first appear to Prometheus as an already non-zero sample; plain
`increase()` then returns `0` and hides real Bronze/DQ/reject evidence.
This value is the maximum published final snapshot observed inside the selected
window, not an arithmetic total across multiple runs. Use RunLedger when an
exact multi-run total is required.

Для bounded reason-level summary dashboard дополнительно использует:

- `bioetl_silver_filter_rejections_total{reason_code,rule_type,field}`
- неизвестные значения схлопываются в `other`
- raw `message` не используется как Prometheus label

**Drilldown (live):** bus `0..6` (Trust → Overview → Runtime → Provider → DQ →
Incident → Run Explorer) preserves the active window via `${__from}` / `${__to}`.
Replay/checkpoint investigation opens via Control Plane / Run Explorer, not a
removed Workflow board. Loki/Tempo Explore-only handoffs are **not** part of the
shipped monitoring surface after 2026-07-23.

______________________________________________________________________

## 12. Дашборд: Silver Reject Explorer

> **REMOVED 2026-07-23.** JSON deleted from `grafana/dashboards/`.
>
> Use CLI for record-level forensics:
> `bioetl quarantine inspect --pipeline <pipeline> ...`
>
> Aggregate Silver structural rejects remain on `4. Data Quality`
> (`bioetl-dq-v2`). Identity HTTP uses **BioETL Ops HTTP** → health
> server `:8000`. Full decision log:
> `docs/05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md`.

Historical panel notes:
`docs/03-guides/dashboards/panels/bioetl-silver-reject-explorer-panels.md`.

## 13. Дашборд: 3. Provider Health

**Файл:** `grafana/dashboards/bioetl-provider-health-v2.json`
**UID:** `bioetl-provider-health-v2`
**Refresh:** 30 секунд
**Time range:** Последние 12 часов
**Назначение:** Операционный incident dashboard по внешним провайдерам. Первый
экран отвечает: какой provider сейчас `DEGRADED`/`FAILING`/`UNKNOWN`, почему,
и какое действие открыть дальше. Range counters/trends остаются evidence ниже
first screen.

**Порядок чтения:** `Monitor GLOBAL Provider Severity Matrix` владеет fleet
verdict, `Monitor Provider Telemetry Freshness` объясняет `UNKNOWN`/no-data,
`Inspect Critical Providers` и `Inspect Provider Top Causes` дают причины, а
shared-shell `Status` — compact selected-provider supporting verdict. `Status`
может расходиться с GLOBAL scope by design и не должен визуально переопределять
GLOBAL severity.

### Панели

| ID  | Название                                        | Тип            | PromQL                                                                                                               | Описание                                                  |
| --- | ----------------------------------------------- | -------------- | -------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| 9101 | Monitor GLOBAL Provider Severity Matrix        | Table          | `bioetl_provider_current_status`                                                                                     | Current provider severity: `0=OK`, `1=DEGRADED`, `2=FAILING`, `null=UNKNOWN`; derived summary semantics, не фильтруется по pipeline. Raw `bioetl_provider_health_status` uses a different contract: `0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY`. |
| 9102 | Inspect Critical Providers                     | Table          | `bioetl_provider_current_status >= 1`                                                                                | Только providers с current `DEGRADED`/`FAILING`; missing current-status telemetry остаётся в `Monitor GLOBAL Provider Severity Matrix` как `UNKNOWN`. Panel exposes direct provider incident runbook handoff. |
| 9103 | Inspect Provider Top Causes                    | Table          | `topk(5, bioetl_provider_current_cause > 0)`                                                                         | Current cause chips: raw health status, failure rate, retry exhaustion, latency, HTTP errors, rate-limit pressure. This panel can stay non-empty while `Monitor GLOBAL Provider Severity Matrix` still reads `0 (OK)` because cause projection includes early-warning provider signals independent of current-status projection. Empty table means no active provider causes are currently above zero; if severity is still non-OK, treat that as an explainability gap. Panel exposes direct provider incident runbook handoff. |
| 9104 | Monitor Provider Telemetry Freshness           | Stat           | `((count(count_over_time(bioetl_provider_current_status[15m])) > bool 0) or (count(count_over_time(bioetl_provider_range_operational_ok[15m])) > bool 0)) * 0 or absent(...) * 1` | First-screen 12h operational-evidence trust marker: `0=OK`, `1=WARN`, `null=UNKNOWN`. Missing both `bioetl_provider_current_status` and `bioetl_provider_range_operational_ok` samples in the active Grafana range means telemetry gap, not proof that providers are healthy; treat `Status=UNKNOWN` as missing provider telemetry until raw enum or selected-range evidence proves otherwise. |
| 9002 | First Action                                   | Text           | n/a                                                                                                                  | CTA block sits on the same first-screen row as `ID` and `Processed Records`, using the rightmost shared-shell slot (`w=8`, `h=6`). It lists the operator read order: GLOBAL severity, telemetry freshness, critical providers/top causes, then selected-provider supporting evidence. Shared `ID` and `Processed Records` stay bounded pipeline-context evidence and do not prove current provider health. |
| 1   | Track Health Check Latency by Provider (p95)    | Timeseries     | `histogram_quantile(0.95, sum by (le, provider) (increase(...[$__interval])))`                                       | Selected-range evidence: p95 latency trend по выбранным providers; `No data` сохраняется как diagnostic gap, не маскируется в `0s`. |
| 114 | Review Raw Provider Health Enum                | Table          | `max by (provider) (bioetl_provider_health_status{provider=~"$provider"}) or ((bioetl_provider_health_check_provider_universe_15m{provider=~"$provider"} * 0) / (bioetl_provider_health_check_provider_universe_15m{provider=~"$provider"} * 0))` | Текущий raw status по provider с mapping `0=UNHEALTHY`, `1=DEGRADED`, `2=HEALTHY`; если provider universe существует без raw status sample, panel остаётся `UNKNOWN`. Use it as supporting evidence when `Status=UNKNOWN` or when first-screen severity and top causes disagree. |
| 2   | Monitor Healthy Checks (Selected Range)         | Stat           | `round(sum(increase(bioetl_health_check_success_total{provider=~"$provider"}[$__range])) or vector(0))`              | Selected-range evidence: completed probes со статусом `HEALTHY` в выбранном окне.  |
| 105 | Monitor Degraded Checks (Selected Range)        | Stat           | `round(sum(increase(bioetl_health_check_degraded_total{provider=~"$provider"}[$__range])) or vector(0))`             | Selected-range evidence: completed probes со статусом `DEGRADED` в выбранном окне; non-zero counts are neutral evidence, not current WARN/CRIT by themselves. |
| 104 | Track Provider Failure Rate (Selected Range)    | Gauge          | `failures_increase / clamp_min(total_increase, 1)`                                                                   | Selected-range evidence: failure-rate за выбранный range. |
| 7   | Track Health Checks Total (Selected Range)      | Stat           | `round(sum(increase(success+degraded+failures[$__range])) or vector(0))`                                             | Selected-range evidence: общий completed health-check volume в выбранном окне. |
| 106 | Failure & Degraded Trend by Provider            | Timeseries     | \`round(sum by (provider) (increase(failures                                                                         | degraded[$\_\_interval])) or vector(0))\`                 |
| 107 | Track Provider Failure Share (Selected Range)   | Bar gauge      | `100 * failures_by_provider / clamp_min(total_failures, 1)`                                                          | Selected-range evidence: ранжирование providers по доле failed probes. |
| 108 | Retries Exhausted by Provider / Operation       | Table          | `round(sum by (provider, operation) (increase(bioetl_data_source_retry_exhausted_total[$__range])) or vector(0))`    | Где retries чаще всего исчерпываются.                     |
| 109 | Retries Exhausted Trend by Provider / Operation | Timeseries     | `round(sum by (provider, operation) (increase(bioetl_data_source_retry_exhausted_total[$__interval])) or vector(0))` | Тренд retry exhaustion incidents во времени.              |
| 102 | Inspect Provider Health Check Latency (p95) - $provider | Gauge          | `histogram_quantile(0.95, sum by (le, provider) (increase(...[$__range])))`                                          | Compact optional selected-provider telemetry; отсутствие samples остаётся diagnostic no-data and not a provider verdict. |

**Используемые метрики:** `health_check_latency_seconds`, `provider_health_status`, `health_check_success_total`, `health_check_degraded_total`, `health_check_failures_total`.

**Фильтрация:** shared context shell `$workflow/$pipeline/$run_type/$run_id`
plus primary `$provider`. Health-check counters и histograms в текущем
инструментировании являются provider-labeled, поэтому current provider status
по-прежнему фильтруется `$provider`; pipeline/run_type/run_id работают как
context/identity/evidence shell.

**Drilldown (live):** bus `0..6` (Trust → Overview → Runtime → Provider → DQ →
Incident → Run Explorer). Sticky shortcuts in the navigation panel do not replace
canonical provider triage; correlate via Runtime/Data Quality or runbook links.

______________________________________________________________________

## 13.1. Дашборд: 2. Runtime

**Файл:** `grafana/dashboards/bioetl-runtime.json`
**UID:** `bioetl-runtime`
**Refresh:** 30 секунд
**Time range:** Последние 12 часов
**Назначение:** L2 diagnostic dashboard для runtime-triage. Он отвечает на вопрос:
где pipeline runtime теряет время, падает, копит backlog или даёт
warning/error conditions. Dashboard остаётся **Prometheus-first**: first screen
должен работать без Loki/Tempo, а tracing-backed log hygiene вынесен в
collapsed row `Tracing-only Log Hygiene (requires optional tracing profile)`.

### Контракт

- **Audience:** SRE, developer, data engineer
- **Primary question:** где runtime теряет время, падает, копит backlog или даёт warning/error signals
- **Variables:** shared `$workflow`, `$pipeline`, `$run_type`, `$run_id` plus bounded `$stage`
- **Forbidden Prometheus labels:** `run_id`, `quarantine_run_id`, `payload_hash`, `manifest_id`, `execution_fingerprint`, `record_id`
- **Top links:** navigation bus `0..6` only; current Runtime stays disabled
- **Known blocked panels:** `Retry vs Failure` и `Batch Size Distribution`
  сознательно не shipped, потому что в текущем metric surface нет подтверждённых
  bounded runtime metrics для этих решений

### Answer Row

| Панель | Query family | Unit | Threshold |
| --- | --- | --- | --- |
| `First Action` | text CTA | n/a | n/a |
| `Runtime Status` | `bioetl_runtime_current_status_trusted{pipeline=~"$pipeline",run_type=~"$run_type"}` | status | `0=OK`, `1=WARN`, `2=CRIT`, `3=INCOMPLETE`, `null=UNKNOWN`; a trust gap forces INCOMPLETE before dashboard filtering |
| `Metrics Evidence` (telemetry confidence) | `bioetl_runtime_trust_gap_status_10m` | status | `0=SCRAPING/RULES OK`, `1=SCRAPE/RULE GAP`, `>=2=SCRAPE+RULE GAP`, `null=UNKNOWN` |
| `Monitor Runtime Blockers` | `bioetl_runtime_current_blocker_reason_scoped{pipeline=~"$pipeline",run_type=~"$run_type"}` anchored by `bioetl_runtime_current_status_trusted == 0` | count | red `>=1`; `0` only when current status is explicitly OK; `null=UNKNOWN` |
| `Runtime Blockers` | `topk(3, bioetl_runtime_current_blocker_reason_scoped{pipeline=~"$pipeline",run_type=~"$run_type"} > 0)` | table | reason/severity/action labels |

Range and localization evidence (`Failed Runs`,
`Runtime Error Rate`, latency, records by stage, logs/traces) lives
below the current-cause row or inside collapsed rows. `Worst Stage Lag`
is colocated with the compact evidence row as a selected-range risk marker; it
is not a current status input.
`Status` and `Runtime Status` consume `bioetl_runtime_current_status_trusted`;
that recording rule applies the runtime telemetry trust gate before dashboard
cards can show green OK. Selected-range zero cards in the
compact evidence row use neutral stat coloring so `0` supports investigation
without becoming a second green health verdict.
`Inspect Active Runtime Blocker Detail` is a collapsed `Detect` drilldown, not
first-screen guidance. This evidence supports investigation but does not replace
the canonical current status recording rule. `Runtime Error Rate`,
`Monitor Runtime Blockers`, `Worst Stage Lag`, and
`Monitor Memory Pressure Active` preserve `UNKNOWN` when telemetry is absent
instead of coercing missing metrics to `0`.
`Monitor Failed Runs` and `Monitor No-Records Runs` show `0` only when
`bioetl_runtime_pipeline_run_type_universe` confirms the selected scope;
missing selected scope remains `UNKNOWN`.
Runtime error-rate thresholds follow the shipped alert policy (`WARN >=5%`,
`CRIT >=20%` dashboard escalation) only when the 30m Bronze denominator is
meaningful (`>=20`); below that gate the panel stays `UNKNOWN` instead of
false OK/CRIT. Stage lag uses `WARN >=300s` and `CRIT >=900s` dashboard
escalation.

### Localization Row

- `Track Stage Backlog Trend`: sustained backlog by `stage`
- `Track Records by Stage / Interval`: throughput by `stage`
- `Track Pipeline Phase Duration p50/p95/p99`: phase latency distribution over
  `bioetl_phase_duration_seconds_bucket`
- `Track Pipeline Duration p50/p95/p99`: runtime/stage latency distribution over
  `bioetl_pipeline_duration_seconds_bucket`
- `Inspect Errors by Stage / Error Code / Range`: bounded runtime error localization
- `Track Records by Stage / Run Type / Range`: dropped/stalled stage localization

### Escalate Row (Handoffs & Process-level Signals)

- **Condition Handoffs**:
  - `Monitor Pipeline Alert Conditions`: runtime failure family using shipped `15m/30m`
    recording rules; links to `pipeline-failure-critical.md`
  - `Inspect DQ Alert Conditions`: compact DQ handoff only; detailed DQ debugging lives in
    `4. Data Quality`
  - `Inspect Control-plane Alert Conditions`: manifest/checkpoint/replay/lineage handoff
    into `0. Control Plane`
  - `Inspect Provider Alert Conditions`: selected-pipeline provider handoff scoped to
    `$provider_hint` across all shipped provider recording-rule conditions
  - `Inspect GLOBAL Provider Alert Conditions`: cluster-wide adapter-latency and
    rate-limiter-wait addends only (not pipeline-localization); provider deep-debug
    stays in `3. Provider Health`
  - `Inspect Freshness Lagged Entities >24h`: raw stale-output freshness evidence
    into DQ/source investigation; this is not a runtime alert-condition recording rule
- **Process-level Signals (GLOBAL)**:
  - `Track GLOBAL Shutdown Initiated by Reason / Interval` and
    `Track GLOBAL Shutdown Completed by Reason / Interval`: process-level graceful
    shutdown visibility; source metrics are reason-only and not pipeline-scoped

Condition handoff cards keep their fixed-window `or vector(0)` event semantics
inside a telemetry anchor: selected Runtime/DQ/Control Plane summaries require
`bioetl_runtime_pipeline_run_type_universe`, and the GLOBAL provider summary
requires `bioetl_provider_current_status`. Missing anchor telemetry renders
`UNKNOWN`, not synthetic OK.

### Logs And Traces

- `Inspect Warning Logs`, `Inspect GLOBAL Unstructured Logs`,
  `Inspect Top Warning Events by Event / Logger / Range`,
  `Track GLOBAL Log Hygiene Trend`
  живут в collapsed tracing-only row и не ломают base runtime surface в
  окружениях без Loki/Tempo
- Loki handoff стартует с безопасного `{job="bioetl"}` entrypoint; warning
  panels parse JSON first, drop parser errors, then filter `pipeline` and
  `level="warning"` parsed fields. Unstructured/global hygiene panels are
  explicitly marked GLOBAL because parse failures cannot be safely scoped by
  pipeline, and they render parsed `.__error__` from the LogQL JSON stage.
  `{job="bioetl"}` is also the canonical smoke-check query for ingestion.
  Empty Explore results can still be legitimate when Loki ingestion/profile
  wiring is disabled or when the runtime emitted no matching structured logs,
  but a fresh local BioETL run with shipped log files should be discoverable
  through this baseline query when Promtail/Loki wiring is healthy.
- Tempo handoff остаётся bounded по `pipeline`; forensic IDs и include-all
  `run_type` selectors в runtime dashboard не протаскиваются. Shipped trace links now open the explicit
search-first Explore Traces route with the active dashboard range passed as
`${__from}` / `${__to}`, `var-ds=tempo`, and safe
`var-groupBy=resource.service.name`, so Tempo metrics
queries stay under the local limit and missing trace data stays an empty Tempo
search rather than failing in a generated breakdown query. Empty trace
drilldowns are legitimate when the runtime used `NoOpTracing` or when no
matching trace spans were exported.

### Drilldown

- Cross-dashboard links передают только target-scoped variables
- Cross-dashboard panel-level handoffs intentionally absent; only canonical navigation bus
  links route to other dashboards. Same-dashboard first-screen drilldowns are
  allowed for blocker inspection.
- `Inspect Control-plane Alert Conditions` и `Monitor No-Records Runs` локализуют
  symptoms. Переход в Control Plane (CP handoff) осуществляется строго через навигационную шину
  (`0. Control Plane` panel 1000) для избежания дублирования ссылок (Вариант А). Панели 5 и 236 используют `dataLinks` только для runbooks и same-dashboard drilldowns.
- action-first Runtime condition panels дополнительно ведут в canonical runbooks

### Instrumentation Debt

- В shipped runtime dashboard отсутствуют `Retry vs Failure` и
  `Batch Size Distribution`, потому что текущий repo не подтверждает bounded
  runtime metric family для этих решений. Это остаётся отдельным follow-up по
  instrumentation, а не поводом выдумывать PromQL.

______________________________________________________________________

## 14. Справочник PromQL-паттернов

### 14.1 Базовые запросы

```promql
# Текущее значение counter
bioetl_records_processed_total{pipeline="chembl", stage="gold"}

# Скорость изменения counter (записей/сек) за 5 минут
rate(bioetl_records_processed_total{pipeline="chembl"}[5m])

# Суммарное значение по всем пайплайнам
sum(bioetl_records_processed_total)

# Группировка по label
sum(bioetl_records_processed_total) by (pipeline)

# Топ-5 пайплайнов по количеству записей
topk(5, sum(bioetl_records_processed_total) by (pipeline))
```

### 14.2 Histogram-запросы

```promql
# P95 длительности пайплайна
histogram_quantile(0.95, sum by (le, pipeline, stage) (rate(bioetl_pipeline_duration_seconds_bucket[5m])))

# P50 (медиана)
histogram_quantile(0.50, sum by (le, pipeline, stage) (rate(bioetl_pipeline_duration_seconds_bucket[5m])))

# Средняя длительность (sum / count)
rate(bioetl_pipeline_duration_seconds_sum[5m]) / rate(bioetl_pipeline_duration_seconds_count[5m])

# P95 с группировкой по пайплайну
histogram_quantile(0.95, sum(rate(bioetl_pipeline_duration_seconds_bucket[5m])) by (le, pipeline))
```

### 14.3 Gauge-запросы

```promql
# Текущее состояние circuit breaker
bioetl_circuit_breaker_state{adapter="chembl"}

# Текущий DQ score
bioetl_dq_validation_score{pipeline="chembl"}

# Среднее время с последнего ingestion
avg(time() - bioetl_data_freshness_seconds) by (pipeline)
```

### 14.4 Ratio и Alert-паттерны

```promql
# Quality Ratio (Gold / Bronze)
sum(bioetl_records_processed_total{stage="gold"}) / sum(bioetl_records_processed_total{stage="bronze"})

# Error Rate (%)
sum by (pipeline) (rate(bioetl_errors_total[5m])) /
  clamp_min(sum by (pipeline) (rate(bioetl_records_processed_total[5m])), 1) * 100

# Quarantine Rate
sum(rate(bioetl_dq_records_quarantined_total[5m])) /
  clamp_min(sum(rate(bioetl_records_processed_total{stage="bronze"}[5m])), 1) * 100

# Circuit breaker open alert
bioetl_circuit_breaker_state == 2

# Data freshness alert (>1 hour stale)
(time() - bioetl_data_freshness_seconds) > 3600
```

### 14.5 Adapter-паттерны

```promql
# P95 latency per provider
histogram_quantile(0.95, sum by (le, provider) (rate(bioetl_adapter_request_duration_seconds_bucket[5m])))

# Request rate per provider
sum(rate(bioetl_adapter_requests_total[5m])) by (provider)

# Error rate per provider
sum(rate(bioetl_http_request_errors_total[5m])) by (provider)

# Success ratio per provider
1 - (sum(rate(bioetl_http_request_errors_total[5m])) by (provider) /
     sum(rate(bioetl_adapter_requests_total[5m])) by (provider))
```

______________________________________________________________________

## 15. Устранение неполадок

### 15.1 Дашборды пустые (No Data)

**Причина 1: Пайплайн не запущен.**

```bash
# Проверить: метрики должны быть доступны
curl -s http://localhost:8000/metrics | head -20

# Если "Connection refused" — запустить пайплайн:
make run-local
```

**Причина 2: Prometheus не скрейпит.**

```bash
# Проверить target в Prometheus UI:
# http://localhost:9090/targets
# Target должен быть "UP"

# Если "DOWN" — проверить сеть:
# На Windows/macOS: host.docker.internal должен резолвиться
# На Linux: добавить --add-host=host.docker.internal:host-gateway
docker compose -f docker-compose.monitoring.yml restart prometheus
```

**Причина 3: Неправильный datasource в Grafana.**

```bash
# Проверить datasource:
# http://localhost:3000/connections/datasources
# Должен быть "Prometheus" с URL "http://prometheus:9090"
# Нажать "Test" — должен показать "Data source is working"
```

**Причина 3a: включён Tempo/Loki datasource без tracing-профиля.**

```bash
# Базовый стек не должен требовать Tempo/Loki.
make monitoring-down
make monitoring-up

# Если нужен tracing-стек, поднимайте его так:
make monitoring-tracing-up
```

**Причина 3b: Grafana Render API отдаёт HTTP 500.**

Server-side screenshots идут через remote `grafana-image-renderer` sidecar.
Для Grafana Image Renderer 5.x repo compose использует pinned image
`grafana/grafana-image-renderer@sha256:c0c920e6974b0d30ae25313051344afcd2054362529968ebd9545a4b2bc8119b`,
explicit shared token (`GF_RENDERING_RENDERER_TOKEN` в Grafana и `AUTH_TOKEN`
в renderer), актуальный `BROWSER_FLAGS=--no-sandbox,--disable-dev-shm-usage`,
`BROWSER_READINESS_TIMEOUT=120s`, `shm_size: 2gb` и renderer metrics scrape
target `grafana-image-renderer`.

```bash
# Проверить, что Grafana видит renderer
curl -u admin:<password> http://localhost:3000/api/frontend/settings

# Проверить server-side render path без Playwright fallback
UV_CACHE_DIR=.cache/uv uv run python -m scripts.ops rerender-grafana \
  --uids bioetl-overview-v2 \
  --fallback none \
  --theme light \
  --width 1024 \
  --height 2200 \
  --timeout-seconds 90 \
  --output-dir /tmp/bioetl-grafana-render-smoke

# После изменения compose обязательно пересоздать оба сервиса:
docker compose -f docker-compose.monitoring.yml up -d --force-recreate renderer grafana
```

Если `/api/frontend/settings` показывает `rendererAvailable=true`, но
`/render/...` всё ещё возвращает `500`, проверьте `docker logs
bioetl-grafana-renderer` и target `grafana-image-renderer` в Prometheus. Для
полного UX-аудита допускается Playwright fallback, но server-side Render API
остаётся отдельным smoke gate. Для полного набора shipped dashboards используйте
не менее `--timeout-seconds 90`: эта опция передается и в локальный HTTP client,
и в параметр Grafana render API `timeout`, поэтому тяжелые dashboard pages не
обрываются на коротком renderer-side smoke-test таймауте при полностью рабочем
renderer sidecar.

For closure/full UX evidence force `--fallback playwright` and run the complete
dark/light × 1600/1024 matrix. `render-manifest.json` must show requested and
actual theme/viewport parity plus `terminal_state_validation.status=ok`.

**Причина 4: Метрики отключены в приложении.**

```bash
# Проверить .env:
grep BIOETL_METRICS .env

# Должно быть:
# BIOETL_METRICS_ENABLED=true
# BIOETL_OBSERVABILITY__METRICS_SERVER_ENABLED=true
```

**Причина 5: пустые панели ID / Processed Records (HTTP, не Prometheus).**

Панели **ID** и **Processed Records** на primary dashboards читают datasource `BioETL Ops HTTP` (`:8000`), а не RunManifest напрямую из Grafana.
Shipped table cards now include explicit no-value copy and a health link:
backend unavailable, invalid selector scope, absent exact run, and true zero
processed records are different states. Treat generic `No data` as
`UNKNOWN` until `/health/live` and the scoped endpoint respond.

```powershell
# Host: BioETL Ops HTTP identity backend (shipping surface after 2026-07-23)
# Quarantine Explorer / :8081 / ensure-quarantine-explorer are retired.
$env:PYTHONPATH = "src"
python -m bioetl health server --host 0.0.0.0 --port 8000

# Проверка
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/metrics
curl "http://127.0.0.1:8000/ops/control-plane/identity-table?pipeline=chembl_target&run_type=backfill&run_id=<run-id>"
```

Docker main stack (health/metrics on `:8000`) + opt-in monitoring:

```bash
python scripts/ops/runtime/docker/runtime_manager.py start --stack main --timeout 180
python scripts/ops/runtime/docker/runtime_manager.py start --stack monitoring --timeout 180
# or: make docker-start-monitoring
```

Grafana from Docker uses **BioETL Ops HTTP** → `http://bioetl:8000`
(env `BIOETL_OPS_HTTP_URL`). There is **no** `quarantine-explorer` service in
`docker-compose.monitoring.yml`. If health server runs on the host instead of
main compose, set `BIOETL_OPS_HTTP_URL=http://host.docker.internal:8000` and
bind the server to `0.0.0.0:8000` (not only `127.0.0.1`).

Canonical Prometheus scrape is `bioetl:8000` on the monitoring network
(job interval 30s). Ops HTTP Prometheus target uses `/metrics`; do not point
`metrics_path` at `/health/live` (JSON). See
`docs/05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md`.

### 15.2 Prometheus Target DOWN

```bash
# Canonical compose-network target (Prometheus API):
# up{job="bioetl",instance="bioetl:8000"} == 1
curl -sS 'http://localhost:9090/api/v1/query?query=up{job="bioetl"}'

# Optional host-side check when metrics are published on the Docker host:
curl http://localhost:8000/metrics

# Host override only (not the shipped default) in grafana/prometheus.yml:
# targets: ['host.docker.internal:8000']  # or host.docker.internal:<port>

# Перезапустить Prometheus
docker compose -f docker-compose.monitoring.yml restart prometheus
```

### 15.3 Grafana не загружает дашборды

```bash
# Проверить provisioning логи
docker logs bioetl-grafana 2>&1 | grep -i "provision\|dashboard\|error"

# Проверить, что JSON-файлы смонтированы
docker exec bioetl-grafana ls /var/lib/grafana/dashboards/

# Проверить валидность JSON
for f in grafana/dashboards/*.json; do
    python -m json.tool "$f" > /dev/null 2>&1 && echo "OK: $f" || echo "FAIL: $f"
done
```

### 15.4 Метрический сервер не запускается (порт занят)

```bash
# Проверить, кто занимает порт
# Windows:
netstat -ano | findstr :8000

# Linux/macOS:
lsof -i :8000

# Решения:
# 1. Изменить порт в .env: BIOETL_METRICS_PORT=8001
# 2. Обновить prometheus.yml: targets: ['host.docker.internal:8001']
# 3. Или убить процесс, занимающий порт
```

### 15.5 Dropdown переменных пустой

Если выпадающий список `Pipeline` или `Run Type` не содержит значений:

- Убедитесь, что пайплайн выполнялся хотя бы один раз после запуска Prometheus.
- Проверьте в Prometheus UI: `http://localhost:9090/graph` → введите `bioetl_records_processed_total` → Execute. Должны появиться результаты.
- Подождите 15-30 секунд после запуска пайплайна (интервал скрейпинга Prometheus).

______________________________________________________________________

## 16. Архитектурные решения и обоснования

### 16.1 Почему Prometheus, а не Push-модель (StatsD, InfluxDB)

Prometheus выбран по следующим причинам:

- **Pull-модель** лучше подходит для batch ETL: приложение не нуждается в знании адреса сервера метрик. Prometheus сам обнаруживает и опрашивает targets.
- **PromQL** — мощный язык запросов для агрегации time series.
- **Prometheus client library** для Python интегрируется минимальным кодом. Метрики определяются как глобальные объекты, HTTP-сервер запускается одной строкой.
- **Grafana интеграция** — Prometheus является first-class datasource в Grafana с полной поддержкой template variables, ad-hoc queries и provisioning.

### 16.2 Почему `run_type` вместо `run_id` в label

Ранние версии дашбордов использовали `run_id` как label для фильтрации по конкретному запуску. Это было исправлено по следующим причинам:

- **High cardinality problem:** Каждый уникальный `run_id` создаёт новую time series в Prometheus. При частых запусках это приводит к экспоненциальному росту количества time series, увеличению потребления памяти и деградации производительности.
- **Prometheus best practices:** Prometheus documentation рекомендует использовать labels с ограниченным количеством возможных значений. `run_type` имеет всего 3 значения (incremental, backfill, rebuild), тогда как `run_id` — неограниченное количество.
- **Практическая достаточность:** Для мониторинга достаточно фильтрации по типу запуска. Для анализа конкретного запуска используются structured logs (JSON) через отдельные инструменты (Loki, ELK).

### 16.3 Разделение v1 и v2 дашбордов

Дашборды существуют в двух версиях для разных use cases:

- **v1 (Legacy):** Исторические тренды за длительные периоды. Используют `rate()` для нормализации counter-метрик. Подходят для анализа производительности за часы и дни.
- **v2 (Latest Run):** Оптимизированы для мониторинга текущего или последнего запуска. Включают информационные панели (Pipeline, Run Type, Timestamp), круговые диаграммы распределения, и более агрессивный time range (7 дней по умолчанию). Используют сырые counter-значения для абсолютных цифр.

### 16.4 MetricsPort vs. прямой prometheus_client

Использование Protocol-интерфейса (MetricsPort) вместо прямого импорта `prometheus_client` обеспечивает:

- **Тестируемость:** В unit-тестах подставляется NoOpMetrics без побочных эффектов.
- **Взаимозаменяемость:** Можно переключиться на StatsD, CloudWatch или любой другой бэкенд без изменения application-кода.
- **Соблюдение ARCH-001:** Domain и Application слои не зависят от infrastructure-библиотек.

Определение MetricsPort в `src/bioetl/domain/ports/observability/metrics.py`:

```python
@runtime_checkable
class MetricsPort(Protocol):
    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str]
    ) -> None: ...
    def increment_counter(
        self, name: str, value: int, labels: dict[str, str]
    ) -> None: ...
    def set_gauge(self, name: str, value: float, labels: dict[str, str]) -> None: ...
    def close(self) -> None: ...
```

### 16.5 NoOp fallback стратегия

Когда метрики отключены или сервер не удаётся запустить, система продолжает работу без мониторинга. Это реализовано через:

- **NoOpMetrics:** Все методы — пустые no-op. Нулевой overhead.
- **Graceful degradation в server.py:** При `fail_fast=false` (по умолчанию) ошибка запуска сервера логируется, но не прерывает пайплайн.
- **Принцип:** Observability не должна блокировать бизнес-логику. Потеря метрик — допустимый tradeoff при сетевых проблемах.

______________________________________________________________________

______________________________________________________________________

## 17. Подробный разбор типов метрик Prometheus

### 17.1 Counter (Счётчик)

Counter — монотонно возрастающая метрика. Значение только увеличивается (или сбрасывается в 0 при перезапуске процесса). Используется для подсчёта событий: количество обработанных записей, количество ошибок, количество HTTP-запросов.

**Особенности Counter в BioETL:**

Prometheus client автоматически создаёт для каждого Counter дополнительную метрику `_created` с timestamp момента первого инкремента. Например, `bioetl_records_processed_total` порождает `bioetl_records_processed_created`. Эти bookkeeping series не следует напрямую показывать в operator dashboards как доменное время выполнения пайплайна.

При работе с Counter в PromQL почти всегда используется функция `rate()` или `increase()`, поскольку сырое значение Counter (кумулятивная сумма) менее информативно, чем скорость изменения.

Пример: `rate(bioetl_records_processed_total{pipeline="chembl", stage="bronze"}[5m])` — показывает среднюю скорость загрузки записей в Bronze-слой за последние 5 минут (записей в секунду).

Пример: `increase(bioetl_records_processed_total{pipeline="chembl", stage="bronze"}[1h])` — показывает абсолютное увеличение количества записей за последний час.

В BioETL Counter-метрики применяются для:

- Подсчёта обработанных записей по стадиям Medallion Architecture (`records_processed_total`).
- Учёта ошибок по типам и стадиям (`errors_total`).
- Отслеживания HTTP-ошибок по провайдерам (`http_request_errors_total`).
- Подсчёта retry-попыток при сетевых сбоях (`data_source_retries_total`, `http_retries_total`).
- Учёта операций vacuum и архивации (`vacuum_files_removed_total`, `archive_files_total`).
- Мониторинга срабатываний circuit breaker (`circuit_breaker_trips_total`).

### 17.2 Histogram (Гистограмма)

Histogram собирает наблюдения (обычно длительности или размеры) и распределяет их по заранее определённым бакетам. Prometheus автоматически создаёт три time series для каждой гистограммы:

- `_bucket{le="X"}` — количество наблюдений, попавших в бакет с границей \<= X.
- `_sum` — сумма всех наблюдённых значений.
- `_count` — общее количество наблюдений.
- `_created` — timestamp создания.

Бакеты определяются при создании метрики. Например, для `bioetl_adapter_request_duration_seconds` бакеты: `[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]` секунд. Это означает, что Prometheus будет считать отдельно количество запросов быстрее 50 мс, быстрее 100 мс, быстрее 250 мс, и так далее.

**Ключевая PromQL-функция: `histogram_quantile()`**

```promql
# P95 латентность API-запросов к ChemBL
histogram_quantile(0.95, sum by (le) (rate(bioetl_adapter_request_duration_seconds_bucket{provider="chembl"}[5m])))
```

Эта функция вычисляет значение, ниже которого попадает заданный процент наблюдений. P95 = значение, ниже которого 95% запросов. Чем выше перцентиль, тем больше "хвостовую" латентность он захватывает.

**Средняя длительность через sum/count:**

```promql
# Средняя длительность запросов за 5 минут
rate(bioetl_adapter_request_duration_seconds_sum{provider="chembl"}[5m])
  /
rate(bioetl_adapter_request_duration_seconds_count{provider="chembl"}[5m])
```

В BioETL Histogram-метрики применяются для:

- Измерения длительности пайплайнов (`pipeline_duration_seconds`).
- Измерения длительности отдельных фаз (`phase_duration_seconds`).
- Распределения размеров батчей (`batch_size_records`).
- Измерения латентности API-запросов (`adapter_request_duration_seconds`, `http_request_duration_seconds`).
- Мониторинга длительности операций хранилища (`vacuum_duration_seconds`, `archive_duration_seconds`, `bronze_write_duration_seconds`).
- Оценки длительности health check (`health_check_duration_seconds`, `health_check_latency_seconds`).
- Измерения времени ожидания rate limiter (`rate_limiter_wait_seconds`).
- Длительности трансформации данных (`transform_duration_seconds`).
- Длительности проверок качества данных (`dq_check_duration_ms`).

### 17.3 Gauge (Измеритель)

Gauge — метрика, значение которой может произвольно увеличиваться или уменьшаться. Представляет "текущее состояние" в момент времени. В отличие от Counter, сырые значения Gauge информативны сами по себе, без `rate()`.

**Примеры Gauge в BioETL:**

- `bioetl_circuit_breaker_state{adapter="chembl"}` — текущее состояние circuit breaker. Значения: 0 (closed — всё работает), 1 (half-open — пробная проверка), 2 (open — провайдер отключён). Этот gauge позволяет мгновенно увидеть, отключён ли какой-то провайдер из-за превышения порога ошибок.

- `bioetl_dq_validation_score{pipeline="chembl", entity="compound"}` — оценка качества данных от 0.0 до 1.0. Значение 0.98 означает, что 98% записей прошли валидацию. Этот gauge обновляется после каждой проверки качества.

- `bioetl_data_freshness_seconds{pipeline="chembl", entity="compound"}` — timestamp (epoch seconds) последнего успешного ingestion. Для вычисления "возраста" данных используется PromQL-выражение `time() - bioetl_data_freshness_seconds`.

- `bioetl_health_check_status{component="database"}` — статус здоровья компонента: 0=unknown, 1=healthy, 2=degraded. Позволяет создавать status pages.

- `bioetl_provider_health_status{provider="chembl"}` — интегральный статус здоровья провайдера.

- `bioetl_rate_limiter_tokens_available{provider="chembl"}` — текущее количество доступных токенов в rate limiter. Когда значение падает до 0, запросы к провайдеру блокируются до восстановления токенов.

______________________________________________________________________

## 18. Medallion Architecture и метрики

### 18.1 Обзор Medallion Architecture

BioETL использует трёхуровневую Medallion Architecture для организации данных. Каждый уровень (Bronze, Silver, Gold) имеет свои метрики, позволяющие отследить поток данных от raw input до чистых финальных таблиц.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL APIs                                │
│    ChemBL API    PubMed API    PubChem API    UniProt API           │
└──────┬────────────┬─────────────┬──────────────┬────────────────────┘
       │            │             │              │
       │  HTTP      │  HTTP       │  HTTP        │  HTTP
       │  requests  │  requests   │  requests    │  requests
       │            │             │              │
       │ Метрики: adapter_request_duration_seconds                    │
       │           http_request_errors_total                          │
       │           adapter_requests_total                             │
       │           rate_limiter_wait_seconds                          │
       ▼            ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BRONZE Layer (Raw Data)                                            │
│                                                                     │
│  Сырые данные с минимальной обработкой. Формат: Parquet.            │
│                                                                     │
│  Метрики:                                                           │
│  - records_processed_total{stage="bronze"} — количество записей     │
│  - bronze_write_duration_seconds — длительность записи               │
│  - bronze_records_written_total — записанные записи                  │
│  - bronze_bytes_written_total — записанные байты                     │
│  - batch_size_records — размеры батчей                               │
│                                                                     │
│  Пример: 15,420 записей из ChemBL API загружены в Bronze            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │  Transform + Validate
                               │
                               │  Метрики:
                               │  - transform_duration_seconds
                               │  - transform_errors_total
                               │  - dq_check_duration_ms
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SILVER Layer (Validated & Deduplicated)                             │
│                                                                     │
│  Данные после валидации, дедупликации, нормализации схемы.          │
│  Формат: Delta Lake (ACID-транзакции, версионирование).             │
│                                                                     │
│  Метрики:                                                           │
│  - records_processed_total{stage="silver"} — валидные записи        │
│  - dq_validation_score — оценка качества (0.0 — 1.0)               │
│  - bioetl_silver_validation_failures_total — ошибки валидации схемы  │
│                                                                     │
│  Пример: 15,380 записей прошли валидацию (40 отсеяно)               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │  Enrich + Final Transform
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  GOLD Layer (Business-Ready)                                        │
│                                                                     │
│  Финальные таблицы для аналитики и data science.                    │
│  Формат: Delta Lake.                                                │
│                                                                     │
│  Метрики:                                                           │
│  - records_processed_total{stage="gold"} — чистые записи            │
│  - dq_records_quarantined_total — канонический DQ quarantine        │
│  - records_processed_total{stage="filtered_out"} — filter rejects   │
│  - data_freshness_seconds — свежесть данных                         │
│                                                                    │
│  Пример: 15,102 записей в Gold, 278 DQ-quarantine, 40 filtered out │
└─────────────────────────────────────────────────────────────────────┘
```

### 18.2 Data Quality Score (Volume-weighted)

Канонический aggregate-показатель качества пайплайна строится из двух
entity-level gauge-метрик:

- `bioetl_dq_validation_score`
- `bioetl_dq_validation_record_count`

```promql
(
  sum(
    last_over_time(bioetl_dq_validation_score{pipeline=~"$pipeline"}[7d])
    * last_over_time(bioetl_dq_validation_record_count{pipeline=~"$pipeline"}[7d])
  )
  /
  clamp_min(
    sum(last_over_time(bioetl_dq_validation_record_count{pipeline=~"$pipeline"}[7d])),
    1
  )
)
```

Этот current stat использует фиксированное seven-day окно, чтобы сохранять
последний репрезентативный DQ snapshot между запусками. Если в окне нет
retained samples, результат остаётся `UNKNOWN`; synthetic zero не создаётся.
`Track: Data Quality Score Trend (Volume-weighted)` намеренно имеет distinct
time semantics и вычисляет raw expression как selected-range trend.

Показатель используется в stat-панели `4. Data Quality` с пороговыми
значениями:

| Значение       | Цвет      | Интерпретация                                      |
| -------------- | --------- | -------------------------------------------------- |
| < 80%          | Красный   | Критическое снижение качества                      |
| 80% .. < 95%   | Оранжевый | Предупреждение, требуется расследование             |
| >= 95%         | Зелёный   | Нормально: высокое качество данных                 |
| Нет samples    | UNKNOWN   | Недостаточно evidence; это не числовой ноль        |

Entity-level gauge `bioetl_dq_validation_score` сохраняется отдельно и остаётся
полезным для worst-case surface (`Monitor: Worst-Entity DQ Score`), но aggregate panel
больше не использует простой `avg(...)`, чтобы крупные сущности не
приравнивались к малым.

Типичное значение для здорового пайплайна: 95-99%. Снижение обычно объясняется:

- Записями с невалидными полями и schema violations.
- DQ quarantine по типизированным ошибкам.
- Аномалиями и soft-threshold событиями, зафиксированными в DQ layer.

### 18.3 Карантин (Quarantined Records)

Записи, не прошедшие валидацию, не удаляются, а перемещаются на карантин.
Канонический операторский источник истины:

- `bioetl_dq_records_quarantined_total{pipeline, error_type, run_type}` — детализированный счётчик с указанием типа ошибки (`schema_violation`, `null_required_field`, `duplicate`, `type_mismatch` и др.).

Важно:

- `bioetl_records_processed_total{stage="quarantined"}` может встречаться как legacy/support signal в части runtime paths.
- shipped dashboards и alerting должны опираться на `bioetl_dq_records_quarantined_total`, когда речь идёт именно о DQ quarantine.

Silver structural rejects имеют две связанные поверхности: stage-total
`bioetl_records_processed_total{stage="filtered_out"}` и bounded breakdown
`bioetl_silver_filter_rejections_total{pipeline, run_type, reason_code, rule_type, field}`.
Shipped rules публикуют `bioetl_silver_filter_reject_total_mismatch_15m` и alert
`BioETLSilverFilterRejectAccountingMismatch`, чтобы эти surfaces не расходились
молча. `FILTERED_OUT_SILVER` остаётся legacy alias только для этого Silver
structural пути; Gold contract/semantic rejects отслеживаются отдельными
`bioetl_processed_records_gold_*_current` surfaces.

______________________________________________________________________

## 19. Circuit Breaker и мониторинг провайдеров

### 19.1 Модель Circuit Breaker (ADR-007)

BioETL использует паттерн Circuit Breaker для защиты от каскадных сбоев при взаимодействии с внешними API. Каждый адаптер (ChemBL, PubMed, PubChem, UniProt) имеет собственный circuit breaker с тремя состояниями:

**Closed (0):** Нормальная работа. Все запросы проходят к провайдеру. Ошибки считаются, но не блокируют запросы.

**Open (2):** Провайдер временно отключён после превышения порога ошибок. Все запросы мгновенно отклоняются без обращения к API. Экономит ресурсы и предотвращает перегрузку нестабильного провайдера.

**Half-Open (1):** Пробное состояние. Допускается один тестовый запрос. Если успешен — переход в Closed. Если неуспешен — обратно в Open.

```promql
# Мониторинг состояния circuit breaker
bioetl_circuit_breaker_state{adapter="chembl"}
# 0 = closed (нормально), 1 = half-open (проверка), 2 = open (отключён)

# Количество срабатываний за последний час
increase(bioetl_circuit_breaker_trips_total{adapter="chembl"}[1h])

# Соотношение успешных/неуспешных вызовов
sum(rate(bioetl_circuit_breaker_success_total{adapter="chembl"}[5m]))
  /
(sum(rate(bioetl_circuit_breaker_success_total{adapter="chembl"}[5m]))
  +
 sum(rate(bioetl_circuit_breaker_failure_total{adapter="chembl"}[5m])))
```

### 19.2 Provider Health Dashboard: как читать

Дашборд `3. Provider Health` теперь строится как answer-first incident surface.
Первый экран отвечает на три вопроса без прокрутки:

1. какой provider сейчас `DEGRADED`/`FAILING`/`UNKNOWN`;
2. какие providers уже вышли из нормального состояния;
3. какая причина сейчас доминирует;
4. есть ли свежая current-status telemetry.

Практический порядок чтения:

- `Monitor GLOBAL Provider Severity Matrix` — canonical first-screen severity.
  `0=OK`, `1=DEGRADED`, `2=FAILING`, `null/NaN=UNKNOWN`.
- `Inspect Critical Providers` — только providers с текущим severity `>=1`.
- `Inspect Provider Top Causes` — active cause chips из canonical recording
  rules: raw health-status degradation, failure rate, retry exhaustion, adapter
  latency, HTTP errors, rate-limit pressure. Эта панель может оставаться
  непустой даже при `GLOBAL severity = OK`, потому что cause projection
  deliberately включает early-warning provider signals независимо от
  current-status projection. Empty table means no canonical provider cause is
  currently above zero; if severity is still non-OK, treat that as an
  explainability gap and continue triage from the severity matrix.
- `Monitor Provider Telemetry Freshness` — first-screen trust marker for
  `bioetl_provider_current_status`; missing samples in the active Grafana range
  mean telemetry gap, not healthy provider state.
- `Status` is the compact selected-provider supporting verdict. It is rendered
  as value-only scoped evidence so `UNKNOWN`, `OK`, `0`, and `No data` states do
  not visually compete with the GLOBAL severity hierarchy.
- `Review Raw Provider Health Enum` stays below the first screen as supporting
  raw-source evidence. Use it when `Status=UNKNOWN` or when top causes and
  first-screen severity disagree.
- Ниже первого экрана идут selected-range evidence panels: health-check
  counters, failure/degraded trends, retry exhaustion, and compact optional
  telemetry for per-provider p95 latency, adapter endpoint latency, HTTP error
  volume, rate-limiter wait/tokens, and circuit-breaker state/trips. Optional
  panels stay collapsed under `Selected Provider Detail` so empty samples do not
  look like a large empty tail.

Ключевые operator semantics:

- `Track Provider Failure Rate (Selected Range)` использует policy thresholds
  `5%` warning / `20%` critical.
- `Inspect Adapter Request Latency by Endpoint (p95)` uses seconds; its `>5s`
  red band aligns with the degraded provider rule, while lower bands are
  earlier-warning diagnostics.
- `Track Rate Limiter Wait by Provider (p95)` keeps a yellow early-warning band
  below the degraded rule threshold `>1s`.
- `Monitor Minimum Rate Limiter Tokens Available` preserves `No data` as a
  telemetry gap; it must not synthesize `0` tokens when samples are absent.
- Circuit-breaker panels intentionally остаются cross-scope adapter diagnostics:
  `bioetl_circuit_breaker_state` и `bioetl_circuit_breaker_trips_total`
  маркируются label `adapter`, не `provider`. Missing samples remain
  diagnostic; trip panel does not invent a synthetic adapter row.
- Для latency panels `No data` означает отсутствие samples или probe activity,
  а не `0s latency`.

______________________________________________________________________

## 20. Data Quality Monitor (DQMonitorPort)

### 20.1 Архитектура DQ мониторинга

Data Quality Monitor реализует статистическое обнаружение аномалий на основе Z-score анализа. Компонент определён через порт `DQMonitorPort` в domain-слое и реализован как `DataQualityMonitor` в infrastructure-слое.

Ключевые метрики DQ, отражающиеся в дашбордах:

**`bioetl_dq_validation_score`** — центральная метрика качества. Gauge от 0.0 до 1.0. Вычисляется как `valid_records / total_records` после каждой проверки. Значение 1.0 означает, что все записи прошли валидацию.

**`bioetl_dq_anomaly_detected`** — инкрементируется при обнаружении аномалии. Labels: `pipeline` (какой пайплайн), `metric` (какая метрика), `severity` (LOW, MEDIUM, HIGH, CRITICAL), `anomaly_type` (SPIKE, DROP, THRESHOLD_EXCEEDED).

**`bioetl_dq_baseline_samples`** — текущее количество исторических точек в baseline для каждой метрики. Чем больше samples, тем точнее Z-score анализ. Рекомендуется минимум 7 точек (недельный baseline).

**`bioetl_dq_baseline_updated`** — количество обновлений baseline. Baseline обновляется только после успешных запусков без критических аномалий. Это защищает от "отравления" baseline плохими данными.

### 20.2 Z-score анализ

DataQualityMonitor вычисляет Z-score для каждой метрики:

```
z_score = (current_value - baseline_mean) / baseline_stddev
```

Пороги severity:

- |z_score| > 2.0: MEDIUM
- |z_score| > 2.5: HIGH
- |z_score| > 3.0: CRITICAL

Пример: если baseline средний record_count = 15,000 с stddev = 500, и текущий record_count = 12,000:

- z_score = (12000 - 15000) / 500 = -6.0
- Severity = CRITICAL (|z_score| > 3.0)
- Anomaly type = DROP (текущее значение ниже baseline)

______________________________________________________________________

## 21. Rate Limiting и его мониторинг

### 21.1 Метрики Rate Limiter

BioETL реализует rate limiting для предотвращения превышения лимитов API провайдеров. Мониторинг осуществляется двумя метриками:

**`bioetl_rate_limiter_tokens_available{provider}`** (Gauge) — текущее количество доступных токенов. При значении 0 все запросы блокируются до восстановления токенов. Мониторинг этой метрики позволяет предсказать, когда пайплайн начнёт замедляться из-за rate limiting.

**`bioetl_rate_limiter_wait_seconds{provider}`** (Histogram) — время ожидания в rate limiter. Бакеты: 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0 секунд. Рост P95 ожидания указывает на приближение к лимитам API.

```promql
# Текущие доступные токены по провайдерам
bioetl_rate_limiter_tokens_available

# P95 ожидание в rate limiter
histogram_quantile(0.95, sum by (le, provider) (rate(bioetl_rate_limiter_wait_seconds_bucket[5m])))

# Среднее время ожидания за последний час
rate(bioetl_rate_limiter_wait_seconds_sum[1h]) / rate(bioetl_rate_limiter_wait_seconds_count[1h])
```

______________________________________________________________________

## 22. Рекомендации по созданию пользовательских дашбордов

### 22.1 Создание через Grafana UI

1. Открыть `http://localhost:3000`.
1. Перейти: Dashboards → New → New Dashboard → Add visualization.
1. Выбрать datasource: Prometheus.
1. Ввести PromQL-запрос, например: `bioetl_records_processed_total{pipeline="chembl"}`.
1. Настроить визуализацию (panel type, thresholds, legend).
1. Сохранить дашборд.

### 22.2 Создание JSON-дашборда для provisioning

Для автоматического provisioning создайте JSON-файл в `grafana/dashboards/`. Структура:

```json
{
    "annotations": { "list": [] },
    "editable": true,
    "panels": [
        {
            "datasource": { "type": "prometheus", "uid": "prometheus" },
            "targets": [
                {
                    "expr": "bioetl_records_processed_total{pipeline=~\"$pipeline\"}",
                    "legendFormat": "{{stage}}",
                    "refId": "A"
                }
            ],
            "title": "My Panel",
            "type": "timeseries",
            "gridPos": { "h": 8, "w": 24, "x": 0, "y": 0 },
            "id": 1
        }
    ],
    "templating": {
        "list": [
            {
                "datasource": { "type": "prometheus", "uid": "prometheus" },
                "definition": "label_values(bioetl_records_processed_total, pipeline)",
                "name": "pipeline",
                "label": "Pipeline",
                "type": "query",
                "includeAll": false,
                "multi": false,
                "refresh": 1
            }
        ]
    },
    "title": "My Custom Dashboard",
    "uid": "my-custom-dashboard",
    "version": 1
}
```

Grafana автоматически обнаружит новый файл в течение 30 секунд (настраивается в `bioetl.yaml` → `updateIntervalSeconds`).

### 22.3 Рекомендуемые визуализации по типу метрик

| Тип метрики          | Рекомендуемая визуализация | Функция PromQL                                      |
| -------------------- | -------------------------- | --------------------------------------------------- |
| Counter (total)      | Timeseries с `rate()`      | `rate(metric[5m])`                                  |
| Counter (total)      | Stat (суммарное значение)  | `sum(metric)`                                       |
| Histogram (duration) | Timeseries с перцентилями  | `histogram_quantile(0.95, sum by (le, <bounded_label>) (rate(metric_bucket[5m])))` |
| Histogram (size)     | Bar chart                  | `histogram_quantile(0.50, metric_bucket)`           |
| Gauge (state)        | Stat с color mapping       | `metric` (сырое значение)                           |
| Gauge (score)        | Gauge с thresholds         | `metric` (значение 0-1)                             |
| Gauge (freshness)    | Stat с unit "seconds"      | `time() - metric`                                   |
| Counter ratio        | Gauge (0-100%)             | `sum(a) / sum(b)`                                   |

### 22.4 Рекомендуемые интервалы rate()

| Сценарий                                           | Интервал            | Обоснование                       |
| -------------------------------------------------- | ------------------- | --------------------------------- |
| Live мониторинг (короткие runtime/overview тренды) | `[1m]`              | Максимальная отзывчивость         |
| Стандартный мониторинг                             | `[5m]`              | Баланс отзывчивости и сглаживания |
| Trend-анализ                                       | `[15m]` или `[30m]` | Сглаженные тренды без шума        |
| Долгосрочный анализ                                | `[1h]`              | Дневные и недельные паттерны      |

Правило: интервал `rate()` должен быть как минимум в 4 раза больше scrape interval цели. Global Prometheus defaults remain `15s` (→ prefer `rate(...[1m])`), while the canonical BioETL job scrapes every **30s** (→ prefer `rate(...[2m])` or longer for bioetl series).

______________________________________________________________________

## 23. FAQ (Часто задаваемые вопросы)

### Как узнать, какие метрики экспортирует BioETL?

```bash
curl -s http://localhost:8000/metrics | grep "^bioetl_" | awk '{print $1}' | sort -u
```

Или в Prometheus UI: введите `{__name__=~"bioetl_.*"}` и нажмите Execute.

### Почему shipped dashboards обновляются каждые 30 секунд?

Primary operator dashboards `0..6` use `refresh: 30s`. That reduces Prometheus
load and keeps heavy queries (`histogram_quantile`, `rate`, multi-label
aggregates, Loki hygiene) predictable.

**Exception:** `Silver Reject Explorer` (`bioetl-silver-reject-explorer`) uses
`refresh: 1m` and default time range `24h` for forensic/record-level work. Do not
document a single global 30s refresh for every shipped dashboard.

### Где legacy v1 dashboards?

Legacy v1 dashboards сохранены только как archived comparison surface. Они не
являются operator entrypoints; текущая эксплуатация использует восемь shipped
JSON surfaces: `bioetl-control-plane-v1`, `bioetl-overview-v2`,
`bioetl-runtime`, `bioetl-provider-health-v2`, `bioetl-dq-v2`,
`retired: workflow/alerts merged, and
`bioetl-silver-reject-explorer`.

### Как добавить новую метрику?

1. Определите метрику в профильном `src/bioetl/infrastructure/observability/_metrics_defs_*.py`:
   ```python
   MY_NEW_METRIC = Counter("bioetl_my_new_metric", "Description", ["label1", "label2"])
   ```
1. Зарегистрируйте её в `src/bioetl/infrastructure/observability/prometheus_metric_registries.py`.
1. Если добавляете labels, синхронизируйте bounded policy в `src/bioetl/infrastructure/observability/prometheus_metric_label_dispatch.py` и `src/bioetl/infrastructure/observability/prometheus_metric_label_policy_sets.py`.
1. Вызывайте через MetricsPort в application-коде:
   ```python
   self._metrics.increment_counter("my_new_metric", value=1, labels={"label1": "val"})
   ```
1. Добавьте panel/rule consumers в shipped JSON/YAML surfaces и обновите promtool/python tests.

### Counter-window semantics

Use `increase(<counter>[$window])` for event-delta counters such as
`bioetl_pipeline_runs_total`, `bioetl_errors_total`, and
`bioetl_silver_validation_failures_total`. Use `max_over_time(...)` only for
pushed snapshot/range-evidence totals where the latest pushed value inside the
window is the intended evidence, including `bioetl_records_processed_total`,
`bioetl_stage_records_total`, and `bioetl_dq_records_quarantined_total`.
`bioetl_silver_filter_rejections_total` may use `max_over_time()` only for a
boolean recent-event presence gate; reason/field event totals use `increase()`.
Pushed snapshot evidence is not an exact multi-run total; reconcile exact totals
from RunLedger.

### Как метрики переживают перезапуск приложения?

При перезапуске BioETL все Counter-метрики сбрасываются в 0 (это стандартное поведение Prometheus client). Prometheus обрабатывает это корректно: функция `rate()` и `increase()` автоматически учитывают сброс счётчика (counter reset), вычисляя дельту с учётом последнего известного значения перед перезапуском. Gauge-метрики также сбрасываются, но будут установлены заново при первом измерении после запуска.

Исторические данные в Prometheus TSDB не теряются при перезапуске приложения. Prometheus хранит все собранные данные в персистентном volume `prometheus-data`.

### Как работает формат Prometheus exposition?

Метрики экспортируются в текстовом формате. Каждая строка — одна time series:

```
metric_name{label1="value1", label2="value2"} numeric_value timestamp
```

Специальные строки начинаются с `#`:

- `# HELP metric_name Description` — описание метрики.
- `# TYPE metric_name counter|gauge|histogram|summary` — тип метрики.

Prometheus парсит этот формат при каждом scrape и сохраняет в TSDB.

### Сколько места занимают метрики в Prometheus?

Зависит от количества уникальных time series (комбинаций метрик и labels). BioETL с 4 провайдерами и 3 типами запуска генерирует приблизительно 200-500 уникальных time series. При scrape_interval=15s и retention=15 дней это занимает около 50-100 МБ. Для production с десятками пайплайнов рекомендуется мониторить `prometheus_tsdb_head_series` (текущее количество active series) и увеличивать storage при необходимости.

### Можно ли использовать Grafana без Docker?

Да. Установите Prometheus и Grafana нативно, затем:

1. Запустите Prometheus с конфигом `grafana/prometheus.yml`. Измените target на `localhost:8000`.
1. Запустите Grafana. Добавьте Prometheus как datasource (`http://localhost:9090`).
1. Импортируйте JSON-файлы из `grafana/dashboards/` через UI: Dashboards → Import → Upload JSON file.

Или настройте provisioning, скопировав содержимое `grafana/provisioning/` в директорию provisioning Grafana и обновив `path` в `bioetl.yaml` на абсолютный путь к `grafana/dashboards/`.

______________________________________________________________________

______________________________________________________________________

## 24. Alerting (Настройка оповещений)

### 24.1 Grafana Alerting

Grafana поддерживает встроенные алерты на основе PromQL-условий. Для настройки:

1. Откройте панель дашборда → Edit.
1. Перейдите на вкладку "Alert" (доступна для Timeseries и Stat панелей).
1. Определите условие: например, `WHEN avg() OF query(A, 5m, now) IS ABOVE 2` (средняя латентность > 2 секунд).
1. Настройте notification channel (Email, Slack, PagerDuty, Webhook).
1. Сохраните дашборд.

### 24.2 Рекомендуемые алерты для BioETL

**Критические алерты (требуют немедленного внимания):**

| Алерт                | Условие PromQL                                                                        | Severity | Описание                                                                       |
| -------------------- | ------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------ |
| Circuit Breaker Open | `bioetl_circuit_breaker_state == 2`                                                   | CRITICAL | Провайдер полностью отключён. Пайплайн не может получать данные.               |
| Quality Ratio Drop   | `sum(records_processed{stage="gold"}) / sum(records_processed{stage="bronze"}) < 0.5` | CRITICAL | Более 50% данных теряется. Возможна проблема с источником или схемой.          |
| Zero Records         | `increase(bioetl_records_processed_total{stage="bronze"}[1h]) == 0`                   | CRITICAL | За последний час не загружено ни одной записи. Пайплайн может быть остановлен. |
| Health Check Failed  | `bioetl_health_check_status == 0`                                                     | CRITICAL | Компонент инфраструктуры недоступен.                                           |

**Предупреждающие алерты (требуют внимания в рабочее время):**

| Алерт                | Условие PromQL                                                                                                                           | Severity | Описание                                                       |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------- |
| High Latency         | `histogram_quantile(0.95, sum by (le, provider) (rate(bioetl_adapter_request_duration_seconds_bucket[5m]))) > 5`                         | WARNING  | P95 латентность API > 5 секунд. Провайдер может деградировать. |
| Error Rate Spike     | `rate(bioetl_http_request_errors_total[5m]) > 0.1`                                                                                       | WARNING  | Более 10% запросов завершаются ошибкой.                        |
| Data Staleness       | `(time() - bioetl_data_freshness_seconds) > 86400`                                                                                       | WARNING  | Данные старше 24 часов. Пайплайн не выполнялся.                |
| Retry Exhaustion     | `increase(bioetl_data_source_retry_exhausted_total[1h]) > 0`                                                                             | WARNING  | Retry-попытки исчерпаны. Запросы к провайдеру не проходят.     |
| DQ Anomaly           | `increase(bioetl_dq_anomaly_detected{severity="critical"}[1h]) > 0`                                                                      | WARNING  | Обнаружена критическая аномалия качества данных.               |
| High Quarantine Rate | `sum(rate(bioetl_dq_records_quarantined_total[5m])) / clamp_min(sum(rate(bioetl_records_processed_total{stage="bronze"}[5m])), 1) > 0.1` | WARNING  | Более 10% записей ушло в DQ quarantine.                        |

### 24.3 Prometheus Alerting Rules

Для production-деплоя рекомендуется использовать Alertmanager. Пример правил алертинга:

```yaml
# prometheus/alerts.yml (примерная конфигурация)
groups:
  - name: bioetl_alerts
    rules:
      - alert: CircuitBreakerOpen
        expr: bioetl_circuit_breaker_state == 2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker open for {{ $labels.adapter }}"
          description: "Circuit breaker for adapter {{ $labels.adapter }} has been open for 5 minutes."

      - alert: HighAPILatency
        expr: histogram_quantile(0.95, sum by (le, provider) (rate(bioetl_adapter_request_duration_seconds_bucket[5m]))) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High API latency for {{ $labels.provider }}"
          description: "P95 latency for {{ $labels.provider }} is {{ $value }}s (threshold: 5s)"

      - alert: DataQualityDrop
        expr: >
          sum(bioetl_records_processed_total{stage="gold"})
            /
          sum(bioetl_records_processed_total{stage="bronze"})
            < 0.8
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Data quality ratio below 80%"
```

### 24.4 Встроенные правила наблюдения

В репозитории добавлен файл правил:

`grafana/prometheus-rules/bioetl_observability.yml`

Правила покрывают:

- targeted `chembl_assay` baseline для preflight/run-failure smoke coverage;
- reusable control-plane и traceability сигналы:
  `manifest_writes_total`, `ledger_appends_total`,
  `checkpoint_compatibility_events_total`, `lineage_*`;
- reusable DQ/freshness сигналы:
  `dq_soft_threshold_exceeded`, quarantine-rate, critical
  `dq_validation_failures_total`, `dq_anomaly_detected`,
  `bioetl_silver_validation_failures_total`, `data_freshness_seconds`;
- reusable provider сигналы:
  `health_check_*` failure ratio и `data_source_retry_exhausted_total`.

Эти rules автоматически загружаются через:

- `grafana/prometheus.yml` (`rule_files: /etc/prometheus/rules/*.yml`);
- volume mount в `docker-compose.monitoring.yml`:
  `./grafana/prometheus-rules:/etc/prometheus/rules:ro`.

Проверка после применения:

```bash
docker compose -f docker-compose.monitoring.yml restart prometheus
# Rules:
open http://localhost:9090/rules
# Active alerts:
open http://localhost:9090/alerts
```

______________________________________________________________________

## 25. Глоссарий

| Термин                     | Определение                                                                                                                   |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Bronze**                 | Первый слой Medallion Architecture. Содержит сырые данные из внешних API без обработки. Формат: Parquet.                      |
| **Silver**                 | Второй слой. Данные после валидации, дедупликации и нормализации. Формат: Delta Lake с ACID-гарантиями.                       |
| **Gold**                   | Третий слой. Финальные бизнес-готовые таблицы для аналитики. Формат: Delta Lake.                                              |
| **Quarantined**            | Записи, не прошедшие валидацию в Silver/Gold. Сохраняются отдельно для ручного анализа.                                       |
| **Circuit Breaker**        | Паттерн, защищающий от каскадных сбоев. Автоматически отключает провайдер при превышении порога ошибок (ADR-007).             |
| **Counter**                | Тип метрики Prometheus. Монотонно возрастающее значение. Сбрасывается при перезапуске процесса.                               |
| **Gauge**                  | Тип метрики Prometheus. Произвольное значение, может расти и уменьшаться. Представляет текущее состояние.                     |
| **Histogram**              | Тип метрики Prometheus. Распределение значений по бакетам. Позволяет вычислять перцентили.                                    |
| **PromQL**                 | Prometheus Query Language. Функциональный язык запросов для агрегации и анализа time series.                                  |
| **Scrape**                 | Процесс сбора метрик. Prometheus выполняет HTTP GET к targets каждые `scrape_interval` секунд.                                |
| **Target**                 | Endpoint, с которого Prometheus собирает метрики. Canonical BioETL: `bioetl:8000` (job interval 30s); host override optional. |
| **Time Series**            | Уникальная комбинация имени метрики и набора labels. Каждая time series хранит набор пар (timestamp, value).                  |
| **Label**                  | Ключ-значение пара, добавляющая измерение к метрике. Позволяет фильтровать и группировать данные.                             |
| **Template Variable**      | Переменная Grafana, значения которой определяются PromQL-запросом. Используется для динамической фильтрации дашбордов.        |
| **Provisioning**           | Механизм автоматической загрузки конфигурации (datasources, dashboards) при старте Grafana.                                   |
| **MetricsPort**            | Protocol-интерфейс в domain-слое BioETL. Абстрагирует запись метрик от конкретной реализации (Prometheus, NoOp).              |
| **NoOpMetrics**            | Null Object реализация MetricsPort. Все методы — пустые no-op. Используется когда метрики отключены.                          |
| **Rate Limiter**           | Механизм ограничения скорости запросов к внешним API для соблюдения лимитов провайдера.                                       |
| **Run Type**               | Тип запуска пайплайна: incremental (только новые данные), backfill (ретроспективное заполнение), rebuild (полная пересборка). |
| **TSDB**                   | Time Series Database. Хранилище Prometheus для time series данных. Оптимизировано для append и range queries.                 |
| **Adapter**                | В контексте Hexagonal Architecture: реализация порта для конкретной технологии (ChemBLClient, PrometheusMetrics).             |
| **Exposition Format**      | Текстовый формат экспорта метрик Prometheus: `metric{labels} value timestamp`.                                                |
| **Retention**              | Период хранения данных в Prometheus TSDB. По умолчанию 15 дней. Настраивается через `--storage.tsdb.retention.time`.          |
| **DQ Monitor**             | Data Quality Monitor. Компонент обнаружения аномалий на основе Z-score анализа baseline метрик.                               |
| **Z-score**                | Статистическая мера, показывающая, на сколько стандартных отклонений значение отклоняется от среднего.                        |
| **Medallion Architecture** | Паттерн организации данных в три слоя (Bronze → Silver → Gold) с повышением качества на каждом уровне.                        |

______________________________________________________________________

## 26. Сводная таблица дашбордов

Canonical human inventory (panel counts, datasources, versioning):
`docs/03-guides/dashboards/dashboard-inventory.md`.
Machine mapping: `docs/03-guides/dashboards/contracts/dashboard-inventory.yaml`.

| Dashboard | UID | Primary surface | Purpose |
| --- | --- | --- | --- |
| 0. Trust | `bioetl-control-plane-v1` | Prometheus + BioETL Ops HTTP | Replay/resume trust, manifest/ledger/checkpoint |
| 1. Overview | `bioetl-overview-v2` | Prometheus + BioETL Ops HTTP | L0 answer, L1 cards, collapsed Alert/SLO triage |
| 2. Pipeline Diagnostics | `bioetl-runtime` | Prometheus + BioETL Ops HTTP | Blockers, latency, backlog, workflow band |
| 3. Provider Health | `bioetl-provider-health-v2` | Prometheus + BioETL Ops HTTP | Provider latency, health, failure taxonomy |
| 4. Data Quality | `bioetl-dq-v2` | Prometheus + BioETL Ops HTTP | DQ current/range, quarantine aggregates |
| 5. Incident Workspace | `bioetl-incident-v1` | Prometheus | Multi-domain suspects + ALERTS support |
| 6. Run Explorer | `bioetl-run-explorer-v1` | BioETL Ops HTTP | Exact-run identity (never Prom `run_id` labels) |

**Retired (not shipped):** `bioetl-workflow-overview`, `bioetl-alerts-slo`,
`bioetl-silver-reject-explorer`. Do not list them as active routing targets.

______________________________________________________________________

## 27. Metric lifecycle reference boundary

The full metric lifecycle is described once in sections 2 and 5 of this
document. The canonical implementation contract is
`docs/04-reference/contracts/observability.md`; the concise operator route is
`docs/03-guides/dashboards/monitoring-index.md`.

Do not add new active lifecycle walkthroughs here. Keep this README focused on
stack setup, provisioning, dashboard inventory, and validation commands.

### 27.1 Dashboard inventory, drift, and health checks

Use the QA entrypoint below when validating shipped dashboards against docs,
provisioning, or exported/deployed snapshots:

```bash
uv run python -m scripts.engineering.qa report-dashboard-inventory --json
uv run python -m scripts.engineering.qa report-dashboard-inventory --check --json
uv run python -m scripts.engineering.qa report-dashboard-inventory --health-summary --json
uv run python -m scripts.engineering.qa report-dashboard-inventory --deployed-dir /path/to/grafana-exports --check --json
```

`--check` validates docs parity plus provisioning contract. `--health-summary`
adds a machine-readable rollup for local dashboard health. `--deployed-dir`
compares shipped JSON against exported/deployed snapshots while ignoring benign
Grafana export noise such as root `id` / `version` and panel-level
`pluginVersion`.

### 27.2 Prometheus rule validation

Use the deterministic QA entrypoint for repo-backed Prometheus rules:

```bash
uv run python -m scripts.engineering.qa check-prometheus-rules
```

It runs:

```bash
promtool check rules grafana/prometheus-rules/bioetl_observability.yml \
  grafana/prometheus-rules/bioetl_control_plane_current_status.yml
promtool test rules grafana/prometheus-rules/tests/bioetl_observability.test.yml
```

If local `promtool` is missing, the command fails fast with install/Docker
guidance. CI runs the same entrypoint with `--runner docker`; add
`--coverage-json` to publish the regression-guarded alert/record/control-plane
fixture coverage summary.

______________________________________________________________________

## 28. Безопасность и production-конфигурация

### 28.1 Ограничение доступа к Grafana

По умолчанию Grafana доступна без аутентификации (`GF_AUTH_ANONYMOUS_ENABLED=true`). Это подходит для локальной разработки, но в production необходимо включить аутентификацию:

```yaml
# docker-compose.monitoring.yml — production конфигурация
environment:
  GF_AUTH_ANONYMOUS_ENABLED: "false"
  GF_SECURITY_ADMIN_USER: "admin"
  GF_SECURITY_ADMIN_PASSWORD: "${GRAFANA_ADMIN_PASSWORD}"  # Из .env файла
  GF_USERS_ALLOW_SIGN_UP: "false"
```

Для организаций с SSO рекомендуется настроить OAuth2-интеграцию (поддерживаются Google, GitHub, LDAP, SAML).

### 28.2 Защита metrics endpoint

Metrics endpoint (`/metrics` на порту 8000) по умолчанию открыт без аутентификации. В production рекомендуется:

1. **Network isolation:** Ограничить доступ к порту 8000 через firewall rules. Только Prometheus должен иметь доступ.
1. **Reverse proxy:** Поставить nginx/Envoy перед metrics endpoint с basic auth.
1. **Prometheus basic auth:** Настроить аутентификацию в `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'bioetl'
    basic_auth:
      username: 'prometheus'
      password_file: '/etc/prometheus/password'
    static_configs:
      - targets: ['bioetl:8000']  # host.docker.internal:8000 only as host override
```

### 28.3 Label cardinality контроль

Высокая cardinality labels — главная угроза производительности Prometheus. Правила BioETL:

- **Запрещено** использовать уникальные ID (run_id, request_id, user_id) в labels. Каждое уникальное значение создаёт новую time series.
- **Допустимо:** pipeline (4-6 значений), stage (4 значения), run_type (3 значения), error_type (5-10 значений).
- **Мониторинг cardinality:** `prometheus_tsdb_head_series` показывает текущее количество active time series. Порог предупреждения: >10,000. Критический: >100,000.

Пример вычисления cardinality для `records_processed_total`:

- 4 пайплайна × 4 стадии × 3 типа запуска = 48 time series
- Плюс автоматически созданные `_created`: ещё 48
- Итого: 96 time series от одной метрики

Для всех 58+ метрик BioETL общая cardinality составляет 200-500 time series, что находится в безопасных пределах.

### 28.4 Retention и storage sizing

Prometheus хранит данные в локальной TSDB. Параметры по умолчанию:

- `--storage.tsdb.retention.time=15d` — хранение 15 дней
- `--storage.tsdb.retention.size` — не ограничено (по умолчанию)

Для production рекомендуется:

- Установить обе опции: `--storage.tsdb.retention.time=30d --storage.tsdb.retention.size=5GB`
- Использовать persistent volume для данных Prometheus (уже настроено в docker-compose.monitoring.yml: volume `prometheus-data`)
- Для долгосрочного хранения (месяцы/годы) использовать remote write в Thanos, Cortex или VictoriaMetrics

### 28.5 Horizontal scaling

При увеличении количества пайплайнов и провайдеров может потребоваться горизонтальное масштабирование мониторинга:

1. **Sharded Prometheus:** Несколько инстансов Prometheus, каждый скрейпит подмножество targets. Grafana использует datasource с type `prometheus` и настройкой `exemplarTraceIdDestinations` для корреляции.

1. **Federation:** Центральный Prometheus агрегирует данные из дочерних инстансов через `federation` endpoint.

1. **VictoriaMetrics:** Совместимая с Prometheus TSDB с более эффективным storage и встроенной поддержкой кластеризации. Замена datasource URL в Grafana на VictoriaMetrics endpoint (полностью совместим с PromQL).

______________________________________________________________________

## 29. Интеграция с CI/CD

### 29.1 Валидация дашбордов в CI

Для предотвращения поломки дашбордов при изменении метрик рекомендуется добавить в CI/CD pipeline:

```bash
# Валидация JSON-формата всех дашбордов
for f in grafana/dashboards/*.json; do
    python -m json.tool "$f" > /dev/null || { echo "FAIL: $f"; exit 1; }
done

# Проверка отсутствия phantom-метрик (метрик, не определённых в коде)
PYTHONPYCACHEPREFIX=/tmp/pycache .venv/bin/python -m pytest \
    tests/integration/test_grafana_config.py \
    tests/integration/test_prometheus_rules_config.py \
    -q

# Canonical inventory/report surface:
PYTHONPYCACHEPREFIX=/tmp/pycache .venv/bin/python -m scripts.engineering.qa \
    report-observability-metric-inventory --json
```

### 29.2 Smoke-тест мониторинга

После деплоя новой версии BioETL рекомендуется выполнить smoke-тест:

```bash
# 1. Проверить доступность metrics endpoint
curl -sf http://localhost:8000/metrics | grep -q "bioetl_" || echo "FAIL: metrics not available"

# 2. Проверить Prometheus target status
curl -sf http://localhost:9090/api/v1/targets | python -c "
import json, sys
data = json.load(sys.stdin)
targets = data['data']['activeTargets']
for t in targets:
    if 'bioetl' in t['labels'].get('job', ''):
        print(f\"{t['labels']['job']}: {t['health']}\")
        if t['health'] != 'up':
            sys.exit(1)
"

# 3. Проверить наличие данных в Prometheus
curl -sf 'http://localhost:9090/api/v1/query?query=bioetl_records_processed_total' | python -c "
import json, sys
data = json.load(sys.stdin)
if data['data']['result']:
    print(f\"Found {len(data['data']['result'])} time series\")
else:
    print('WARNING: No data yet (pipeline may not have run)')
"

# 4. Проверить доступность Grafana
curl -sf http://localhost:3000/api/health | python -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Grafana: {data['database']}\" )
"
```

### 29.3 Обновление дашбордов при изменении метрик

При переименовании или удалении метрик в коде необходимо синхронно обновить все дашборды. Рекомендуемый workflow:

1. Найти все использования метрики в дашбордах:
   ```bash
   grep -rn "old_metric_name" grafana/dashboards/
   ```
1. Обновить PromQL-запросы в соответствующих JSON-файлах.
1. Обновить каталог метрик в документации (раздел 5 этого документа).
1. Запустить CI-валидацию (раздел 29.1).
1. Выполнить smoke-тест (раздел 29.2).

______________________________________________________________________

**Конец документа.**

*Версия 2.0.0. Обновлена 2026-07-03. Синхронизирована с RULES.md v6.1.4 и текущим состоянием shipped dashboards.*
