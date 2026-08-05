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

| Canonical variable | Accepted aliases |
| --- | --- |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | `GITHUB_TOKEN` |
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

## Token Matrix

| MCP | Variable | Required | Source | Minimum scope | Rotation |
| --- | --- | --- | --- | --- | --- |
| GitHub | `GITHUB_PERSONAL_ACCESS_TOKEN` | Yes for GitHub MCP | GitHub fine-grained PAT or classic PAT | Repository read access needed for the task | 90 days |
| Brave Search | `BRAVE_API_KEY` | Yes for Brave MCP | Brave Search API console | Web Search API quota | 90 days |
| Ref Tools | `REF_TOOL_API_KEY` or OAuth | No when OAuth is used | Ref Tools key console or interactive OAuth | Documentation search only | 90 days |
| OpenRouter | `OPENROUTER_API_KEY` | Only for OpenRouter-backed tooling | OpenRouter key console | Models explicitly selected by the local tool | 90 days |
| Prometheus | `PROMETHEUS_TOKEN` or username/password | No | Local protected Prometheus endpoint | Read/query only | 90 days for shared service accounts |
| Grafana | `GRAFANA_SERVICE_ACCOUNT_TOKEN` or username/password | No | Grafana service account preferred | Viewer/read-only dashboard and datasource access | 90 days |
| Neo4j Cypher | `NEO4J_*` | No for local defaults | Local Neo4j memory instance | Local memory database only | Rotate default before shared-host use |
| Neo4j Memory | `NEO4J_*` | No for local defaults | Local Neo4j memory instance | Local memory database only | Rotate default before shared-host use |
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
| GitHub MCP says token missing | Set `GITHUB_PERSONAL_ACCESS_TOKEN` or `GITHUB_TOKEN`; verify alias normalization with `test_env_loading.sh` or `check.sh`. |
| GitHub token prefix warning | Confirm the token came from GitHub and has only the scopes needed by the local MCP task. |
| Brave MCP exits immediately | Set `BRAVE_API_KEY` or a supported alias; keys shorter than 31 characters are rejected. |
| DeepWiki MCP requires login | Set `DEEPWIKI_API_KEY` and `DEEPWIKI_ORGANISATION_ID`; tracked projections contain environment references, never credential values. |
| Ref MCP requires login | Use interactive OAuth, or set `REF_TOOL_API_KEY`; Codex sends it through `env_http_headers` as `x-ref-api-key` without placing the value in config. |
| Grafana MCP starts but queries fail | Set `GRAFANA_SERVICE_ACCOUNT_TOKEN` or local username/password; confirm `GRAFANA_URL`. |
| Prometheus MCP cannot query | Confirm `PROMETHEUS_URL`; add token or username/password only if the endpoint is protected. |
| Neo4j MCP authentication fails | Confirm `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, or `NEO4J_AUTH`. Rotate the documented local default before shared-host use. |
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
