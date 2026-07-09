# MCP Governance

## Назначение
MCP используются как tooling-layer для AI-ассистентов.

## Ограничения
- MCP не являются частью ETL runtime
- Нельзя обходить UnifiedHTTPClient
- Нельзя писать в domain
- Code interpreter работает только в sandbox

## Активные MCP
memory, filesystem, fetch, github, context7, ast-grep, mcp-code-interpreter,
prometheus, grafana, mermaid,
brave-search,
docker, neo4j-cypher, neo4j-memory,
biomoltechDocs, mintlify, deepwiki

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

## Retired wrapper artifacts

The following wrapper files are retained only as reviewed compatibility
artifacts during the MCP retirement window and MUST NOT be registered in the
tracked MCP configs:

- `scripts/ai/mcp/mcp_docker_docs_wrapper.sh`
- `scripts/ai/mcp/mcp_dockerhub_wrapper.sh`
- `scripts/ai/mcp/mcp_needle_wrapper.sh`
- `scripts/ai/mcp/mcp_paper_search_wrapper.sh`
