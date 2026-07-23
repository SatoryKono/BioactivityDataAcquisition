# Monitoring surface reduction (2026-07-23)

## Decision

Strategy **A (soft only)** for the overall monitoring stack: Prometheus /
Pushgateway / Grafana / image-renderer remain as an **opt-in** local adjunct
(ADR-010), not part of the default release path.

**Hard-removed** from shipping Docker/UI surface:

| Removed | Kind |
| --- | --- |
| Loki | container + config + Grafana datasource |
| Promtail | container + config |
| Tempo | container + config + Grafana datasource |
| Quarantine Explorer | `bioetl quarantine serve` in default main compose, Infinity “Quarantine Explorer” datasource, Silver Reject Explorer dashboard, Prometheus scrape job `quarantine-explorer` |

Domain Medallion **quarantine write/storage** in `src/bioetl` is **retained**.
CLI helpers `bioetl quarantine inspect|replay|purge` remain for operators.

## Default vs opt-in

| Stack | Default |
| --- | --- |
| main (`:8000` health/metrics only) | Yes (if Docker used) |
| monitoring (Prom/Pushgateway/Grafana/renderer) | **Opt-in only** |
| neo4j / redis / minio | Helpers only |

`make docker-start-full` does **not** start monitoring.
Use `make docker-start-monitoring` explicitly.

## Operator commands

```bash
# default
python scripts/ops/runtime/docker/runtime_manager.py start --stack main

# opt-in Grafana/Prom
python scripts/ops/runtime/docker/runtime_manager.py start --stack monitoring
# or
make docker-start-monitoring

# stop monitoring without volume wipe
python scripts/ops/runtime/docker/runtime_manager.py stop --stack monitoring
```

## Identity HTTP after Quarantine Explorer removal

Shipped dashboards that need control-plane identity helpers use the Infinity
datasource **BioETL Ops HTTP** (`uid: bioetl-ops-http`) pointing at the main
health server:

`http://bioetl:8000` (env override: `BIOETL_OPS_HTTP_URL`).

Endpoints live on `bioetl health server` (`/ops/control-plane/*`).
The old Quarantine Explorer port `:8081` is not published by default.

`python -m scripts.ops ensure-quarantine-explorer` is a fail-closed stub (exit 2).

## Residual volumes

Legacy volumes `*-loki-data` / `*-tempo-data` may still exist on disk. Do **not**
`down -v` unless explicitly approved. They are unused after this change.

## Docs updated with this program

Operator/reference surfaces aligned to the reduced stack:

- `docs/DOCKER_QUICKSTART.md`, `docs/DOCKER_SETUP.md`
- `docs/03-guides/dashboards/*` (inventory, monitoring-index, navigation, v2 usage)
- `docs/03-guides/dashboard-guide.md`, `docs/03-guides/running-pipelines.md`
- `docs/04-reference/cli.md`
- `docs/05-operations/01-monitoring-guide.md`, `runbooks/quarantine-management.md`,
  `runbooks/observability-checklist.md`, `sli-slo-baseline.md`
- `docs/security/rbac-matrix.md`
- `grafana/README.md` (header + shipping inventory)
- `configs/quality/observability_slo_alert_contract.yaml`

Historical panel guide `docs/03-guides/dashboards/panels/bioetl-silver-reject-explorer-panels.md`
is marked **REMOVED** and points operators to CLI inspect.
