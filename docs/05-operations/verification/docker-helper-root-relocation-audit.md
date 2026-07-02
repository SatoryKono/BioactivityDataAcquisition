# Docker Helper Root Relocation Audit

Status: audit-only. No relocation is approved by this document.

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
| `docker-compose.codex.yml` | Codex MCP adjunct stack | Codex setup docs, startup scripts | `must_stay_root_for_now` | `docker/compose/codex.yml` behind a root shim only |
| `docker-compose.alertmanager.yml` | optional ADR-010 adjunct helper | `configs/quality/docker_helper_contracts.yaml`, Docker docs | `candidate_rehome_after_shim` | `docker/helpers/alertmanager.compose.yml` |
| `docker-compose.minio.yml` | optional ADR-010 adjunct helper | contract file, Docker docs, local operator flows | `candidate_rehome_after_shim` | `docker/helpers/minio.compose.yml` |
| `docker-compose.redis.yml` | optional ADR-010 adjunct helper | contract file, Makefile, Docker docs | `candidate_rehome_after_shim` | `docker/helpers/redis.compose.yml` |
| `docker-compose.sonarqube.yml` | optional ADR-010 adjunct helper | contract file, Docker docs | `candidate_rehome_after_shim` | `docker/helpers/sonarqube.compose.yml` |
| `docker-setup.ps1` | reviewed Windows bootstrap helper | operator docs, launcher instructions | `must_stay_root_for_now` | `scripts/ops/runtime/docker/docker-setup.ps1` behind a root shim |
| `docker-setup.sh` | reviewed Bash bootstrap helper | operator docs, launcher instructions | `must_stay_root_for_now` | `scripts/ops/runtime/docker/docker-setup.sh` behind a root shim |
| `Dockerfile.bioetl` | main local image build surface | manual builds, compose context assumptions | `must_stay_root_for_now` | `docker/images/bioetl/Dockerfile` only with compose/build refactor |
| `Dockerfile.mcp-fetch` | Codex/MCP helper build surface | `docker-compose.codex.yml` | `candidate_rehome_after_compose_refactor` | `docker/images/mcp-fetch/Dockerfile` |
| `Dockerfile.mcp-filesystem` | Codex/MCP helper build surface | `docker-compose.codex.yml` | `candidate_rehome_after_compose_refactor` | `docker/images/mcp-filesystem/Dockerfile` |
| `Dockerfile.mcp-github` | Codex/MCP helper build surface | `docker-compose.codex.yml` | `candidate_rehome_after_compose_refactor` | `docker/images/mcp-github/Dockerfile` |
| `Dockerfile.mcp-memory` | Codex/MCP helper build surface | `docker-compose.codex.yml` | `candidate_rehome_after_compose_refactor` | `docker/images/mcp-memory/Dockerfile` |
| `Dockerfile.warp` | reviewed network/tooling helper image | Docker docs, local operator flows | `candidate_rehome_after_compose_refactor` | `docker/images/warp/Dockerfile` |
| `grafana-datasource.yml` | provisioning sidecar artifact | Grafana provisioning / compose mount assumptions | `candidate_rehome_after_mount_refactor` | `grafana/provisioning/datasources/datasource.yml` |

## Constraints

- ADR-010 remains authoritative: helper stacks are optional local-only adjuncts.
- `configs/quality/docker_helper_contracts.yaml` is the machine-readable
  contract for the optional adjunct compose files.
- Root relocation is blocked until the exact root filenames are replaced by
  stable shims or every documented/manual invocation is updated in one reviewed
  change.
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

Audit complete. Root relocation remains deferred. The approved next move is a
shim-first migration, not a direct path rename.
