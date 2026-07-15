# Docker Compose project migration

This runbook applies only to the optional local Docker helpers permitted by
ADR-010. The canonical BioETL runtime remains the Python/venv flow.

## Ownership contract

Run the read-only gate before any start, stop, or migration operation:

```bash
python scripts/ops/runtime/docker/docker_runtime_preflight.py
```

The machine-readable source is
`configs/quality/docker_runtime_contracts.yaml`.

| Compose file | Project | Single-owner services |
|---|---|---|
| `docker-compose.yml` | `bioetl-main` | `bioetl`; `warp` is opt-in via profile `warp` |
| `docker-compose.monitoring.yml` | `bioetl-monitoring` | monitoring, logging, tracing, renderer |
| `docker-compose.neo4j.yml` | `bioetl-neo4j` | `neo4j` |
| `docker-compose.neo4j-audit.yml` | `bioetl-neo4j-audit` | `neo4j-audit` |
| `docker-compose.codex.yml` | `bioetl-codex` | retired legacy MCP helpers; use canonical on-demand wrappers |

Never combine these files into one Compose invocation. Normal stop commands
MUST NOT use `--volumes`; volume removal is a separate, explicit data-retention
decision.

Do not start the retired `bioetl-codex` project. The file remains as a bounded
migration/reference surface only. `mcp-filesystem` mounts a repository at
`/workspace`, never over image-owned `/app`, so an accidental render cannot
hide image-installed `node_modules`.

The shared networks are external infrastructure with stable literal names:

| Logical network | External name | Consumers | Owner |
|---|---|---|---|
| `monitoring` | `bioetl-monitoring` | `bioetl-main`, `bioetl-monitoring` | `scripts/ops/docker-setup` |
| `warp-network` | `warp-network` | `bioetl-main`, `bioetl-neo4j`, `bioetl-codex` | `scripts/ops/docker-setup` |

Create or verify these networks through `scripts/ops/docker-setup.sh` or
`scripts/ops/docker-setup.ps1` before starting a consumer. The former
project-local network `bioetl-main_warp-network` carries no persistent data and
MUST NOT be reused; after all legacy consumers are stopped it may be removed
only as a separate, explicit cleanup operation.

## One-time project and volume map

The legacy project was `bioactivitydataacquisition2`. Project-owned volumes
must be migrated explicitly:

| Legacy volume | New volume |
|---|---|
| `bioactivitydataacquisition2_neo4j_data` | `bioetl-neo4j_neo4j_data` |
| `bioactivitydataacquisition2_neo4j_logs` | `bioetl-neo4j_neo4j_logs` |
| `bioactivitydataacquisition2_warp-data` | `bioetl-main_warp-data` |
| `bioactivitydataacquisition2_prometheus-data` | `bioetl-monitoring_prometheus-data` |
| `bioactivitydataacquisition2_grafana-data` | `bioetl-monitoring_grafana-data` |
| `bioactivitydataacquisition2_loki-data` | `bioetl-monitoring_loki-data` |
| `bioactivitydataacquisition2_tempo-data` | `bioetl-monitoring_tempo-data` |
| `bioactivitydataacquisition2_mcp-fetch-cache` | `bioetl-codex_mcp-fetch-cache` |

Do not remove a legacy volume until the corresponding new project has passed
its readiness check and the backup has been retained.

## Windows/WSL repository origin

For Docker Desktop under WSL, run the Compose projects from a Linux-filesystem
runtime mirror such as
`~/.local/share/bioetl-runtime/BioactivityDataAcquisition2`. A project whose
working directory or bind sources resolve through `/mnt/c`, `/mnt/d`, or
`/mnt/e` fails the runtime preflight. Keep the source checkout authoritative,
but synchronize the runtime mirror before a Compose mutation and verify
`com.docker.compose.project.working_dir` after it.

The mirror must contain the same `src`, `configs`, `data`, `logs`, `reports`,
Grafana provisioning, and Compose files needed by the selected services. A
partial data copy can make exact RunManifest identity work while leaving other
HTTP panels unavailable, so the live panel audit remains mandatory.

Pass required values through the process or an explicitly named local
`--env-file`; never create or rewrite a repository `.env` as part of cutover.

## Mandatory Neo4j backup/restore drill

Perform this drill before migrating a workstation that has an existing legacy
Neo4j volume. It does not modify or remove the source volume.

1. Stop only the legacy Neo4j service and record the source volume identity.
1. Mount `bioactivitydataacquisition2_neo4j_data` read-only in a disposable
   utility container and create a timestamped archive under an operator-chosen
   backup directory outside the volume.
1. Restore that archive into a newly created, disposable drill volume.
1. Compare a sorted SHA-256 manifest of every regular file in the read-only
   source with the restored drill volume.
1. Launch Neo4j from the drill volume under project
   `bioetl-neo4j-restore-drill`, with a unique container name and alternate
   localhost ports. Wait for its configured health check to become `healthy`.
1. Record the archive hash, source/restored manifest hashes, image digest,
   health result, start/end timestamps, and operator in
   `reports/quality/docker-neo4j-migration-drill.json`.
1. Stop the drill project without `--volumes`. Remove its disposable volume
   only after the evidence file and archive have been verified.

If the Docker daemon or legacy volume is absent, record the drill as
`not_applicable_no_legacy_volume`; do not claim a successful restore. A real
legacy volume must never be cut over on static evidence alone.

## Cutover

After a successful drill, create the target volume, restore the verified
archive, verify both external networks, and start only:

```bash
docker network inspect warp-network
docker network inspect bioetl-monitoring
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml up -d
docker compose -p bioetl-neo4j -f docker-compose.neo4j.yml ps
```

Use the project-specific commands from the table for every other stack. To
roll back, stop the new project without `--volumes` and restart the legacy
project against the untouched legacy volume.

For the main and monitoring cutover, start only the canonical projects and
wait for readiness:

```bash
docker compose -p bioetl-main -f docker-compose.yml up -d --wait bioetl
docker compose -p bioetl-monitoring -f docker-compose.monitoring.yml \
  --profile tracing up -d --wait \
  prometheus pushgateway loki promtail tempo renderer grafana
```

Grafana 12 uses `GF_PLUGINS_PREINSTALL` only. Do not also set legacy
`GF_INSTALL_PLUGINS`: the duplicate CLI installer delays readiness and can
restart the container while a restored plugin volume is being inspected.

Before promotion, require all of the following:

1. Runtime preflight reports zero errors and warnings from the Linux origin.
1. Host and Grafana-network fixed-time Prometheus queries return identical
   payloads.
1. A live panel audit resolves a concrete Run ID and Manifest ID and returns
   numeric Processed Records, including legitimate zero-valued rows.
1. Ten full stop/start cycles preserve volume mountpoints with restart delta,
   OOM kills, and unresolved unhealthy states all equal to zero.
1. The same invariants remain clean for the full 24-hour observation window.

Retain the verified backups and all legacy source volumes throughout the
observation. If a stateful canary fails, restore only the affected target
volume from its verified backup; do not prune or delete the legacy source.
