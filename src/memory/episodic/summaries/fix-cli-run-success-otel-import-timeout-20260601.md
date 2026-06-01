---
id: fix-cli-run-success-otel-import-timeout-20260601
title: Fix CLI run success OpenTelemetry logging import timeout
task_id: fix-cli-run-success-otel-import-timeout-20260601
created_at: '2026-06-01T06:02:06Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/observability/logging_config.py
summary: Changed logging trace context lookup to use already-loaded OpenTelemetry
  modules from sys.modules instead of importing opentelemetry from every structlog
  event. Added regression tests proving inactive tracing does not import OTel and
  loaded OTel trace context is still injected. Verified CLI run success targeted timeout
  regression, ruff, module coverage inventory, and source-tree hash guard.
---

# Episodic summary

## Task

- Title: Fix CLI run success OpenTelemetry logging import timeout

## Outcome

- Changed logging trace context lookup to use already-loaded OpenTelemetry modules from sys.modules instead of importing opentelemetry from every structlog event. Added regression tests proving inactive tracing does not import OTel and loaded OTel trace context is still injected. Verified CLI run success targeted timeout regression, ruff, module coverage inventory, and source-tree hash guard.

## Lessons learned

- Replace with durable follow-up if needed
