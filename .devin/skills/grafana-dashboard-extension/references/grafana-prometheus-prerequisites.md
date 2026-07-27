# Grafana And Prometheus Prerequisites

Shared reference for BioETL Grafana and Prometheus skills. Use this from
dashboard extension/render work and Prometheus discovery, debugging, alert
editing, and rule testing.

## Source Order

1. Repo files first: `grafana/dashboards/*.json`, alert/rule files, and
   `docs/03-guides/dashboards/`.
1. Live datasource discovery second, when available.
1. Screenshots/render evidence only after repo state and query intent are
   understood.

Do not treat screenshots, stale docs, or memory as the source of truth for
dashboard structure.

## Recommended Skill Order

1. `prometheus-metric-discovery`: verify metric names, labels, and selectors.
1. `prometheus-query-debugger`: fix PromQL shape, aggregation, empty-state, and
   label matching.
1. `grafana-dashboard-extension` or `prometheus-alert-rule-editor`: make repo
   dashboard/rule changes.
1. `prometheus-rule-testing`: prove repo-backed alert or recording rules with
   `promtool` when applicable.
1. `grafana-dashboard-render`: run render preflight and screenshot evidence for
   shipped dashboards.

## State Reporting

Use distinct status language:

- `No data`: query is valid but selected range has no samples.
- `Zero`: missing series semantically means zero events and the query encodes it
  intentionally, for example with `or vector(0)`.
- `Query invalid`: PromQL/LogQL/TraceQL cannot execute or has unsupported shape.
- `Datasource unavailable`: live validation cannot reach the datasource.
- `Render blocked`: dashboard JSON/query may be valid, but screenshot/render
  evidence could not be captured.
- `Validation failed`: local JSON, promtool, or test gates failed.

## Required Checks

For dashboard JSON edits:

```bash
uv run python -m json.tool grafana/dashboards/<dashboard>.json
uv run python -m pytest -q tests/integration/test_grafana_config.py
```

For repo-backed Prometheus rules:

```bash
promtool test rules <test-file.yml>
```

For runtime AI/docs guidance changes:

```bash
uv run python -m scripts.docs check-drift --runtime-mirrors --freshness
```

## Guardrails

- Do not invent metric names or labels.
- Preserve absence when missing data is diagnostic.
- Use low-cardinality selectors unless a high-cardinality selector is explicitly
  justified.
- Keep dashboard navigation aligned with AGENTS.md dashboard routing.
- Keep docs mirrors synchronized when shipped dashboard behavior changes.

