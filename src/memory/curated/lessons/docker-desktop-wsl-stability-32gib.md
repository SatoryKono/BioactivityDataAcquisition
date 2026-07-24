______________________________________________________________________

id: docker-desktop-wsl-stability-32gib
title: Docker Desktop / WSL stability on 32 GiB Windows hosts
kind: lesson
source_refs:

- docs/DOCKER_QUICKSTART.md
- docs/DOCKER_SETUP.md
- scripts/ops/runtime/docker/ensure-stable.ps1
- configs/quality/docker_helper_contracts.yaml
- ADR-010 Local-Only deployment
  confidence: curated
  last_verified: '2026-07-24T00:00:00Z'
  summary: Prefer ensure-stable, modest WSL memory, no-build main-only stacks; thrash and high WSL caps kill the engine pipe.

______________________________________________________________________

# Lesson

## Observation

- On 32 GiB Windows hosts, Docker engine “deaths” almost always present as
  missing `npipe:////./pipe/dockerDesktopLinuxEngine` while
  `docker-desktop` WSL is **Stopped**. Root cause is host free-RAM collapse,
  not a broken compose file.
- High WSL caps (`memory=16GB`) plus PyCharm + multi-stack `compose --build` /
  `--force-recreate` thrash reliably kill Desktop under ~3–4 GiB free host RAM.
- BioETL Docker remains ADR-010 optional adjunct: default surface is **main**
  health server (`:8000`); monitoring is opt-in; Loki/Tempo/Quarantine Explorer
  UI are removed from shipping compose.
- PowerShell wrappers must not use parameter name `$Args` (automatic variable);
  it silently empties docker CLI args.

## Reuse guidance

- Prefer:
  `.\scripts\ops\runtime\docker\ensure-stable.ps1 -WithNeo4j`
  and after flap:
  `.\scripts\ops\runtime\docker\ensure-stable.ps1 -RestartWsl -WithNeo4j`
- One-time per machine:
  `.\scripts\ops\runtime\docker\harden-desktop-host.ps1 -RegisterWatchdog`
  (Resource Saver effectively off, AutoStart, no Extensions/AI; Task Scheduler
  watchdog every 5 min → soft/hard ensure, rate-limited).
- MCP thrash: duplicate `mcp/*` containers come from stdio MCP clients, not
  BioETL compose. Apply
  `.\scripts\ops\runtime\docker\apply-docker-stable-mcp.ps1 -Profile stable`
  and/or `cleanup-mcp-orphans.ps1`; local `setup_mcp.py --profile stable|core`
  (default generator profile is `core`).
- Operator host defaults for this class: WSL `memory=6GB`, free host RAM ≥4 GiB,
  main mem_limit 768 m, neo4j mem_limit 768 m / heap max 384 m.
- Start **one** stack at a time; use project flags
  `-p bioetl-main` / `-p bioetl-neo4j` / `-p bioetl-monitoring`.
- Never recover with `down -v`, volume prune, or VHDX deletion.
- Stop foreign non-`bioetl-*` containers when reclaiming RAM.
- Canonical lifecycle manager remains
  `python scripts/ops/runtime/docker/runtime_manager.py ...`.
