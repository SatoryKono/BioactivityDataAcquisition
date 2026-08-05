______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-05'

______________________________________________________________________

# Monitoring surface reduction (2026-07-23)

## Trigger

Use this runbook when validating, operating, or changing the reduced optional
monitoring stack introduced on 2026-07-23.

## Impact

Starting retired services or treating monitoring as a mandatory runtime would
violate the Local-Only deployment contract. Removing the retained quarantine
storage domain would cause data-loss and replay regressions.

## Preconditions

- Confirm ADR-010 and the current optional-monitoring inventory.
- Distinguish retired UI/telemetry helpers from retained domain quarantine
  write/storage and operator CLI commands.
- Obtain explicit approval before any destructive volume operation.

## Procedure

Apply the decision and operator commands below. Keep the default runtime on the
main health/metrics surface and start monitoring only when explicitly needed.

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
The Windows compatibility launcher
`scripts/ops/observability/grafana/start_quarantine_explorer.ps1` delegates to
that stub and must not start a replacement backend.

### CLI alignment (follow-up)

- `--ensure-observability-backend` defaults to **off**
- default health / Ops HTTP port is **8000** (`DEFAULT_HEALTH_SERVER_PORT`)
- when ensure is explicitly enabled, CLI starts **`bioetl health server`**, not
  `quarantine serve`
- Grafana audit cycle defaults match: no auto-ensure; app base URL `:8000`

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

## Verification

- Confirm the default start path does not launch Prometheus, Grafana, Loki,
  Tempo, or Quarantine Explorer.
- Confirm the explicit monitoring command starts only the retained optional
  metrics stack.
- Confirm quarantine `inspect`, `replay`, and `purge` remain available without
  a replacement web UI.

## Rollback/Recovery

- Revert an unintended monitoring configuration change through the normal PR
  path; do not resurrect retired Loki, Tempo, or Quarantine Explorer services.
- Preserve legacy volumes until an operator explicitly approves their removal.

## Compliance

- ADR-010 Local-Only deployment remains authoritative.
- Monitoring is optional; quarantine payload immutability and CLI operations
  remain mandatory.
- Do not add Docker or external orchestration requirements to the default path.

## Post-incident

Record which surface was inspected, the commands run, whether any legacy
volume remains, and any follow-up needed to remove stale operator wording.
