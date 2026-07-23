# Monitoring surface reduction (2026-07-23)

## Decision

Default BioETL Docker surface no longer includes:

| Removed | Kind |
| --- | --- |
| Loki | container + config + Grafana datasource |
| Promtail | container + config |
| Tempo | container + config + Grafana datasource |
| Quarantine Explorer | `bioetl quarantine serve` in main compose, Infinity datasource, Silver Reject Explorer dashboard, Prometheus scrape job |

Domain Medallion **quarantine write/storage** in `src/bioetl` is **retained**.

## Default vs opt-in

| Stack | Default |
| --- | --- |
| main (`:8000` health) | Yes (if Docker used) |
| monitoring (Prom/Grafana/renderer) | Opt-in only |
| neo4j / redis / minio | Helpers only |

## Operator commands

```bash
# default
python scripts/ops/runtime/docker/runtime_manager.py start --stack main

# opt-in Grafana
python scripts/ops/runtime/docker/runtime_manager.py start --stack monitoring

# stop monitoring without volume wipe
python scripts/ops/runtime/docker/runtime_manager.py stop --stack monitoring
```

## Residual volumes

Legacy volumes `*-loki-data` / `*-tempo-data` may still exist on disk. Do **not**
`down -v` unless explicitly approved. They are unused after this change.
