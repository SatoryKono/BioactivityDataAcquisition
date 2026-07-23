---
name: grafana-dashboard-render
description: Render, preflight-check, and capture evidence for shipped BioETL Grafana dashboards. Use when the task is to produce reproducible dashboard screenshots, validate Grafana render/auth readiness, run live reviewed panel audits, or explain why full render is blocked on the current host.
---

# Grafana Dashboard Render

## Overview

Use this skill when the task is about rendering shipped Grafana dashboards in
this repository, not editing their JSON semantics.

This skill is for:

- full screenshot refresh of `grafana/dashboards/*.json`
- preflight checks before a dashboard audit
- live reviewed panel validation against Grafana, Prometheus, and Quarantine
  Explorer
- diagnosing render failures such as `401`, missing Playwright runtime, or
  missing Chromium shared libraries

Use `grafana-dashboard-extension` instead when the user wants to change
dashboard JSON, queries, navigation, or operator-facing UX.

## BioETL Runtime Policy

- Project runtime contract: `../../../AGENTS.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Shared Grafana/Prometheus prerequisites: [../grafana-dashboard-extension/references/grafana-prometheus-prerequisites.md](../grafana-dashboard-extension/references/grafana-prometheus-prerequisites.md)
- Shipped dashboards: `grafana/dashboards/*.json`
- Canonical screenshot tooling:
  - `python -m scripts.ops rerender-grafana`
  - `python -m scripts.ops check-grafana-audit-preflight`
  - `python -m scripts.ops audit-live-grafana`
- Operator/tooling docs: `grafana/README.md`
Do not treat ad-hoc `curl /render/...` experiments as canonical evidence unless
they match the shipped tooling path.

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
- `quarantine-explorer: ok/error` tells you whether HTTP-backed dashboard panels
  can be audited safely

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

### 4. Run live reviewed panel audit when semantics matter

For semantically sensitive validation, use:

```bash
uv run python -m scripts.ops audit-live-grafana \
  --workflow <workflow> \
  --pipeline <pipeline> \
  --run-type <run_type> \
  --run-id <run_id> \
  --app-base-url http://127.0.0.1:8081 \
  --output /tmp/live-panel-audit.json
```

Use this when the user cares about:

- `ID`
- `Processed Records`
- checkpoint freshness
- DQ freshness
- zero-vs-no-data semantics
- Silver Reject Explorer denominator behavior

### 5. Report render blockers honestly

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
- Quarantine Explorer-backed dashboards may require a live BioETL HTTP backend
  on `127.0.0.1:8081`.

## Validation Checklist

- Preflight result captured
- Render output directory contains expected PNGs and `render-manifest.json`
- If semantics matter, live reviewed panel audit output captured
- If full render is blocked, the exact failing preflight/render check is
  reported

## Definition Of Done

- The requested dashboards are rendered through the canonical repo tooling, or
  the exact blocker is identified.
- Any live panel audit requested by the user is run with explicit scope.
- The final response distinguishes:
  - render success/failure
  - data/semantic success/failure
  - host/runtime prerequisites
