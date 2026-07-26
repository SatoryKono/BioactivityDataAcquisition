# MCP_LOCAL_RUNTIME_CONFIG.md

*Status: internal-published (AI runtime config strategy)*

## Purpose

Document how BioETL treats MCP/runtime config files, including the distinction
between portable tracked workspace manifests and generated machine-local
runtime surfaces.

## Scope

This policy applies to:

- `.mcp.json`
- `scripts/ai/.mcp.json`
- `.zed/mcp.json`
- `.codex/settings.json`
- `.gemini/settings.json`
- `.codex/config.toml`
- `.codex/config-headless.toml`
- `.gemini/config.toml`
- `.devin/config.json`

## Current Classification

| Surface | Tracked on `main` | Runtime class | Notes |
| --- | --- | --- | --- |
| `.mcp.json` | yes | tracked exact-root workspace MCP entrypoint | generated from `scripts/ai/codex/setup_mcp.py`; MUST stay repo-relative and must not embed machine-local absolute paths |
| `scripts/ai/.mcp.json` | yes | tracked workspace MCP mirror | generated with the same portable payload as `.mcp.json` for AI runtime/script consumers |
| `.zed/mcp.json` | yes | tracked Zed workspace MCP mirror | generated with the same portable payload as `.mcp.json` |
| `.codex/settings.json` | no | local-only/generated runtime config | may exist in local checkouts; ignored by `.gitignore`; may contain machine-local absolute paths |
| `.codex/config.toml` | no | local-only/untracked runtime config | may exist in local checkouts; ignored by `.gitignore`; may contain machine-local absolute paths |
| `.gemini/settings.json` | no | local-only/generated runtime config | may exist in local checkouts; not a tracked runtime source on `main`; may contain machine-local absolute paths |
| `.codex/config-headless.toml` | no | local-only/untracked runtime config | headless variant; not currently tracked on `main` |
| `.gemini/config.toml` | no | local-only/untracked runtime config | may exist in local checkouts; not a tracked runtime source on `main` |
| `.devin/config.json` | yes | tracked active Devin runtime projection | shared-profile servers use localhost HTTP; remaining command paths stay repo-relative |
| `.claude/**` | no | unavailable in current checkout | not an active source for Codex/Gemini behavior in this program |

## Strategy

1. Treat `.mcp.json` as a retained exact-root workspace entrypoint, not as a
   machine-local runtime file. It, `scripts/ai/.mcp.json`, and `.zed/mcp.json`
   MUST use repo-relative paths.
1. Treat generated Codex/Gemini/editor runtime mirrors as local-only runtime
   surfaces when ignored by `.gitignore`; these may contain machine-local
   absolute paths when the consuming tool requires them.
1. Codex runtime npm/uv caches MUST use the native user cache directory
   (`$XDG_CACHE_HOME/bioetl-mcp` or `~/.cache/bioetl-mcp`) instead of a
   Windows-mounted workspace path. Tracked portable MCP projections continue
   to use repo-relative `.cache/**` paths.
1. Treat `.devin/config.json` as a portable tracked Devin projection. The setup
   generator replaces only `mcpServers` with the canonical repo-relative
   21-server payload and preserves existing Devin-owned top-level settings such
   as `version`, `devin`, `shell`, and `theme_mode`.
1. Devin starts repository work in its cloned workspace and root environment
   commands from the repository root. Relative MCP filesystem, cache, memory,
   and wrapper arguments therefore use that repository root as their execution
   precondition. A runtime that changes this working-directory contract must
   materialize a local-only absolute projection instead of committing it.
1. Contributor docs MUST say whether a config is portable/repo-relative or
   depends on machine-local absolute paths. `.devin/config.json` is part of the
   portable tracked set.
1. Do not silently rewrite checked-in runtime paths during unrelated work.
1. If broader portability work is required, introduce an explicit
   template/strategy change instead of implying that all current runtime
   surfaces are portable.
1. Codex launchers MUST treat MCP synchronization as an idempotent ensure
   operation: verify persisted workspace projections and the managed
   `~/.codex/config.toml` block first, regenerate only missing or stale state,
   and reserve force-refresh for an explicit setup command.

## Materialization profiles (least privilege)

The tracked portable inventory remains the full sanctioned server set
(currently 21 servers). Local materialization may use a **profile** so high-
privilege servers are not always-on:

| Profile | Membership intent | Default for daily coding? |
| --- | --- | --- |
| `stable` | host/HTTP MCP only (no `docker run` / `docker mcp gateway` servers) | **yes on 32 GiB Docker Desktop hosts** |
| `shared` | `stable` + Docker-backed daily servers over shared HTTP | **default; start shared plane first** |
| `core` | `stable` + mermaid (gateway) | explicit legacy/local profile |
| `ops` | `core` + prometheus, grafana, github-actions | observability / dashboard work |
| `graph` | `ops` + neo4j-*, brave-search, mutmut, mcp-code-interpreter, docker | research / graph / mutation work |
| `full` | entire sanctioned inventory (same as tracked portable set) | only when explicitly needed |

Shared Streamable HTTP plane (multi-client, localhost): see
[`MCP_SHARED_RUNTIME.md`](./MCP_SHARED_RUNTIME.md). Tracked portable inventory
stays stdio; only **local** projections may emit `http://127.0.0.1:…/mcp` when
`--transport-mode shared` is set.

### Why Docker MCP multiplies containers

Stdio MCP transport starts **one process/container per client session**. Each
AI host (Grok, Cursor, WSL gateway, etc.) that loads docker-backed servers
(`brave-search`, `docker`, `mermaid`, `grafana`, `prometheus`, …) can leave
orphans with random names (`elastic_*`, labels `docker-mcp=true`). On 32 GiB
hosts this thrash is a primary Docker Desktop failure mode — not a BioETL
compose bug.

### Generator

```bash
# Daily / Docker-stable (recommended on this host class):
python scripts/ai/codex/setup_mcp.py --profile stable --skip-codex-validation

# Default generator profile (core):
python scripts/ai/codex/setup_mcp.py --profile core --skip-codex-validation

# Full local enablement:
python scripts/ai/codex/setup_mcp.py --profile full --skip-codex-validation
```

One-shot host apply (profile + orphan cleanup + ensure-stable):

```powershell
.\scripts\ops\runtime\docker\apply-docker-stable-mcp.ps1 -Profile stable -WithNeo4j
# orphans only:
.\scripts\ops\runtime\docker\cleanup-mcp-orphans.ps1 -IncludeGatewayHint
```

Rules:

1. Tracked `.mcp.json` / `scripts/ai/.mcp.json` / `.zed/mcp.json` remain the
   portable **full** inventory SSOT unless a separate reviewed change says
   otherwise.
2. Profiles filter active projections (`.devin/config.json`,
   `.cursor/mcp.json`, `.vscode/mcp.json`, workspace `.codex/settings.json`,
   and optional local-only targets). Generator defaults are **`shared`**
   profile and **`shared`** transport.
3. Retired servers in `REMOVED_MCP_SERVER_NAMES` must never reappear.
4. Do not increase tech-debt budgets to paper over privilege sprawl.
5. Prefer **one** AI client with a heavy **stdio**/Docker MCP profile at a time;
   after reconnects run `cleanup-mcp-orphans.ps1` or `ensure-stable.ps1`.
   Alternatively run the **shared HTTP plane** (`start-shared.ps1` +
   `--profile shared --transport-mode shared`) so multiple clients share one
   process per migrated server — see `MCP_SHARED_RUNTIME.md`.

## Token Configuration

MCP tokens are local runtime inputs, not portable workspace configuration. The
tracked `.mcp.json` and `scripts/ai/.mcp.json` files must route token-bearing
servers through `scripts/ai/mcp/*wrapper*` scripts rather than embedding token
values.

The repo env loaders are:

- `scripts/ops/support/load_repo_env.sh`
- `scripts/ai/mcp/support/load_repo_env.ps1`

For Grok on Windows, the documented compatibility helper
`scripts/ai/mcp/export_mcp_env_from_dotenv.ps1` can export already configured
local values to process scope, or to user scope with `-UserScope`. It MUST NOT
write secret values into tracked MCP configuration.

They load local env files when present and normalize common aliases such as:

- `GITHUB_TOKEN` <-> `GITHUB_PERSONAL_ACCESS_TOKEN`
- `BRAVE_SEARCH_API_KEY` / `BRAVE_API_KEY1` -> `BRAVE_API_KEY`
- `GRAFANA_TOKEN` / `GRAFANA_API_KEY` -> `GRAFANA_SERVICE_ACCOUNT_TOKEN`
- `DOCKERHUB_PAT` / `DOCKERHUB_TOKEN` -> `HUB_PAT_TOKEN`

Token-bearing wrappers must also use:

- `scripts/ai/mcp/support/token_validation.sh`
- `scripts/ai/mcp/support/token_validation.ps1`

Validation must check missing required tokens, minimum length, and known token
prefixes where a provider has stable prefixes. Optional service tokens should
warn and continue with local-default or unauthenticated behavior.

CI/CD stance: default CI may run static config checks and stub/local MCP smoke
tests. CI must not require personal MCP tokens or third-party service tokens
unless a separate security design approves the secret source, scopes, rotation,
and fork/PR exposure model. Document any approved CI secret usage in
[`../../mcp-token-configuration.md`](../../mcp-token-configuration.md).

Remote MCP servers that support OAuth, including Ref Tools at
`https://api.ref.tools/mcp`, must use the key-free base URL in tracked and
generated config. Ref authentication may use interactive OAuth or the local
Codex-only `env_http_headers` mapping from `x-ref-api-key` to
`REF_TOOL_API_KEY`. Only the environment variable name may appear in generated
config; API key values must not be embedded in URLs or committed config.

## Required Documentation Language

When AI docs mention these configs, they SHOULD state:

- whether the file is tracked on `main` or local-only/untracked
- whether the file is a portable workspace manifest or an active local runtime
  config
- absolute local paths are forbidden in tracked workspace MCP manifests,
  including the tracked Devin projection, but may be expected in generated
  local-only runtime surfaces
- local verification may be required for local-only runtime settings
- `.claude/**` is out of scope unless a future task restores and verifies it

## Validation Expectations

- Validate JSON syntax for `*.json` config files after edits.
- Validate TOML syntax for `*.toml` config files after edits.
- Re-check runtime/mirror docs when config strategy language changes.

## Related Files

- `AGENTS.md`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md`
- `docs/00-project/ai/agents/policy/MCP_SHARED_RUNTIME.md`
- `scripts/ops/runtime/mcp/README.md`

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.

## Devin HTTP Header Projection

The canonical MCP server inventory is shared with Devin, but HTTP authentication
must use Devin-supported configuration. The generated `.devin/config.json`
projects the `ref` credential as:

```json
"headers": {
  "x-ref-api-key": "$REF_TOOL_API_KEY"
}
```

`env_http_headers` remains a Codex-specific field and MUST NOT be copied into
Devin configuration. Store `REF_TOOL_API_KEY` in Devin Secrets; never commit the
secret value.
