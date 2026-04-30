> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source:
> - Gemini: `/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/.codex/skills/grafana-dashboard-extension/SKILL.md`
> Governance: [AI Runtime Mirror Ownership](../../../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md), [Memory Usage](../../../agents/guides/MEMORY_USAGE.md), [Post-Change Validation](../../../agents/policy/POST_CHANGE_VALIDATION.md).
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

## name: grafana-dashboard-extension description: Extend, edit, validate, and review shipped Grafana dashboards for BioETL. Use when tasks touch `grafana/dashboards/*.json`, dashboard navigation, panel queries, variables, units, thresholds, Loki/Tempo drilldowns, or operator-facing dashboard UX. Treat repo dashboard JSON as source of truth and update docs when shipped dashboard behavior changes.

# Grafana Dashboard Extension

## Overview

Use this skill when the task involves changing, extending, validating, or
reviewing Grafana dashboards in BioETL.

## BioETL Runtime Policy

- Project runtime contract: `../../../AGENTS.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

Default to repo dashboard mode first:

- shipped dashboards under `grafana/dashboards/*.json`
- local dashboard docs under `docs/03-guides/dashboards/`

Use live Grafana tooling only to validate or debug behavior after the repo state
is understood.

## When To Use

Trigger this skill when the user asks to:

- add, remove, or edit panels in `grafana/dashboards/*.json`
- change dashboard links, navigation, variables, units, thresholds, or legends
- add or fix Prometheus, Loki, or Tempo queries
- add or fix Loki / Tempo drilldowns
- debug empty, noisy, or misleading panels
- review a dashboard for usability, correctness, or observability hygiene
- synchronize dashboard docs with changed shipped behavior

## Required Starting Point

Before editing:

1. Read the target dashboard JSON in `grafana/dashboards/`.
1. Read `docs/03-guides/dashboards/dashboard-extension-llm.md`.
1. If the task affects shipped navigation or operator workflow, also read:
   - `docs/03-guides/dashboards/README.md`
   - `docs/03-guides/dashboards/monitoring-index.md`
   - `docs/03-guides/dashboards/dashboard-v2-usage.md`
   - `docs/05-operations/01-monitoring-guide.md`
   - `grafana/README.md`

## BioETL Rules

### Source of Truth

- Treat `grafana/dashboards/*.json` as the primary source of truth.
- Do not infer dashboard structure from screenshots, memory, or stale docs.
- If docs and JSON disagree, trust the JSON and then reconcile docs.

### Current Navigation Model

Preserve the current shipped model unless the task explicitly changes it:

- `1. Overview`
- `2. Runtime`
- `3. Provider Health`
- `4. Data Quality`

If this model changes, update the affected docs in the same change set.

### Query and Panel Safety

- Do not invent metric names.
- Avoid unnecessary high-cardinality label filters in summary panels.
- Be explicit about `0` versus `No data`.
- Do not silently turn dashboard hints into real alerting behavior.
- Keep drilldown links readable, stable, and operator-friendly.

### Datasource Conventions

#### Prometheus

- Use `or vector(0)` only when missing series really means zero events.
- Preserve absence when missing data is diagnostic.

#### Loki

- Prefer safe baselines such as `{job="bioetl"}` when narrowing queries.
- Use `| json` and `__error__` deliberately when extracting structured logs.
- Do not rely on brittle encoded interpolation as a hidden source of truth.

#### Tempo

- Keep trace search behavior explicit.
- Prefer minimal, stable search expressions before introducing richer filters.

## Workflow

### 1. Triage the Request

Classify the change:

- structure change: new panel, row, variable, or link
- query change: PromQL, LogQL, or TraceQL correction
- UX change: title, description, unit, threshold, legend, or time range
- navigation change: dashboard links, overview hub, operator flow
- debug task: empty panel, broken link, wrong labels, noisy data

### 2. Read Current State

- Open the target dashboard JSON.
- Identify:
  - `uid`
  - title
  - tags
  - templating variables
  - panel IDs
  - datasource references
  - links and drilldowns
- Preserve stable IDs unless a deliberate migration is required.

### 3. Make the Smallest Safe Change

- Prefer localized edits over broad JSON rewrites.
- Preserve existing panel IDs and ordering when possible.
- Reuse naming and panel conventions from nearby dashboards.
- Keep operator UX coherent across the dashboard family.

### 4. Cascade Docs When Needed

Update docs in the same change set if you changed:

- dashboard title
- navigation links
- default time range or refresh
- operator-facing workflow
- drilldown behavior
- datasource expectations that affect usage guidance

### 5. Verify

Minimum verification:

```bash
uv run python -m json.tool grafana/dashboards/<dashboard>.json
uv run python -m pytest -q tests/integration/test_grafana_config.py
```

Recommended when navigation or panel semantics changed:

```bash
uv run python -m pytest -q tests/integration/test_grafana_config.py tests/architecture
```

If live Grafana access is available and relevant:

- confirm the dashboard renders
- confirm links open the intended destination
- confirm variables and drilldowns interpolate correctly
- confirm empty-state behavior is intentional

## Review Checklist

- JSON is valid.
- `uid` is preserved unless migration is explicit.
- Panel and query changes match real datasource semantics.
- `0` versus `No data` is intentional.
- Links and drilldowns remain coherent.
- Titles, units, thresholds, and legends are consistent.
- No unnecessary high-cardinality filters were introduced.
- Docs were updated if shipped behavior changed.

## Tooling Guidance

Prefer:

- local file edits for repo dashboard JSON
- Grafana MCP for dashboard summaries, panel queries, datasource discovery,
  screenshots, panel renders, and query debugging

Use live Grafana tools to validate behavior, not to replace repo JSON as source
of truth.

## Definition of Done

- The dashboard JSON is valid.
- The intended panel, navigation, or query behavior is implemented.
- Repo docs are synchronized if shipped behavior changed.
- Targeted verification passes.
- No accidental dashboard drift was introduced outside the requested scope.
