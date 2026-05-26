---
id: fix-track-d-fixture-opentelemetry-import-timeout-20260526
title: Fix Track D fixture OpenTelemetry import timeout
task_id: fix-track-d-fixture-opentelemetry-import-timeout-20260526
created_at: '2026-05-26T08:19:26Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/bootstrap/runtime/tracing_bootstrap.py
- src/bioetl/composition/bootstrap/runtime/logger_bootstrap.py
- src/bioetl/composition/bootstrap/runtime/metrics_bootstrap.py
- src/bioetl/composition/bootstrap/runtime/dq_bootstrap.py
- src/bioetl/composition/bootstrap/runtime/observability.py
- tests/unit/composition/bootstrap/runtime/test_tracing_bootstrap.py
- tests/unit/composition/bootstrap/runtime/test_observability_entrypoints.py
summary: Lazy-loaded runtime observability bootstrap adapters so disabled/default
  paths no longer import OpenTelemetry, structlog-backed logger, Prometheus metrics,
  or DQ anomaly adapters at module import time. Added regression tests for import
  laziness and verified Track D fixture linkage on Windows.
---

# Episodic summary

## Task

- Title: Fix Track D fixture OpenTelemetry import timeout

## Outcome

- Lazy-loaded runtime observability bootstrap adapters so disabled/default paths no longer import OpenTelemetry, structlog-backed logger, Prometheus metrics, or DQ anomaly adapters at module import time. Added regression tests for import laziness and verified Track D fixture linkage on Windows.

## Lessons learned

- Replace with durable follow-up if needed
