# Docker Helper Root Relocation Audit

Status: implemented for post-2026-07 candidate adjuncts and RF-003 root setup
helper retirement. Required root compose entrypoints remain at root; optional
helper adjuncts and setup helpers are owned by scripts paths.

**RH-04 / #6704 (2026-07-27) decision:** keep `docker-compose.neo4j.yml` and
`docker-compose.neo4j-audit.yml` at exact root for now. Live consumers include
`configs/quality/docker_runtime_contracts.yaml` and architecture contract tests.
Rehome only after a dedicated repoint PR updates contracts, docs, and launchers.

This audit closes the "review before move" requirement for the reviewed root
Docker helper family. It complements
`configs/quality/docker_helper_contracts.yaml` and the
`BIOETL_DOCKER_HELPER_ADR010_ADJUNCT` governance anchor.

## Scope

Reviewed root Docker helper surfaces:

- `docker-compose*.yml`
- `docker-setup.ps1`
- `docker-setup.sh`
- `Dockerfile.*`
- `grafana-datasource.yml`

## Relocation Matrix

| Surface | Current role | Primary consumers | Current decision | Future target if rehomed |
| --- | --- | --- | --- | --- |
| `docker-compose.yml` | default local stack entrypoint | operator docs, manual `docker compose up -d` flows | `must_stay_root_for_now` | keep exact filename unless a root shim is added |
| `docker-compose.monitoring.yml` | reviewed monitoring stack entrypoint | `docs/DOCKER_SETUP.md`, `docs/DOCKER_QUICKSTART.md`, operator flows | `must_stay_root_for_now` | `docker/compose/monitoring.yml` behind a root shim only |
| `docker-compose.neo4j.yml` | reviewed Neo4j helper stack | ops docs, manual audit flows | `must_stay_root_for_now` | `docker/compose/neo4j.yml` behind a root shim only |
| `docker-compose.neo4j-audit.yml` | reviewed audit helper stack | audit docs and operator flows | `must_stay_root_for_now` | `docker/compose/neo4j-audit.yml` behind a root shim only |
| `docker-compose.alertmanager.yml` | optional ADR-010 adjunct helper | `configs/quality/docker_helper_contracts.yaml`, Docker docs | `rehomed_2026_07` | `scripts/ops/runtime/docker/compose/alertmanager.yml` |
| `docker-compose.minio.yml` | optional ADR-010 adjunct helper | contract file, Docker docs, local operator flows | `rehomed_2026_07` | `scripts/ops/runtime/docker/compose/minio.yml` |
| `docker-compose.redis.yml` | optional ADR-010 adjunct helper | contract file, Makefile, Docker docs | `rehomed_2026_07` | `scripts/ops/runtime/docker/compose/redis.yml` |
| `docker-compose.sonarqube.yml` | optional ADR-010 adjunct helper | contract file, Docker docs | `rehomed_2026_07` | `scripts/ops/runtime/docker/compose/sonarqube.yml` |
| `docker-setup.ps1` | retired root Windows bootstrap helper | legacy operator docs, launcher instructions | `retired_root_script_2026_07_10` | `scripts/ops/docker-setup.ps1` command-compatible helper |
| `docker-setup.sh` | retired root Bash bootstrap helper | legacy operator docs, launcher instructions | `retired_root_script_2026_07_10` | `scripts/ops/docker-setup.sh` command-compatible helper |
| `Dockerfile.bioetl` | main local image build surface | manual builds, compose context assumptions | `must_stay_root_for_now` | `docker/images/bioetl/Dockerfile` only with compose/build refactor |
| `docker-compose.codex.yml`, `Dockerfile.mcp-*` | retired persistent MCP surface | on-demand MCP manifests/wrappers | `retired_rf002` | do not restore |
| `Dockerfile.warp` | retired privileged helper | none | `retired_rf004` | do not restore |
| `grafana-datasource.yml` | provisioning sidecar artifact | Grafana provisioning / compose mount assumptions | `rehomed_2026_07` | `grafana/provisioning/datasources-local/grafana-datasource.yml` |

## Reference Map Verification

Last verified: 2026-07-27 for root hygiene issues #5995 and #6725. The live
consumer map below was rechecked after the RH-04 decision.

Current root Docker entrypoints remain root-retained because live repository
consumers still use exact root filenames:

| Root surface | Current consumers | Move condition |
| --- | --- | --- |
| `Dockerfile.bioetl` | `.github/workflows/docker.yml`, `Makefile`, manual image build flows | Move only after Docker workflow build inputs and local build commands are repointed or wrapped. |
| `docker-compose.yml` | `.github/workflows/docker.yml`, `.github/workflows/tests.yml`, `Makefile`, `scripts/startup.*`, `scripts/shutdown.*`, operator docs | Move only behind a root-compatible shim or after every default `docker compose` flow is repointed. |
| `docker-compose.monitoring.yml` | `.github/workflows/docker.yml`, `.github/workflows/tests.yml`, `Makefile`, `docs/DOCKER_SETUP.md`, `docs/DOCKER_QUICKSTART.md`, ops helpers | Move only after monitoring workflow and docs references use the new path or a shim. |
| `docker-compose.neo4j.yml` | `Makefile`, Neo4j ops docs, local audit flows | Move only after Neo4j helper commands and docs are repointed. |
| `docker-compose.neo4j-audit.yml` | Neo4j audit launchers and audit docs | Move only after audit launchers and docs are repointed. |
| `docker-setup.ps1` | retired root script; command parity retained in `scripts/ops/docker-setup.ps1` | Do not restore the root filename. |
| `docker-setup.sh` | retired root script; command parity retained in `scripts/ops/docker-setup.sh` | Do not restore the root filename. |

Root minimization for Docker setup helpers is no longer blocked on the root
script filenames: legacy verbs are retained by `scripts/ops/docker-setup.ps1`
and `scripts/ops/docker-setup.sh`. Future moves for compose files or
`Dockerfile.bioetl` remain blocked on exact-root tool contracts and must update
workflows, `Makefile`, operator docs, root allowlist, and
`configs/quality/docker_helper_contracts.yaml` together.

## RF-003 Command Compatibility Matrix

| Legacy root verb | Scripts-owned Bash command | Scripts-owned PowerShell command | Parity decision |
| --- | --- | --- | --- |
| `check` | `scripts/ops/docker-setup.sh check` | `.\scripts\ops\docker-setup.ps1 check` | retained non-mutating Docker/Compose check |
| `build` | `scripts/ops/docker-setup.sh build` | `.\scripts\ops\docker-setup.ps1 build` | retained `bioetl:latest` build from `Dockerfile.bioetl` |
| `start` | `scripts/ops/docker-setup.sh start` | `.\scripts\ops\docker-setup.ps1 start` | retained main stack start plus health check |
| `start-full` | `scripts/ops/docker-setup.sh start-full` | `.\scripts\ops\docker-setup.ps1 start-full` | retained image build, full helper stack start, and health check |
| `stop` | `scripts/ops/docker-setup.sh stop` | `.\scripts\ops\docker-setup.ps1 stop` | retained main stack stop |
| `stop-full` | `scripts/ops/docker-setup.sh stop-full` | `.\scripts\ops\docker-setup.ps1 stop-full` | retained main plus helper stack stop |
| `logs [service]` | `scripts/ops/docker-setup.sh logs [service]` | `.\scripts\ops\docker-setup.ps1 logs [service]` | retained compose log tailing |
| `health` | `scripts/ops/docker-setup.sh health` | `.\scripts\ops\docker-setup.ps1 health` | retained compose status plus readiness probe |
| `clean` | `scripts/ops/docker-setup.sh clean` | `.\scripts\ops\docker-setup.ps1 clean` | retained destructive cleanup wording and behavior |

## Constraints

- ADR-010 remains authoritative: helper stacks are optional local-only adjuncts.
- `configs/quality/docker_helper_contracts.yaml` is the machine-readable
  contract for the optional adjunct compose files.
- Optional helper root relocation is complete for the candidate adjuncts listed
  as `rehomed_2026_07`; restoring any legacy root filename requires fresh owner
  review and root allowlist updates.
- No helper relocation should broaden runtime requirements for BioETL itself.

## Validation Required Before Any Future Move

1. Update all doc, workflow, Makefile, and launcher references.
1. Keep `configs/quality/docker_helper_contracts.yaml` aligned with the new
   filenames or shim surface.
1. Re-run:

```bash
python3 -m pytest \
  tests/architecture/test_docs_root_surface_governance_alignment.py \
  tests/architecture/test_root_script_wrapper_surfaces.py -q
python3 scripts/engineering/repo/check_root_governance_docs.py
python3 scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
```

## Decision

Audit complete. Required root compose entrypoints remain deferred. Candidate
optional adjuncts were rehomed under existing owned trees without adding a new
root directory.
