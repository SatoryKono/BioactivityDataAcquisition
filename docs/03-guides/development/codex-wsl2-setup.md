______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# OpenAI Codex CLI: Setup and Usage via WSL2

Guide for running OpenAI Codex CLI on Windows through WSL2 Debian,
with VPN proxy workaround.

## Prerequisites

| Component          | Version | Notes                          |
| ------------------ | ------- | ------------------------------ |
| WSL2               | 2.6+    | `wsl --version`                |
| Debian (WSL)       | any     | `wsl --install -d Debian`      |
| Node.js (in WSL)   | 22.x    | Installed to `/usr/local/`     |
| Codex CLI (in WSL) | 0.112+  | `npm install -g @openai/codex` |
| Python (Windows)   | 3.11+   | For proxy server               |

> **Why WSL2?** Codex CLI is a Rust binary that doesn't run natively on
> Windows. WSL2 provides a Linux environment where it works correctly.

______________________________________________________________________

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Windows Host                                   │
│                                                 │
│  scripts/ops/runtime/wsl/wsl_proxy.py ──► VPN ──► Internet  │
│        ▲  (port 3128)                           │
│        │                                        │
│  ┌─────┼───────────────────────────────────┐    │
│  │  WSL2 Debian                            │    │
│  │     │                                   │    │
│  │  http_proxy=http://HOST_IP:3128         │    │
│  │     │                                   │    │
│  │  codex ──► proxy ──► api.openai.com     │    │
│  │  npx   ──► proxy ──► registry.npmjs.org │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

WSL2 on Windows 10 cannot route HTTPS traffic through the host VPN
directly (mirrored networking requires Windows 11 23H2+). The proxy
bridges this gap.

______________________________________________________________________

## File Inventory

| File                   | Location                   | Purpose                                  |
| ---------------------- | -------------------------- | ---------------------------------------- |
| `wsl_proxy.py`         | `scripts/ops/`             | HTTP CONNECT proxy (Python stdlib)       |
| `start-wsl-proxy.bat`  | `scripts/ops/`             | Start proxy in background                |
| `codex.bat`            | `scripts/ops/`             | Launch interactive Codex from Windows    |
| `codex-exec.bat`       | `scripts/ops/`             | Launch full-auto Codex from Windows      |
| `.setup_wsl_codex.sh`  | `scripts/engineering/dev/` | DNS resolver (dig + PowerShell fallback) |
| `.wsl_proxy_env.sh`    | `scripts/engineering/dev/bash/` | Auto-configure proxy env vars            |
| `.codex/config.toml`   | repo root                  | Project-level Codex config               |
| `~/.codex/config.toml` | WSL home                   | Global Codex config (MCP servers)        |
| `~/.bashrc`            | WSL home                   | Sources DNS + proxy scripts              |

______________________________________________________________________

## Quick Start

### 1. Start the proxy (Windows)

Run once before working with Codex:

```cmd
scripts\ops\start-wsl-proxy.bat
```

Or manually:

```cmd
python scripts\ops\wsl_proxy.py
```

The proxy listens on `0.0.0.0:3128`. Verify:

```cmd
netstat -an | findstr 3128
```

### 2. Open WSL2

```cmd
wsl -d Debian
```

### 3. Use Codex

```bash
cx                              # interactive mode
cxe "fix the failing test"      # full-auto mode (no confirmations)
codex review                    # code review mode
```

### 4. Alternative: launch from Windows

```cmd
scripts\ops\codex.bat                           # interactive
scripts\ops\codex.bat "add retry logic"         # interactive with prompt
scripts\ops\codex-exec.bat "fix the bug"        # full-auto
```

### 5. Optional: install `codex` into Windows PATH

If you want to run Codex from any `cmd.exe` or PowerShell session without
prefixing the repo path:

```cmd
scripts\ops\install-codex-cmd.bat
```

This creates user-level shims in `%USERPROFILE%\bin` and adds that directory to
your user `PATH`. Installed commands:

```cmd
codex
codex-exec "your prompt"
cx
cxe "your prompt"
```

Windows launcher behavior:

- by default, `scripts\ops\codex.bat` and `scripts\ops\codex-exec.bat` use the
  current default WSL distro;
- set `BIOETL_WSL_DISTRO` if Codex should target a specific distro explicitly.

______________________________________________________________________

## Initial Setup (one-time)

### Install Codex in WSL2

```bash
wsl -d Debian

# Node.js (if not installed)
curl -fsSL https://nodejs.org/dist/v22.14.0/node-v22.14.0-linux-x64.tar.xz \
  | sudo tar -xJ -C /usr/local --strip-components=1

# Codex CLI
npm install -g @openai/codex
codex --version
```

### Authenticate

```bash
codex login --device-auth
```

Follow the prompts: open the URL in your browser and enter the one-time code.

> **VPN note:** The proxy must be running for authentication to work.
> Make sure `http_proxy` / `https_proxy` are set (happens automatically
> via `~/.bashrc` → `scripts/engineering/dev/bash/.wsl_proxy_env.sh`).

### Verify

```bash
codex login status
# Expected: "Logged in using ChatGPT"
```

______________________________________________________________________

## Configuration

### Project config (`.codex/config.toml`)

```toml
model = "gpt-5.4"
approval_policy = "on-request"
sandbox_mode = "workspace-write"
model_reasoning_effort = "high"
web_search = "cached"

[sandbox_workspace_write]
network_access = true

[features]
experimental_windows_sandbox = true
shell_snapshot = true
```

### Global config (`~/.codex/config.toml`)

Key settings:

```toml
model = "gpt-5.4"
model_provider = "openai"
personality = "pragmatic"

[projects.'BioactivityDataAcquisition']
trust_level = "trusted"

[features]
multi_agent = true
```

> Do not define `[model_providers.openai]` in modern Codex CLI configs.
> `openai` is a built-in provider ID, and overriding it now fails during
> startup. If you need API-key-based auth, set `OPENAI_API_KEY` in the
> environment instead of redefining the built-in provider block.

### MCP Servers

The generated workspace config from `python -m scripts.engineering.dev setup-mcp`
registers the active BioETL MCP server set:

| Server | Transport | Purpose |
| --- | --- | --- |
| `memory` | `npx @modelcontextprotocol/server-memory` | Persistent assistant memory file |
| `filesystem` | `scripts/ai/mcp/mcp_filesystem_wrapper.sh` (WSL) / `scripts/ai/mcp/mcp_filesystem_wrapper.ps1` (Windows) | Repo-scoped file access (host-native absolute root) |
| `fetch` | `uvx --python 3.13 --from mcp-server-fetch==2025.4.7 mcp-server-fetch` | HTTP fetch tooling; CPython 3.13 avoids the known 3.14 stdio startup hang in WSL |
| `github` | Project wrapper | GitHub API access |
| `docker` | Project wrapper | Docker MCP gateway access |
| `context7` | Project wrapper | Documentation/context lookup |
| `ast-grep` | Project wrapper | Structural code search |
| `mcp-code-interpreter` | Project wrapper | Sandboxed code interpreter |
| `prometheus` | Project wrapper | Prometheus queries and target discovery |
| `grafana` | Project wrapper | Grafana dashboards, datasources, and observability context |
| `brave-search` | Project wrapper | Web search when credentials are available |
| `neo4j-cypher` | Project wrapper | Neo4j Cypher access |
| `neo4j-memory` | Project wrapper | Neo4j-backed project memory access |
| `mermaid` | Project wrapper | Mermaid rendering/diagram tooling |
| `deepwiki` | Remote HTTP MCP | DeepWiki repository documentation lookup |
| `ref` | Remote HTTP MCP with OAuth | Ref Tools documentation search and URL retrieval |

Retired MCP servers such as `sequential-thinking`, `pdf`, `needle`,
`docker-docs`, `dockerhub`, `paper-search`, `biomoltechDocs`, and
`mintlify` are intentionally not registered in generated configs. See
`docs/00-project/ai/mcp-governance.md` for the active/retired inventory.

After the initial setup, manual MCP re-registration is not necessary on every
new Codex session. `bash scripts/ai/codex/run-codex.sh`,
`scripts/ops/launchers/codex/codex.sh`, and
`scripts/ops/launchers/codex/codex-exec.sh` verify the persisted workspace
projections and the managed `~/.codex/config.toml` block before launch. Current
files are left untouched; missing or stale state is regenerated automatically.

______________________________________________________________________

## VPN Workaround Details

### Problem

WSL2 on Windows 10 uses a NAT-based virtual network. When a VPN is active,
WSL2 traffic cannot reach external hosts because:

1. VPN routes bypass the WSL2 virtual adapter
1. DNS resolution in WSL2 fails (queries go to the gateway, not VPN DNS)
1. Mirrored networking (`networkingMode=mirrored`) requires Windows 11 23H2+

### Solution: Two-layer workaround

**Layer 1: DNS** (`scripts/engineering/dev/.setup_wsl_codex.sh`)

Resolves OpenAI and npm hosts using:

- `dig` (fast, works when WSL DNS is functional)
- `powershell.exe Resolve-DnsName` fallback (uses Windows DNS via VPN)

Caches IPv4 addresses in `/etc/hosts`. Runs automatically from `~/.bashrc`
if `api.openai.com` is missing from `/etc/hosts`.

Manual refresh:

```bash
bash "$BIOETL_DIR/scripts/engineering/dev/.setup_wsl_codex.sh"
```

**Layer 2: Proxy** (`scripts/ops/runtime/wsl/wsl_proxy.py`)

Minimal HTTP CONNECT proxy running on Windows, listening on `0.0.0.0:3128`.
WSL2 routes all HTTP/HTTPS traffic through it via `http_proxy` / `https_proxy`
environment variables (set by `scripts/engineering/dev/bash/.wsl_proxy_env.sh`).

The proxy runs on the Windows host where VPN routing works correctly.

______________________________________________________________________

## WSL2 Shell Configuration

### `~/.bashrc` additions

```bash
# BioETL project alias
export BIOETL_DIR="BioactivityDataAcquisition"
alias cdp="cd $BIOETL_DIR"
alias cx="cd $BIOETL_DIR && codex"
alias cxe="cd $BIOETL_DIR && codex exec --full-auto"

# Ensure OpenAI DNS (VPN workaround)
if ! grep -q "api.openai.com" /etc/hosts 2>/dev/null; then
  bash "$BIOETL_DIR/scripts/engineering/dev/.setup_wsl_codex.sh" 2>/dev/null
fi

# WSL2 proxy (VPN workaround)
source "$BIOETL_DIR/scripts/engineering/dev/bash/.wsl_proxy_env.sh" 2>/dev/null
```

### Proxy control aliases

```bash
proxy-on     # enable proxy (auto-detects Windows host IP)
proxy-off    # disable proxy (when VPN is off)
```

### `/etc/wsl.conf`

```ini
[network]
generateHosts = false       # preserve our DNS entries
generateResolvConf = false   # keep custom resolv.conf
```

______________________________________________________________________

## Troubleshooting

### Codex can't connect to OpenAI

1. **Check proxy is running** (Windows):

   ```cmd
   netstat -an | findstr 3128
   ```

   If not listening, run `scripts\ops\start-wsl-proxy.bat`.

1. **Check proxy env** (WSL):

   ```bash
   echo $http_proxy
   # Expected: http://172.x.x.x:3128
   ```

   If empty, run `proxy-on` or `source ~/.bashrc`.

1. **Test connectivity** (WSL):

   ```bash
   curl -x $http_proxy -sI https://api.openai.com | head -3
   # Expected: HTTP/1.1 200 Connection Established
   ```

### DNS not resolving

```bash
# Refresh DNS cache
bash "$BIOETL_DIR/scripts/engineering/dev/.setup_wsl_codex.sh"

# Verify
grep openai /etc/hosts
```

### MCP servers timeout

All servers have `startup_timeout_sec = 30` in `~/.codex/config.toml`.
If still failing, increase to 60 or check that `registry.npmjs.org`
is in `/etc/hosts` and the proxy is running.

### Token expired

```bash
codex login --device-auth
# Open URL in browser, enter the code
```

### Model mismatch

Project config overrides global. Check both:

```bash
cat "$BIOETL_DIR/.codex/config.toml" | grep model
cat ~/.codex/config.toml | grep model
```

### VPN is off, proxy not needed

```bash
proxy-off    # disable proxy vars
```

When VPN is back on:

```bash
proxy-on     # re-enable proxy vars
```

______________________________________________________________________

## Useful Commands

| Command                  | Description                      |
| ------------------------ | -------------------------------- |
| `cx`                     | Interactive Codex in project dir |
| `cxe "prompt"`           | Full-auto Codex                  |
| `codex review`           | Code review                      |
| `codex resume`           | Resume previous session          |
| `codex login status`     | Check auth status                |
| `proxy-on` / `proxy-off` | Toggle proxy                     |
| `cdp`                    | cd to project directory          |

______________________________________________________________________

*Last updated: 2026-03-10*
