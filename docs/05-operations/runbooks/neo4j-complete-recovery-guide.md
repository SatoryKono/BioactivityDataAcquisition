______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: Informational
  Last verified: '2026-04-12'

______________________________________________________________________

# Neo4j MCP Backend - Recovery Guide

## Trigger

- MCP-backed Neo4j workflows fail because the backend is unhealthy, unreachable, or not fully ready.
- Use this runbook when Docker Desktop + WSL connectivity appears correct but driver or HTTP readiness checks remain unstable.

## Impact

- Neo4j-backed memory and audit tooling remain unavailable until backend readiness is restored.
- MCP wrappers may appear healthy while all real graph operations continue to fail.

## Preconditions

- Access to Docker Desktop on Windows and the shared repository checkout.
- Permission to restart Docker Desktop and recreate the local Neo4j container.
- This runbook is for auxiliary Neo4j/MCP tooling only; it does not change the BioETL runtime ADR-010 Local-Only posture.

## Problem Summary

The MCP layer is configured correctly, but the Neo4j backend has shown intermittent startup and runtime instability in Docker Desktop + WSL.

Confirmed facts:

- MCP wrapper and registration are correct
- `.env.local` is synchronized for WSL usage
- Windows and WSL can often reach the published ports
- driver-level operations still fail when Neo4j is not actually ready

This guide focuses on backend recovery, not MCP reconfiguration.

## Procedure

### Recommended Recovery Flow

### 1. Restart Docker Desktop

PowerShell:

```powershell
.\scripts\ops\runtime\docker\restart-docker.ps1
```

Or manually:

1. Quit Docker Desktop
1. Wait 10 seconds
1. Relaunch Docker Desktop
1. Wait 60 seconds

### 2. Start Neo4j 5.13

Preferred:

```powershell
docker compose -f docker-compose.neo4j.yml up -d
Start-Sleep -Seconds 60
```

Alternative:

```powershell
docker rm -f bioetl-neo4j
docker run -d --name bioetl-neo4j `
  -p 7474:7474 -p 7687:7687 `
  -e "NEO4J_AUTH=neo4j/bioetl_secure_password" `
  -e "NEO4J_ACCEPT_LICENSE_AGREEMENT=yes" `
  -e "NEO4J_server_memory_heap_initial__size=256m" `
  -e "NEO4J_server_memory_heap_max__size=512m" `
  -e "NEO4J_server_memory_pagecache_size=128m" `
  neo4j:5.13-community

Start-Sleep -Seconds 60
```

### 3. Validate backend from Windows

```powershell
docker ps --filter "name=bioetl-neo4j"
docker logs bioetl-neo4j | Select-Object -Last 30
curl.exe http://localhost:7474/
node test_neo4j_connection.js
```

Expected:

- container is `Up`
- logs show normal startup progress
- HTTP returns `200` or `302`
- `test_neo4j_connection.js` prints `Connection successful`

### 4. Validate backend from WSL

```bash
bash scripts/memory/setup/wsl_startup.sh
```

This maintained script:

- uses `docker.exe`
- tests `host.docker.internal`
- runs the repo-root connection test

### 5. Seed project memory

Once connectivity is stable:

```bash
node seed_test_docs_memory.js
node query_test_docs_memory.js
```

## Verification

- `docker ps` shows `bioetl-neo4j` as `Up`
- `curl http://localhost:7474/` returns `200` or `302`
- `node test_neo4j_connection.js` succeeds
- `bash scripts/memory/setup/wsl_startup.sh` succeeds
- `node seed_test_docs_memory.js` succeeds
- `node query_test_docs_memory.js` returns counts greater than zero

## Recovery

- If the recreated container remains unstable, stop seed/query operations and revert to the last known working local Docker Desktop state before reattempting MCP usage.
- If WSL validation fails while Windows validation passes, keep the backend stopped for MCP operations and return to `bash scripts/memory/setup/wsl_startup.sh` diagnostics before additional config changes.

## Post-incident

- Capture the failing Docker logs, readiness checks, and which recovery step restored stability.
- Update this runbook or the related setup guides if the restored path differs from the documented maintained flow.

## Maintained Files

| File                                            | Purpose                                                    |
| ----------------------------------------------- | ---------------------------------------------------------- |
| `docker-compose.neo4j.yml`                      | Docker Compose service for Neo4j 5.13                      |
| `test_neo4j_connection.js`                      | Driver-level connectivity test using the active URI        |
| `test_neo4j_localhost.js`                       | Localhost-specific connectivity test                       |
| `seed_test_docs_memory.js`                      | Seed block for test strategy + docs source-of-truth memory |
| `query_test_docs_memory.js`                     | Retrieval check for seeded test/docs memory                |
| `scripts/ops/runtime/docker/restart-docker.ps1` | Docker Desktop restart helper                              |
| `scripts/memory/setup/wsl_startup.sh`           | WSL-aware setup and validation path                        |

## Troubleshooting

### Container exits immediately

```powershell
docker logs bioetl-neo4j
```

Check for:

- invalid env vars
- memory issues
- port conflicts

### HTTP responds inconsistently

If `curl http://localhost:7474/` sometimes works and sometimes hangs, treat the backend as unstable. Do not run seed/query scripts until HTTP and driver checks pass consistently.

### Driver times out

If `node test_neo4j_connection.js` times out:

- backend is still not truly ready
- or Bolt path is unstable even though TCP is open

This is not enough to declare the integration healthy.

### WSL path fails while Windows works

Run:

```bash
bash scripts/memory/setup/wsl_startup.sh
```

and verify that:

- `host.docker.internal` resolves
- HTTP works from WSL
- the repo-root Node test can connect

## What Not To Assume

- Open TCP ports do not prove Neo4j readiness.
- TLS is not yet proven as the primary root cause.
- `/tmp` scripts are not the maintained execution path anymore.

## MCP Status

Once the backend is stable:

- `neo4j-memory` MCP is already configured
- no further MCP-layer changes are needed
- Codex usage can start immediately

## Compliance

- Use this guide only for local Neo4j/MCP auxiliary tooling, not as runtime deployment guidance for BioETL.
- Preserve the validation evidence from both Windows and WSL before declaring the backend recovered.
