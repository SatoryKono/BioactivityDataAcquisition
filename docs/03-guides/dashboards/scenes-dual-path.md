# Optional Scenes dual path

BioETL has one authoritative dashboard data surface and two presentation
paths:

1. Seven provisioned JSON dashboards under `grafana/dashboards/` — production
   fallback and rollback source of truth.
2. Optional `bioetl-scenes-app` — read-only shadow presentation adapter with
   six task-oriented routes.

The app is not required by BioETL core, is not enabled by default, and owns no
metric, query backend, incident record, or control-plane write.

## Route mapping

| App route | JSON fallback |
| --- | --- |
| Operations Home | `bioetl-overview-v2` |
| Pipeline Flow | `bioetl-runtime` |
| Dependency Health | `bioetl-provider-health-v2` |
| Incident Console | `bioetl-incident-v1` |
| Data Trust & Recovery | `bioetl-control-plane-v1`, `bioetl-dq-v2` |
| Run Explorer | `bioetl-run-explorer-v1` |

Route context is allow-listed and preserves workflow, pipeline, time, relevant
run/provider/stage/reason selection, evidence basis, and origin. Unknown query
keys are discarded. Prometheus queries never receive `run_id`.

## Install for shadow review

```bash
cd grafana/plugins/bioetl-scenes-app
npm ci
npm run typecheck
npm run test:ci
npm run build
```

Install or mount the resulting `dist/` using the operator's local Grafana plugin
policy, then enable `bioetl-scenes-app` for the review organization. Default
monitoring provisioning intentionally does neither.

## Disable and rollback

Disable or remove `bioetl-scenes-app`. Keep the existing dashboard provisioner
unchanged. All seven JSON UIDs remain reachable and no data migration or
service restart in BioETL core is required.

UID retirement is explicitly outside this delivery. It requires a separate
decision, usage evidence, zero functional loss, and redirects or tombstones for
at least one release.
