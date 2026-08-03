# Shared MCP plane — operator playbook

Program: GitHub #6589 (Phase 3), #6563 (closed).  
Policy: `docs/00-project/ai/agents/policy/MCP_SHARED_RUNTIME.md`.

## Goal

Multiple AI clients (Codex, Devin, Grok, Cursor) → **one** long-lived
Streamable HTTP endpoint per logical MCP server → **≤1** process/container
per thrash image (no N× `docker run --rm -i` stdio).

## Daily multi-client (recommended)

```bash
cd <repo>

# 1) Shared plane (daily servers only; skips daily=false e.g. deja without binary)
./scripts/ops/runtime/mcp/start-shared.sh
./scripts/ops/runtime/mcp/health-shared.sh
# optional full catalog including optional servers:
# ./scripts/ops/runtime/mcp/start-shared.sh --all
# ./scripts/ops/runtime/mcp/health-shared.sh all

# 2) Local projections → localhost HTTP
export PYTHONPATH=.
python3 scripts/ai/codex/setup_mcp.py \
  --profile shared --transport-mode shared --skip-codex-validation
# Optional: rewrite tracked workspace MCP JSON files onto shared HTTP URLs
# (does not start the plane; do not commit the rewritten local files).
python3 scripts/ops/runtime/mcp/_materialize_shared_http_configs.py
# Do NOT commit OS-flipped tracked portable .mcp.json from Linux apply.
git checkout -- .mcp.json .devin/config.json 2>/dev/null || true

# 3) Devin machine-local HTTP projection (gitignored)
python3 scripts/ops/runtime/mcp/apply-shared-to-devin.py

# 4) Grok (Windows path when applicable)
# .\scripts\ops\runtime\mcp\apply-shared-to-grok.ps1 -DisableDockerGateways

# 5) Full restart of AI clients (required — hot reload often keeps old stdio)
#    Codex, Devin, Grok, Cursor, VS Code
```

### Thrash proof

```bash
# Expect 1 each for thrash docker images while 2+ clients are live
docker ps --format '{{.Image}}' | grep -E 'grafana|brave-search|prometheus' | sort | uniq -c

# Parent of docker run must be mcp-proxy, not codex/devin
pgrep -af 'docker run.*(grafana|brave-search|prometheus)' 

codex mcp list --json | python3 -c "import json,sys; d=json.load(sys.stdin);
for n in ('grafana','brave-search','prometheus','fetch','github'):
 e=next((x for x in d if x.get('name')==n),None); print(n, (e or {}).get('transport',{}).get('type'), (e or {}).get('transport',{}).get('url'))"

devin mcp list 2>/dev/null | grep -E 'grafana|brave|prometheus|context7|URL:|Command:' | head -40
```

## Fallback (single heavy client, stdio)

```bash
python3 scripts/ai/codex/setup_mcp.py \
  --profile stable --transport-mode stdio --skip-codex-validation
# Prefer one AI client only — stdio multiplies per session
```

## Optional servers

| Server | Port | Daily | Notes |
| --- | --- | --- | --- |
| deja | 8814 | **no** | Needs `deja` binary (`go install github.com/vshulcz/deja-vu/cmd/deja@latest`). Start with `./start-shared.sh deja` when installed. |
| docker | 8817 | **no** | Gateway thrash leader. Single proxy: `./start-shared.sh docker`. Keep off daily unless needed; Devin daily still omits. |
| mermaid | 8818 | **no** | Same pattern: `./start-shared.sh mermaid` (or `docker mermaid dockerhub`). |
| dockerhub | 8819 | **no** | Same pattern: `./start-shared.sh dockerhub`. |

Catalog SSOT: `scripts/ops/runtime/mcp/shared-servers.json` (`daily: false` = optional).

## Ready gate (start-shared)

- Success = HTTP `GET http://127.0.0.1:<port>/ping` (not TCP-only).
- Default settle ≈25s host / 45s docker-backed; retries **never** double-bind (kill tree + wait free, or accept already-ready).
- Idempotent re-run: already-ready servers report `already_up` and exit 0 when all selected are healthy.

## Toolkit / gateway

- Do **not** enable Docker Desktop MCP Toolkit full catalog / `MCP_DOCKER --profile default`.
- Disable Toolkit servers: `jetbrains`, `node-code-sandbox`.
- `container_name` in Compose is **not** a substitute for shared HTTP.

## Thrash recovery

```powershell
# Windows (when clients idle preferred)
.\scripts\ops\runtime\docker\cleanup-mcp-orphans.ps1 -KillHostGateways
```

**Never** kills `bioetl`, `bioetl-neo4j`, `bioetl-*`, or label `bioetl.mcp.shared=true`.

## Stop plane

```bash
./scripts/ops/runtime/mcp/stop-shared.sh
```

## Related issues

- #6589 Phase 3 umbrella
- #6590 generator/ensure
- #6594 Devin local shared
- #6593 plane reliability
- #6592 expand anti-thrash
- #6591 docs/closeout
- #6293 no long-lived stdio Compose
