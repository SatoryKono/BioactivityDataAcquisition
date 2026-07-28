# MCP wrapper deep audit 2026-04-29

*Status: Supporting operational context*
*Date: 2026-04-29*

## Purpose

This note extends the earlier
`mcp-wrapper-contract-audit-2026-04-28.md` with a body-level classification of
the retained MCP wrapper surface under `scripts/ai/mcp/`.

## Scope

Reviewed evidence:

- `scripts/ai/codex/setup_mcp.py`
- `scripts/ai/mcp/__main__.py`
- representative wrapper bodies across all retained families
- support helpers:
  - `scripts/ai/mcp/support/load_repo_env.sh`
  - `scripts/ai/mcp/support/docker_cli_resolver.sh`
- tests:
  - `tests/architecture/test_dev_setup_copilot_codex_mcp_consolidation.py`
  - `tests/unit/scripts/test_setup_copilot_codex_mcp.py`
  - `tests/unit/scripts/ops/test_neo4j_memory_mcp_adapter.py`

## Inventory

The retained runtime contract currently consists of:

- 16 `_wrapper` stems with `.sh` and `.ps1` platform pairs
- 1 adjacent named pair, `github-mcp-wrapper.{sh,ps1}`, that does not match the
  underscore naming pattern but is part of the same generated config contract

That is 17 named wrapper families and 34 concrete wrapper files.

## Generated config dependency

`scripts/ai/codex/setup_mcp.py` generates MCP server entries for:

- `.mcp.json`
- `.vscode/mcp.json`
- `.gemini/settings.json`
- `~/.codex/config.toml`

For wrapper-backed servers, the generated config stores concrete wrapper paths,
not abstract server metadata. The public contract therefore includes:

- exact wrapper stem names
- OS-specific suffix selection (`.sh` vs `.ps1`)
- shell command selection (`bash` vs `powershell`)
- repo-local path resolution under `scripts/ai/mcp/`

The architecture and unit tests lock this shape explicitly.

## Family map

### 1. Docker MCP gateway passthrough wrappers

Families:

- `mcp_docker_wrapper`
- `mcp_docker_docs_wrapper`
- `mcp_context7_wrapper`
- `mcp_paper_search_wrapper`
- `mcp_chembl_wrapper`
- `mcp_pubchem_wrapper`
- `mcp_pubmed_wrapper`
- `mcp_mermaid_wrapper`

Observed behavior:

- resolve Docker CLI per platform
- dispatch to `docker mcp gateway run --servers <name> --transport stdio`
- preserve named server identity in the wrapper path itself

Why they are not generic aliases:

- generated config points at concrete wrapper filenames
- the wrapper name encodes the upstream gateway server identity
- platform-specific shell targets are part of the tested contract

### 2. Image-backed wrappers with repo env or credential policy

Families:

- `mcp_dockerhub_wrapper`
- `mcp_prometheus_wrapper`
- `mcp_grafana_wrapper`
- `mcp_brave_search_wrapper`
- `mcp_sonarqube_wrapper`

Observed behavior:

- load repo-local `.env` data
- apply service-specific required credentials or defaults
- construct different `docker run` environments per server
- in some cases, derive fallback credentials from local container state

Examples:

- `mcp_grafana_wrapper.sh` falls back to Grafana container env inspection
- `mcp_prometheus_wrapper.sh` injects URL and optional auth material
- `mcp_sonarqube_wrapper.sh` enforces token plus org/URL semantics
- `mcp_dockerhub_wrapper.*` enforces Docker Hub username/token requirements
- `mcp_brave_search_wrapper.*` requires `BRAVE_API_KEY`

Why they are not generic aliases:

- each wrapper owns different validation and fallback rules
- the runtime environment surface differs per server
- replacing them with one generic launcher would require a new server metadata
  layer, not a filename cleanup

### 3. Direct npx or remote wrappers

Families:

- `github-mcp-wrapper`
- `mcp_needle_wrapper`
- `mcp_neo4j_cypher_wrapper`

Observed behavior:

- `github-mcp-wrapper.*` loads repo env, preserves a legacy token alias, and
  invokes `@modelcontextprotocol/server-github`
- `mcp_needle_wrapper.*` loads repo env and forwards auth headers to a remote
  MCP endpoint
- `mcp_neo4j_cypher_wrapper.sh` resolves Neo4j auth fallbacks, manages local
  Node path hints, and launches `@daanrongen/neo4j-mcp`

Why they are not generic aliases:

- they are not all Docker-backed
- they do not share one transport model
- they embed server-specific credential adaptation and upstream launcher policy

### 4. Adapter bridge wrapper

Family:

- `mcp_neo4j_memory_wrapper`

Observed behavior:

- loads repo env and Neo4j credential fallbacks
- then routes the upstream server through
  `scripts/ai/mcp/neo4j_memory_mcp_adapter.py`
- the adapter bridges framed MCP stdio expected by repo tooling to the
  upstream line-delimited JSON protocol

Why it is special:

- this is not just process launch
- it is a protocol bridge with dedicated tests
- collapsing it into a generic wrapper would still require retaining a special
  adapter path somewhere in the contract

## Tested invariants

Current tests lock these properties:

1. The generated workspace config contains the expected MCP server set.
2. Wrapper-backed servers resolve to exact named wrapper stems with the
   platform-appropriate suffix.
3. GitHub wrapper env-loading and legacy token compatibility remain intact.
4. Neo4j memory wrapper continues to route through the dedicated adapter.

These are file-identity and behavior contracts, not just convenience tests.

## Decision

Retain all current MCP wrapper families as contract-bound runtime surfaces.

The correct abstraction boundary today is:

- `setup_mcp.py` owns generated config shape
- named wrappers own per-server launch semantics
- support helpers own shared env and Docker resolution
- dedicated adapters own protocol translation where needed

## Safe improvements

- factor repeated shell logic into support helpers
- improve wrapper-specific smoke tests
- document family-level behavior more explicitly
- add generated-config comments or metadata that explain why a server uses a
  named wrapper

## Redesign prerequisites

Do not attempt generic wrapper collapse unless all of the following are done in
one dedicated wave:

1. Introduce a new canonical server metadata model in `setup_mcp.py`.
2. Encode per-server launch type, auth policy, env loading, and adapter needs
   in that model.
3. Redesign generated config outputs and their tests together.
4. Preserve OS-specific launcher behavior for both shell families.
5. Replace the Neo4j memory adapter path with an explicit first-class concept,
   not an incidental side effect.

## Unsafe moves

- Do not merge all wrappers into one generic script.
- Do not rename wrapper stems independently of generated config and tests.
- Do not delete wrapper pairs because their bodies look similar.
- Do not treat the Docker gateway family as proof that the whole directory is
  mechanically deduplicable.
