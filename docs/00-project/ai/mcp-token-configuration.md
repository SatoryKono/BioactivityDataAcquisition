# MCP Token Configuration

Status: internal-published

This guide documents local MCP token sources, aliases, validation, rotation,
and troubleshooting. It is intentionally about AI tooling/runtime helpers, not
BioETL ETL runtime dependencies.

## Local Storage Policy

- Keep real values in the shell environment or local untracked `.env` /
  `.env.local` files.
- Do not commit, paste, log, or screenshot real token values.
- Use `.env.example` only as a template and status/source checklist.
- Prefer provider-specific read-only or least-privilege scopes.
- Rotate shared service-account tokens every 90 days, and rotate immediately
  after exposure, workstation turnover, or owner transfer.

## Historical Exposure Note

Current `HEAD` must not track real `.env` / `.env.local` files; only tracked
templates such as `.env.example` may be present. Repository history contains
historical `.env` / `.env.local` path entries, so any token that was ever
committed there must be treated as exposed and rotated before use. Do not claim
the repository history is secret-free unless a dedicated history rewrite or
secret scan has been completed and reviewed.

## Environment Loading

The MCP wrappers load environment values through:

- `scripts/ops/support/load_repo_env.sh`
- `scripts/ai/mcp/support/load_repo_env.ps1`

Supported aliases:

GitHub MCP uses one token path per process:

1. `GITHUB_PERSONAL_ACCESS_TOKEN` if already set (never overwritten)
1. else alias `GITHUB_TOKEN` copied into `GITHUB_PERSONAL_ACCESS_TOKEN`
1. else `GITHUB_CDX_PERSONAL_ACCESS_TOKEN` or `GITHUB_ANY_PERSONAL_ACCESS_TOKEN`
   (compat only; do not add `ANY` to new `.env` files)
1. else `gh auth token` when the GitHub CLI is logged in

Loaders alias **into PAT only**. They must not copy PAT into `GITHUB_TOKEN` or
write `GH_TOKEN` (#10298): parent `gh` then prefers env over `hosts.yml` and
returns HTTP 401 when a stale User `ghp_*` is present.

`GITHUB_TOKEN_02` is **not** in the alias chain. Leave it unused or document an
owner; do not load it into process (#10301).

Wrappers log the chosen path name on stderr and never print the secret.
Do not configure PAT and `gh auth` as two silent sources for the same
process.

Parent `gh` CLI: `hosts.yml` OAuth, **no** process `GITHUB_TOKEN` / `GH_TOKEN`.
MCP child: PAT in the child process only. `export_mcp_env_from_dotenv.ps1
-UserScope` must not persist GitHub keys into the User hive.

| Canonical variable | Accepted aliases |
| --- | --- |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | `GITHUB_TOKEN`, `GH_TOKEN` (bash → PAT only), `GITHUB_CDX_PERSONAL_ACCESS_TOKEN` |
| `BRAVE_API_KEY` | `BRAVE_SEARCH_API_KEY`, `BRAVE_API_KEY1` |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN` | `GRAFANA_TOKEN`, `GRAFANA_API_KEY` |
| `GRAFANA_USERNAME` | `GF_SECURITY_ADMIN_USER` |
| `GRAFANA_PASSWORD` | `GF_SECURITY_ADMIN_PASSWORD` |
| `HUB_PAT_TOKEN` | `DOCKERHUB_PAT`, `DOCKERHUB_TOKEN` |
| `DOCKERHUB_USERNAME` | `DOCKER_USERNAME` |
| `NEO4J_USERNAME` / `NEO4J_PASSWORD` | `NEO4J_AUTH`, `NEO4J_AUTH_USERNAME`, `NEO4J_AUTH_PASSWORD` |

Provider credentials are intentionally isolated. `OPENAI_API_KEY` and
`OPENROUTER_API_KEY` identify different providers and MUST be configured separately;
the repository environment loaders never project one into the
other.

Run a non-secret status check:

```bash
bash scripts/ai/mcp/test_env_loading.sh
```

The script reports `SET` / `NOT SET` only and must not print secret values.
GitHub names (`GITHUB_PERSONAL_ACCESS_TOKEN`, `GITHUB_TOKEN`,
`GITHUB_CDX_PERSONAL_ACCESS_TOKEN`, `GITHUB_TOKEN_02`, `GH_TOKEN`) are status
only: `NOT SET` is allowed and must not fail the script.

### Credential surfaces (no values)

| Surface | Role | Notes |
| --- | --- | --- |
| User env `GITHUB_PERSONAL_ACCESS_TOKEN` | Must not be a stale `ghp_*` | Poisons every new PowerShell; #10298 phase 0 |
| `.env` PAT / CDX | MCP child | Loader does not overwrite an already-set process PAT |
| `.env` `GITHUB_TOKEN_02` | Not in alias chain | Do not load into process (#10301) |
| `gh auth` `hosts.yml` | Parent `gh` | OAuth `gho_*`; requires no process `GITHUB_TOKEN` |
| MCP child | One PAT in child only | Wrappers never export `GITHUB_TOKEN` to parent |

`.env` edits need explicit per-task approve. Tracked docs and `test_env_loading.sh`
do not require that approve.

## Token Matrix

| MCP | Variable | Required | Source | Minimum scope | Rotation |
| --- | --- | --- | --- | --- | --- |
| GitHub | `GITHUB_PERSONAL_ACCESS_TOKEN` | Yes for GitHub MCP | GitHub fine-grained PAT, classic PAT, or `gh auth token` (one path) | Repository read access needed for the task | 90 days |
| Brave Search | `BRAVE_API_KEY` | Yes for Brave MCP | Brave Search API console | Web Search API quota | 90 days |
| Ref Tools | `REF_TOOL_API_KEY` or OAuth | No when OAuth is used | Ref Tools key console or interactive OAuth | Documentation search only | 90 days |
| OpenRouter | `OPENROUTER_API_KEY` | Only for OpenRouter-backed tooling | OpenRouter key console | Models explicitly selected by the local tool | 90 days |
| Prometheus | `PROMETHEUS_TOKEN` or username/password | No | Local protected Prometheus endpoint | Read/query only | 90 days for shared service accounts |
| Grafana | `GRAFANA_SERVICE_ACCOUNT_TOKEN` or username/password | No | Grafana service account preferred | Viewer/read-only dashboard and datasource access | 90 days |
| Neo4j Cypher | `NEO4J_USERNAME` / `NEO4J_PASSWORD` or `NEO4J_AUTH` | Yes when Neo4j MCP is used | Local Neo4j memory instance | Local memory database only | Rotate after exposure or ownership changes |
| Neo4j Memory | `NEO4J_USERNAME` / `NEO4J_PASSWORD` or `NEO4J_AUTH` | Yes when Neo4j MCP is used | Local Neo4j memory instance | Local memory database only | Rotate after exposure or ownership changes |
| Docker Hub | `HUB_PAT_TOKEN` | No | Docker Hub PAT | Read-only pull access unless publishing is explicitly required | 90 days |

## Wrapper Validation

Token-bearing wrappers use:

- `scripts/ai/mcp/support/token_validation.sh`
- `scripts/ai/mcp/support/token_validation.ps1`

Validation behavior:

- required tokens fail fast when missing or too short
- known token prefixes are checked where stable
- optional tokens warn and continue
- values are never printed
- `BIOETL_MCP_VALIDATE_ONLY=1` validates configuration and exits before
  launching a long-lived stdio server

Examples:

```bash
BIOETL_MCP_VALIDATE_ONLY=1 scripts/ai/mcp/github-mcp-wrapper.sh
BIOETL_MCP_VALIDATE_ONLY=1 scripts/ai/mcp/mcp_brave_search_wrapper.sh
BIOETL_MCP_VALIDATE_ONLY=1 scripts/ai/mcp/mcp_grafana_wrapper.sh
```

For the full local registration and wrapper preflight:

```bash
bash scripts/ai/mcp/check.sh
```

## Troubleshooting

| Symptom | Check |
| --- | --- |
| GitHub MCP says token missing | Set **one** of `GITHUB_PERSONAL_ACCESS_TOKEN`, `GITHUB_TOKEN`, or a working `gh auth token`; verify alias normalization with `test_env_loading.sh` or `check.sh`. |
| `gh api user` HTTP 401 after `Import-BioetlRepoEnv` | Process `GITHUB_TOKEN` / `GH_TOKEN` is poisoning `hosts.yml`. Loader must not copy PAT → `GITHUB_TOKEN`. Unset User-scope stale `ghp_*`. Do not print token values (#10298). |
| GitHub MCP says official binary missing | Install [`github/github-mcp-server`](https://github.com/github/github-mcp-server) and set `BIOETL_GITHUB_MCP_SERVER` (or `GITHUB_MCP_SERVER_BIN`) to the executable. Wrappers do not fall back to `@modelcontextprotocol/server-github`. |
| GitHub token prefix warning | Confirm the token came from GitHub and has only the scopes needed by the local MCP task. |
| Brave MCP exits immediately | Set `BRAVE_API_KEY` or a supported alias; keys shorter than 31 characters are rejected. |
| DeepWiki MCP requires login | Set `DEEPWIKI_API_KEY` and `DEEPWIKI_ORGANISATION_ID`; tracked projections contain environment references, never credential values. |
| Ref MCP requires login | Use interactive OAuth, or set `REF_TOOL_API_KEY`; Codex sends it through `env_http_headers` as `x-ref-api-key` without placing the value in config. |
| Grafana MCP starts but queries fail | Set `GRAFANA_SERVICE_ACCOUNT_TOKEN` or local username/password; confirm `GRAFANA_URL`. |
| Prometheus MCP cannot query | Confirm `PROMETHEUS_URL`; add token or username/password only if the endpoint is protected. |
| Neo4j MCP authentication fails | Confirm `NEO4J_URI`; configure `NEO4J_USERNAME` and `NEO4J_PASSWORD`, or `NEO4J_AUTH`, with the instance credentials. The template supplies no password. With `LIVE_AUDIT_MODE=true`, configure `NEO4J_AUDIT_PASSWORD` or `NEO4J_AUDIT_AUTH`; audit mode does not fall back to main credentials. `NEO4J_AUDIT_USERNAME` takes priority over the username in `NEO4J_AUDIT_AUTH`: clear the template's username to use the complete AUTH pair, or set it to the intended audit account. |
| OpenRouter authentication fails | Set a dedicated `OPENROUTER_API_KEY`; never reuse or alias `OPENAI_API_KEY`. |
| Docker-backed MCP cannot start | Confirm Docker is installed and available through the wrapper resolver. |

## CI/CD Stance

Default CI may validate MCP config structure, wrapper syntax, token-validation
behavior with synthetic values, and stub/local MCP smoke tests.

Default CI must not require real personal or third-party MCP tokens. Adding
GitHub Actions secrets for live MCP token tests requires a separate security
design that defines:

- exact secret names and owners
- least-privilege scopes
- rotation cadence
- fork/PR exposure rules
- failure mode when secrets are unavailable

Until that design exists, live configured-token MCP checks remain local
operator validation.

## Devin HTTP Header Projection

The canonical MCP server inventory is shared with Devin, but HTTP authentication
must use Devin-supported configuration. The generated
`.devin/mcp_config.json` projects DeepWiki and Ref credentials as:

```json
"headers": {
  "x-deepwiki-api-key": "${env:DEEPWIKI_API_KEY}",
  "x-deepwiki-organisation-id": "${env:DEEPWIKI_ORGANISATION_ID}",
  "x-ref-api-key": "${env:REF_TOOL_API_KEY}"
}
```

`env_http_headers` remains a Codex-specific field and MUST NOT be copied into
Devin configuration. Store `DEEPWIKI_API_KEY`,
`DEEPWIKI_ORGANISATION_ID`, and `REF_TOOL_API_KEY` in Devin Secrets; never
commit secret values.
