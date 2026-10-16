---
title: "docs(observability): refresh Grafana provisioning path docs to the current split datasource layout"
labels: documentation, observability, enhancement
assignees: []
---

## Context

The 2026-06-19 documentation audit found a concrete operator-facing drift in
Grafana setup docs: multiple published pages still reference provisioning paths
that no longer exist in the repository.

## Problem

Published observability/dashboard docs still point to legacy paths such as:

- `grafana/provisioning/dashboards/bioetl.yml`
- `grafana/provisioning/datasources/prometheus.yml`
- `grafana/provisioning/datasources/loki.yml`
- `grafana/provisioning/datasources/tempo.yml`
- `grafana/provisioning/datasources/quarantine-explorer.yml`

The actual shipped layout is:

- `grafana/provisioning/dashboards/bioetl.yaml`
- `grafana/provisioning/datasources-core/prometheus.yml`
- `grafana/provisioning/datasources-core/quarantine-explorer.yml`
- `grafana/provisioning/datasources-tracing/loki.yml`
- `grafana/provisioning/datasources-tracing/tempo.yml`

This can send operators to non-existent files during dashboard review or stack
bootstrap.

## Evidence

- `docs/03-guides/dashboard-guide.md:39-43`
- `docs/02-architecture/current-state-inventory.md:214`
- `grafana/README.md:424`
- `grafana/provisioning/dashboards/bioetl.yaml`
- `grafana/provisioning/datasources-core/prometheus.yml`
- `grafana/provisioning/datasources-core/quarantine-explorer.yml`
- `grafana/provisioning/datasources-tracing/loki.yml`
- `grafana/provisioning/datasources-tracing/tempo.yml`

## Proposed Solution

1. Update all published provisioning-path references to the current split
   layout.
2. Normalize `bioetl.yml` -> `bioetl.yaml`.
3. Reconcile top-level guides with `grafana/README.md` so setup guidance and
   detailed reference pages do not disagree.
4. Keep archive-only/planning docs out of scope unless they are still linked as
   active guidance.

## Acceptance Criteria

- [ ] Active docs no longer reference `grafana/provisioning/datasources/*.yml` as the canonical shipped layout.
- [ ] Active docs use `grafana/provisioning/dashboards/bioetl.yaml`.
- [ ] Active docs point to `datasources-core/` and `datasources-tracing/` correctly.
- [ ] Repo search finds legacy paths only in archive/planning surfaces or intentional historical notes.

## Validation

```bash
rg -n "grafana/provisioning/datasources/|grafana/provisioning/dashboards/bioetl\\.yml" \
  docs README.md grafana/README.md
find grafana/provisioning -maxdepth 3 -type f | sort
```

## Non-Goals

- changing Grafana JSON dashboards
- changing datasource UIDs or runtime behavior
- refactoring observability code

