> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/grafana-dashboard-render/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: grafana-dashboard-render
description: Render, preflight-check, and capture runtime evidence for shipped BioETL Grafana dashboards. Use when the task is to produce reproducible dashboard renders, validate Grafana render/auth readiness, run live reviewed panel audits, or explain why full render is blocked on the current host.
---

# Grafana Dashboard Render

## Overview

Use this skill when the task is about rendering shipped Grafana dashboards in
this repository, not editing their JSON semantics.

This skill is for:

- full runtime-render refresh of `grafana/dashboards/*.json`
- preflight checks before a dashboard audit
- live reviewed panel validation against Grafana, Prometheus, and BioETL Ops
  HTTP (`bioetl health server` on `:8000`)
- diagnosing render failures such as `401`, missing Playwright runtime, or
  missing Chromium shared libraries

Use `grafana-dashboard-extension` instead when the user wants to change
dashboard JSON, queries, navigation, or operator-facing UX.

## BioETL Runtime Policy

- Project runtime contract: `../../../AGENTS.md`

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`

- Shared Grafana/Prometheus prerequisites: [../grafana-dashboard-extension/references/grafana-prometheus-prerequisites.md](../grafana-dashboard-extension/references/grafana-prometheus-prerequisites.md)
- Shipped dashboards: `grafana/dashboards/*.json`
- Canonical screenshot tooling:
  - `python -m scripts.ops rerender-grafana`
  - `python -m scripts.ops check-grafana-audit-preflight`
  - `python -m scripts.ops audit-live-grafana`
- Operator/tooling docs: `grafana/README.md`
Do not treat ad-hoc `curl /render/...` experiments as canonical evidence unless
they match the shipped tooling path.

## Evidence Policy

Runtime-rendered dashboards are the primary evidence for every visual audit.
Before assessing readability, render every dashboard in scope through the
canonical project renderer. Use evidence in this order:

1. `RUNTIME_RENDER`
1. `DASHBOARD_JSON` when layout structure must be confirmed
1. `GRAFANA_INSPECT`
1. `BROWSER_INSPECTION`
1. `USER_SCREENSHOT`

User-provided screenshots are supplemental only when runtime rendering is
blocked, a panel is missing from the render, or comparison with an older state
is required. Never prefer a user screenshot over a contradictory runtime
render.

Every observation must name its evidence source and confidence:

- evidence source: `RUNTIME_RENDER`, `DASHBOARD_JSON`, `GRAFANA_INSPECT`,
  `BROWSER_INSPECTION`, or `USER_SCREENSHOT`
- confidence: `FACT`, `INFERENCE`, or `UNKNOWN`
- use two independent indicators for a conclusion whenever the available
  evidence permits it

If a panel did not render completely, record:

```text
Confidence: UNKNOWN
Reason: Render incomplete.
```

Do not infer the missing visual state.

## Default Workflow

### 1. Inventory the target

- Read the shared prerequisites when render work includes Prometheus-backed
  panel semantics, zero-vs-no-data interpretation, or validation handoff:
  [../grafana-dashboard-extension/references/grafana-prometheus-prerequisites.md](../grafana-dashboard-extension/references/grafana-prometheus-prerequisites.md).
- If the user asked for all dashboards, enumerate `grafana/dashboards/*.json`.
- If the user named specific dashboards, preserve those UIDs and avoid broad
  rerender noise.

Useful command:

```bash
uv run python scripts/engineering/qa/report_dashboard_inventory.py --json
```

### 2. Run preflight first

Always start with:

```bash
uv run python -m scripts.ops check-grafana-audit-preflight --json --skip-screenshot-check
```

Interpretation:

- `grafana: ok` means Grafana API is reachable
- `grafana-render-auth: ok` means render-sensitive auth is valid
- `playwright-runtime: ok/error` tells you whether browser fallback can work on
  this host
- `quarantine-explorer` / Ops HTTP probe: prefer BioETL Ops HTTP health on
  `:8000` for HTTP-backed identity panels (Explorer UI removed 2026-07-23)

If preflight fails, report the failing check explicitly before attempting more
render work.

### 3. Choose the render path

Prefer the canonical Python renderer:

```bash
uv run python -m scripts.ops rerender-grafana --timeout-seconds 90 --output-dir <dir>
```

Useful variants:

```bash
uv run python -m scripts.ops rerender-grafana --uids bioetl-control-plane-v1 --fallback none --output-dir <dir>
uv run python -m scripts.ops rerender-grafana --uids bioetl-overview-v2 bioetl-runtime --output-dir <dir>
```

Guidance:

- Use `--fallback none` when you need to prove the server-side Grafana render
  path works independently of Playwright.
- Use at least `--timeout-seconds 90` for full-suite server-side renders. The
  option is forwarded to the Grafana render API `timeout` parameter as well as
  the local client timeout; larger BioETL dashboards can exceed short
  smoke-test timeouts even when the Render API is healthy.
- Use default fallback behavior when you want a best-effort screenshot refresh
  and browser capture is acceptable.

### 4. Capture required render groups

A render group is uniquely defined by dashboard, time range, selector state,
viewport, theme, and render timestamp. If the same dashboard is rendered more
than once with the same state, retain one group for the visual audit and use
the repeat only for consistency validation.

For every dashboard record:

- UID and title
- URL
- time range
- template variables and selected values
- viewport size
- browser zoom when browser capture is used
- Grafana version when available
- render timestamp
- datasource loading/terminal-state status
- panels not rendered
- panels with errors

Capture both the initial viewport and a full-page render. Use the Grafana
Render API for reproducible viewport evidence and the Playwright path for
full-page, expanded-row, lazy-panel, actual-theme, and terminal-state evidence.

At minimum render these viewports:

- `1366x768`
- `1440x900`
- `1920x1080`

When the canonical render path supports kiosk mode, also render:

- `2560x1440`
- `3840x2160`

For every supported viewport check clipping, wrapping, overflow, auto-shrink,
scrollbars, panel resize, navigation and selector wrapping, legend wrapping,
table overflow, and responsive typography. Do not claim responsive behavior
from a single viewport.

Render both `dark` and `light` when supported. If light theme is not supported,
record this as a fact, not a defect:

```text
Confidence: FACT
Light Theme is not supported.
```

Repeat one identical-state render group for every dashboard and compare layout,
typography, panel size, wrapping, clipping, and layout shifts. Dynamic data
differences must not be reported as render inconsistency.

### 5. Run live reviewed panel audit when semantics matter

For semantically sensitive validation, use:

```bash
uv run python -m scripts.ops audit-live-grafana \
  --workflow <workflow> \
  --pipeline <pipeline> \
  --run-type <run_type> \
  --run-id <run_id> \
  --app-base-url http://127.0.0.1:8000 \
  --output /tmp/live-panel-audit.json
```

Use this when the user cares about:

- `ID`
- `Processed Records`
- checkpoint freshness
- DQ freshness
- zero-vs-no-data semantics
- control-plane identity / Ops HTTP tables

### 6. Audit only runtime renders

All readability findings must be based on generated runtime renders. Do not:

- assess clipping from a user screenshot when a runtime render exists
- infer text size from a downscaled image
- use JPEG artifacts as evidence
- claim responsive behavior without multiple viewport renders

Use dashboard JSON only as corroboration for layout, not as a substitute for
rendered readability evidence.

### 7. Report render blockers honestly

Common outcomes:

- `401 Unauthorized`:
  repo/local Grafana auth mismatch or missing env bootstrap
- `Playwright runtime probe failed: Cannot find module 'playwright'`:
  browser fallback not installed on this host
- `Missing shared libraries prevent Playwright Chromium from launching`:
  host OS packages missing

When blocked:

- say whether the block is in server-side render, browser fallback, or backend
  datasource health
- keep data-contract findings separate from screenshot/runtime failures

## Host And Env Notes

- Repo env bootstrap: `scripts/ops/support/load_repo_env.sh`
- Grafana auth must come from runtime env only:
  `GF_SECURITY_ADMIN_PASSWORD` / `GRAFANA_PASSWORD` (optional
  `GRAFANA_USERNAME` / `GF_SECURITY_ADMIN_USER`). Do not document or commit a
  default password; preflight fails closed when auth material is missing.
- Service-account auth may be provided through `GRAFANA_SERVICE_ACCOUNT_TOKEN`.
- BioETL Ops HTTP identity panels require a live `bioetl health server` on
  `127.0.0.1:8000` (not Quarantine Explorer / `:8081`).

## Validation Checklist

- Preflight result captured
- Render output directory contains expected PNGs and `render-manifest.json`
- Required viewport/theme render groups captured
- Initial viewport and full-page evidence distinguished
- Repeated render consistency checked
- Every finding includes evidence source and confidence
- If semantics matter, live reviewed panel audit output captured
- If full render is blocked, the exact failing preflight/render check is
  reported

## Final Report Format

Use `Render Inventory`, never `Screenshot Inventory`.

| Render Group | Dashboard | Viewport | Theme | Time Range | Variables | Render Status | Missing Panels | Evidence Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

For each finding include:

```text
Evidence source:
- RUNTIME_RENDER
- DASHBOARD_JSON

Confidence: FACT
```

## Definition Of Done

- The requested dashboards are rendered through the canonical repo tooling, or
  the exact blocker is identified.
- Any live panel audit requested by the user is run with explicit scope.
- The final response distinguishes:
  - render success/failure
  - data/semantic success/failure
  - host/runtime prerequisites
