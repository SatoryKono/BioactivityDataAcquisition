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

## Активные MCP
memory, filesystem, fetch, github, context7, ast-grep, mcp-code-interpreter,
prometheus, grafana, mermaid,
brave-search,
docker, neo4j-cypher, neo4j-memory,
deja, adr-analysis, mutmut, code-analyzer, github-actions,
deepwiki, ref

`ref` uses the key-free `https://api.ref.tools/mcp` endpoint. Local clients
authenticate through OAuth or, for Codex, an `env_http_headers` reference to
`REF_TOOL_API_KEY`. Ref API key values must not be embedded in tracked or
generated MCP configuration.

## Новые MCP сервера

### deja (deja-vu v0.13.1)
- **Статус:** ✅ Работает
- **Описание:** Auto-recall настроен в `.codex/AGENTS.md`
- **Настройка:** `DEJA_AUTO_RECALL_PATH` указывает на `.codex/AGENTS.md`
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
- **Установка:** `uvx --from git+...wdm0006/mutmut-mcp`
- **Обёртки:** `scripts/ai/mcp/mcp_mutmut_wrapper.sh` (Linux/WSL), `scripts/ai/mcp/mcp_mutmut_wrapper.ps1` (Windows)

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
