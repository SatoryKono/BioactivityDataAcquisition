# Neo4j Backend Connectivity Resolution - Action Plan

## Current Situation

**Status**: Neo4j backend intermittently unstable in Docker Desktop + WSL.

**What is already correct**:
- MCP package, wrapper, and Codex registration
- `.env.local` synchronization for `NEO4J_URI`, credentials, and WSL pathing
- WSL routing strategy via `host.docker.internal`

**What still fails intermittently**:
- container may expose ports before the database is actually ready
- `curl`/driver checks may hang or reset even when TCP ports are open
- Docker Desktop responsiveness may degrade during failed startup attempts

## Immediate Recovery Steps

### Step 1: Restart Docker Desktop

Use either:

```powershell
.\scripts\restart-docker.ps1
```

Or manually:
1. Quit Docker Desktop from the tray icon
2. Wait 10 seconds
3. Relaunch Docker Desktop
4. Wait 60 seconds until `docker ps` responds immediately

### Step 2: Start Neo4j 5.13 with bounded memory

Recommended path:

```powershell
docker compose -f docker-compose.neo4j.yml up -d
Start-Sleep -Seconds 60
```

Equivalent direct run:

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

### Step 3: Verify backend readiness

```powershell
docker ps --filter "name=bioetl-neo4j"
docker logs bioetl-neo4j | Select-Object -Last 30
curl.exe http://localhost:7474/
node test_neo4j_connection.js
```

Success means:
- container is `Up`
- HTTP returns `200` or `302`
- `node test_neo4j_connection.js` prints `Connection successful`

### Step 4: WSL validation path

From WSL:

```bash
bash scripts/setup-neo4j-wsl.sh
```

This script now:
- uses `docker.exe` instead of Linux `docker`
- tests HTTP via `host.docker.internal`
- runs the repo-root `test_neo4j_connection.js`

### Step 5: Seed and verify test/docs memory

From repo root after backend readiness:

```bash
node seed_test_docs_memory.js
node query_test_docs_memory.js
```

## Files Ready

- `docker-compose.neo4j.yml`
- `test_neo4j_connection.js`
- `test_neo4j_localhost.js`
- `seed_test_docs_memory.js`
- `query_test_docs_memory.js`
- `scripts/restart-docker.ps1`
- `scripts/setup-neo4j-wsl.sh`

## Troubleshooting Matrix

| Symptom | Check | Action |
| --- | --- | --- |
| `docker ps` hangs | Docker Desktop | restart Docker Desktop |
| Container `Exited` | `docker logs bioetl-neo4j` | inspect startup error, then recreate |
| HTTP hangs | `curl http://localhost:7474/` | wait 30-60s more, then inspect logs |
| Driver timeout | `node test_neo4j_connection.js` | backend still not healthy or Bolt path unstable |
| WSL path fails | `bash scripts/setup-neo4j-wsl.sh` | verify `host.docker.internal` route and Docker Desktop integration |

## Important Non-Assumptions

- Do **not** assume TLS is the confirmed root cause.
- Do **not** assume open TCP ports mean Neo4j is ready.
- Do **not** use `/tmp` paths for the maintained recovery scripts; repo-root scripts are now canonical.

## Success Criteria

- `docker ps` shows `bioetl-neo4j` as `Up`
- `curl http://localhost:7474/` returns `200` or `302`
- `node test_neo4j_connection.js` exits with code `0`
- `node seed_test_docs_memory.js` completes
- `node query_test_docs_memory.js` returns non-zero counts
