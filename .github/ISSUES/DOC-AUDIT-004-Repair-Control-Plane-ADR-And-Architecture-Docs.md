---
title: "docs(architecture): repair control-plane ADR cross-links and ADR-022 observability guidance"
labels: documentation, architecture, observability, enhancement
assignees: []
---

## Context

The 2026-06-19 documentation audit found architecture-level documentation drift
in two places:

1. `domain-control-plane.md` misattributes ADR-044 and ADR-047.
2. ADR-022 still documents legacy noop module paths and outdated label-policy
   assumptions.

## Problem

`docs/02-architecture/domain-control-plane.md` currently says:

- `ADR-044 (Workflow Control Plane)`
- `ADR-047 (Control Plane Architecture)`

The accepted ADRs actually are:

- `ADR-044: Run Manifest and Run Ledger Control Plane`
- `ADR-047: Workflow Control Plane for Declarative Workflows`

Separately, `docs/02-architecture/decisions/ADR-022-tracing-noop.md` still:

- points to legacy `domain/ports/noop.py`;
- implies `run-id` may appear in metrics labels;

while the current repo contract places noop implementations under
`src/bioetl/domain/ports/noop/` and explicitly forbids `run_id` as a
Prometheus label in current dashboard/rule governance.

## Evidence

- `docs/02-architecture/domain-control-plane.md:7-8`
- `docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md`
- `docs/02-architecture/decisions/ADR-047-workflow-control-plane.md`
- `docs/02-architecture/decisions/ADR-022-tracing-noop.md:74`
- `src/bioetl/domain/ports/noop/__init__.py`
- `docs/03-guides/dashboards/monitoring-index.md`
- `docs/04-reference/contracts/observability.md`
- `tests/integration/test_grafana_dashboard_links.py:845`
- `tests/integration/test_prometheus_rules_config.py:804`

## Proposed Solution

1. Correct ADR names and links in `domain-control-plane.md`.
2. Re-review the page for any additional control-plane/workflow-plane wording drift.
3. Update ADR-022 to the current noop package layout.
4. Update ADR-022 correlation/metrics wording so `run_id` is described as
   control-plane or HTTP identity context, not a Prometheus label.
5. Cross-link ADR-022 back to the current observability contract pages.

## Acceptance Criteria

- [ ] `domain-control-plane.md` references ADR-044 and ADR-047 correctly.
- [ ] ADR-022 references `src/bioetl/domain/ports/noop/` rather than legacy `noop.py`.
- [ ] ADR-022 no longer implies `run_id` is a Prometheus label.
- [ ] Architecture and observability contract pages no longer contradict each other on this point.

## Validation

```bash
rg -n "ADR-044|ADR-047|domain/ports/noop\\.py|run-id|run_id" \
  docs/02-architecture docs/03-guides/dashboards docs/04-reference/contracts
```

## Non-Goals

- changing runtime observability implementation
- changing dashboard queries or Prometheus rules
- rewriting unrelated ADRs

