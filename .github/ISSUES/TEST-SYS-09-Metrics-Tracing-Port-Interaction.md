---
title: "[P2][testing] TEST-SYS-09: MetricsPort/TracingPort interaction tests for top pipelines"
labels: P2, testing, observability, metrics, tracing, quality
assignees: []
github_issue: 7031
---

## Context

Observability ports are gated in architecture/integration for naming and some
emission consistency, but **not every critical pipeline unit path asserts**
MetricsPort / TracingPort side-effects via fakes.

**Audit:** `reports/grok/review_test_system_architecture_audit_20260729_FULL.md` §9, P2-3  
**Epic:** TEST-SYS-00  
**Prior:** TEST-AUDIT-017 (#5929)

## Problem

Metric/tracing regressions can ship while business assertions pass.

## Scope / modules

- `LoggerPort` / `MetricsPort` / `TracingPort` fakes in unit tests
- Top pipelines: composite orchestration + one primary provider pipeline path
- Application services that own emission points

## Acceptance Criteria

- [ ] Unit tests with port fakes assert expected metric names/labels and span/events for happy + failure paths on agreed top surfaces
- [ ] No requirement that Grafana/Docker monitoring be up for unit green (ADR-010 local-only)
- [ ] Align metric names with governance/architecture metric tests
- [ ] Avoid duplicating full dashboard integration in unit lane

## Related

- Integration emission tests (keep)
- ADR-010 optional monitoring
