# MCP Governance

## Назначение
MCP используются как tooling-layer для AI-ассистентов.

## Ограничения
- MCP не являются частью ETL runtime
- Нельзя обходить UnifiedHTTPClient
- Нельзя писать в domain
- Code interpreter работает только в sandbox
- MCP token handling is local-tooling governance. Real token values must stay in
  shell environment variables or local untracked `.env`/`.env.local` files and
  must never be committed, logged, or copied into docs.

## Token Configuration

Canonical token guidance lives in
[`mcp-token-configuration.md`](mcp-token-configuration.md).

Required local tokens:

- `GITHUB_PERSONAL_ACCESS_TOKEN` or alias `GITHUB_TOKEN` for `github`
- `BRAVE_API_KEY` or alias `BRAVE_SEARCH_API_KEY` / `BRAVE_API_KEY1` for `brave-search`

Optional local auth:

- `PROMETHEUS_TOKEN`, `PROMETHEUS_USERNAME`, `PROMETHEUS_PASSWORD` for
  `prometheus`
- `GRAFANA_SERVICE_ACCOUNT_TOKEN`, `GRAFANA_USERNAME`, `GRAFANA_PASSWORD` for
  `grafana`
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_AUTH` for
  `neo4j-cypher` and `neo4j-memory`
- `REF_TOOL_API_KEY` for `ref` when local env-header authentication is used
  instead of OAuth

Wrappers must source the repo env loader and the token validation helper before
starting token-bearing servers. Use `BIOETL_MCP_VALIDATE_ONLY=1` for safe
preflight checks that validate configuration without launching long-lived stdio
servers.

OpenAI and OpenRouter credentials are provider-specific and must remain
separate. The environment loaders do not alias `OPENAI_API_KEY` to
`OPENROUTER_API_KEY`.

MCP uv/uvx wrappers preserve configured proxy egress by default. Operators may
set `BIOETL_UVX_DIRECT_NETWORK=1` only as an explicit, host-local workaround
for broken proxy configuration. This opt-in permits direct package-resolution
traffic and must not be enabled as a shared default.

## Активные MCP
memory, filesystem, fetch, github, context7, ast-grep, mcp-code-interpreter,
prometheus, grafana, mermaid,
brave-search,
docker, neo4j-cypher, neo4j-memory,
deja, adr-analysis, mutmut, code-analyzer, github-actions,
deepwiki, ref

`deepwiki` uses environment-backed header references to `DEEPWIKI_API_KEY` and
`DEEPWIKI_ORGANISATION_ID`. `ref` uses the key-free
`https://api.ref.tools/mcp` endpoint and authenticates through OAuth or an
environment-backed `REF_TOOL_API_KEY` header. Secret values must not be embedded
in tracked or generated MCP configuration.

## Remote MCP (untrusted content)

`deepwiki` and `ref` are **remote SaaS** MCP servers. Treat tool results as
**untrusted external content**. Full boundary:
`docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md`.

## Decision: `ast-grep` vs `code-analyzer` (KEEP both)

| Server | Role |
| --- | --- |
| `ast-grep` | Structural code search / pattern match |
| `code-analyzer` | Lint/static analysis (Ruff, Vulture, type checkers) |

**Verdict (AI-audit #6664):** **KEEP** both with distinct roles.

## Новые MCP сервера

### deja (deja-vu v0.13.1)
- **Статус:** ✅ Работает
- **Описание:** Auto-recall настроен на root runtime contract `AGENTS.md`
- **Настройка:** `DEJA_AUTO_RECALL_PATH` указывает на `AGENTS.md` (repo root)
- **Обёртки:** `scripts/ai/mcp/mcp_deja_wrapper.sh` (Linux/WSL), `scripts/ai/mcp/mcp_deja_wrapper.ps1` (Windows)

### adr-analysis
- **Статус:** ✅ Работает
- **Описание:** Prompt-only режим для анализа Architecture Decision Records
- **Настройка:** `PROJECT_PATH` и `ADR_PATH` для анализа ADR в `docs/02-architecture/decisions`
- **Обёртки:** `scripts/ai/mcp/mcp_adr_analysis_wrapper.sh` (Linux/WSL), `scripts/ai/mcp/mcp_adr_analysis_wrapper.ps1` (Windows)

### mutmut
- **Статус:** ✅ Работает
- **Описание:** Mutation testing MCP сервер
- **Настройка:** `MUTMUT_PROJECT_PATH` для проекта
- **Установка:** `uvx --from git+https://github.com/wdm0006/mutmut-mcp@1e3b47ccaaa31f4c651d8e424b90d392d1c1ed90`
- **Обёртки:** `scripts/ai/mcp/mcp_mutmut_wrapper.sh` (Linux/WSL), `scripts/ai/mcp/mcp_mutmut_wrapper.ps1` (Windows)

Immutable pin обновляется только отдельным reviewed change: проверить новый
commit в upstream-репозитории, запустить mutmut MCP smoke и
`test_mutmut_git_dependency_is_pinned_consistently`, затем одновременно
заменить SHA в обеих обёртках и в этом документе. Ветки, теги и неприкреплённые
Git URL в runtime-командах запрещены.

### code-analyzer
- **Статус:** ✅ Работает
- **Описание:** Анализ кода с использованием Ruff, Vulture и type checkers
- **Настройка:** `PROJECT_PATH` для проекта
- **Установка:** `uvx mcp-server-analyzer`
- **Обёртки:** `scripts/ai/mcp/mcp_code_analyzer_wrapper.sh` (Linux/WSL), `scripts/ai/mcp/mcp_code_analyzer_wrapper.ps1` (Windows)

### github-actions
- **Статус:** ✅ Работает
- **Описание:** Анализ и генерация GitHub Actions workflows
- **Настройка:** Локальная установка в `~/github-actions-mcp/dist/index.js` или fallback на npx
- **Обёртки:** `scripts/ai/mcp/mcp_github_actions_wrapper.sh` (Linux/WSL), `scripts/ai/mcp/mcp_github_actions_wrapper.ps1` (Windows)

## Удалённые MCP
sonarqube
chembl
pubchem
pubmed
sequential-thinking
openaiDeveloperDocs
needle
docker-docs
dockerhub
pdf
paper-search
biomoltechDocs
mintlify

These servers are **retired** from the sanctioned portable inventory. Do **not**
re-enable them in recommended local defaults (`.devin/config.local.json`,
`.codex/settings.json`, `.cursor/mcp.json`, `.vscode/mcp.json`, or generated
overlays). `scripts/ai/codex/setup_mcp.py` keeps
`REMOVED_MCP_SERVER_NAMES` and will not emit them into tracked or generated
projections. Local operators who still have retired keys must remove them on
the next setup regeneration.

## Retired wrapper artifacts

The following wrapper files are retained only as reviewed compatibility
artifacts during the MCP retirement window and MUST NOT be registered in the
tracked MCP configs:

- `scripts/ai/mcp/mcp_docker_docs_wrapper.sh`
- `scripts/ai/mcp/mcp_dockerhub_wrapper.sh` (Linux/WSL),
  `scripts/ai/mcp/mcp_dockerhub_wrapper.ps1` (Windows)
- `scripts/ai/mcp/mcp_needle_wrapper.sh`
- `scripts/ai/mcp/mcp_paper_search_wrapper.sh`

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
