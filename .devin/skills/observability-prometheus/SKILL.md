---
name: "observability-prometheus"
description: "Create, review, test, or debug BioETL Prometheus alert and recording rules with real metric and label evidence."
---

# Observability Prometheus

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Prometheus rules and tests in the repository

## Workflow

1. Discover the real metric and label contract before editing PromQL.
2. Use `mode=rule-edit`, `rule-test`, or `query-debug`.
3. Validate changed rules with `promtool` and repository tests when available.
4. Treat empty results and zero-valued results as distinct alerting states.

This single skill replaces `prometheus-alert-rule-editor` and
`prometheus-rule-testing`; dashboard callers use `observability-dashboard`.
