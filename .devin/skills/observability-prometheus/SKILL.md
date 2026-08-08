---
name: "observability-prometheus"
description: "Create, review, test, or debug BioETL Prometheus alert and recording rules with real metric and label evidence."
---

# Observability Prometheus

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- Prometheus rules and tests in the repository

## Environment Configuration

This skill uses Prometheus credentials from the repository root `.env` file:

- `PROMETHEUS_URL` - Prometheus server URL (default: http://localhost:9090)
- `PROMETHEUS_TOKEN` - Prometheus authentication token
- `PROMETHEUS_USERNAME` - Prometheus username (basic auth)
- `PROMETHEUS_PASSWORD` - Prometheus password (basic auth)

**Note:** Monitoring services are optional (ADR-010). Do not start `docker-compose.monitoring.yml`
unless the user explicitly requests Prometheus rule work.

## Workflow

1. Discover the real metric and label contract before editing PromQL.
2. Use `mode=rule-edit`, `rule-test`, or `query-debug`.
3. Validate changed rules with `promtool` and repository tests when available.
4. Treat empty results and zero-valued results as distinct alerting states.

This single skill replaces `prometheus-alert-rule-editor` and
`prometheus-rule-testing`; dashboard callers use `observability-dashboard`.
