# MCP Wrapper Redesign Prerequisites 2026-04-29

*Status: Supporting operational context*
*Date: 2026-04-29*

## Purpose

This note defines the minimum redesign prerequisites for any future attempt to
collapse, rename, or otherwise restructure the retained
`scripts/ai/mcp/*_wrapper.*` families.

It does **not** authorize a cleanup wave. It exists so future work starts from
the real contract boundary instead of treating wrapper filenames as incidental
implementation detail.

## Current Contract

Today `scripts/ai/codex/setup_mcp.py` is the source of truth for generated MCP
workspace configuration. It writes concrete server definitions into:

- `.mcp.json`
- `.vscode/mcp.json`
- `.gemini/settings.json`
- `~/.codex/config.toml`

For wrapper-backed servers, those generated configs currently store:

- concrete wrapper paths under `scripts/ai/mcp/`
- platform-specific suffixes (`.sh` or `.ps1`)
- shell command choice (`bash` or `powershell`)

That means the public runtime contract currently includes:

- exact wrapper stem names
- OS-specific wrapper suffixes
- repo-local wrapper placement
- server-specific launch semantics embedded in wrapper identity

## Why Generic Collapse Is Unsafe

The wrappers are not one transport family.

Observed launch classes in the current surface:

1. Docker gateway passthrough wrappers
2. Docker/image-backed wrappers with service-specific env and auth policy
3. Direct `npx` or remote endpoint wrappers
4. Adapter-backed wrapper for Neo4j memory protocol bridging

Because of that, a generic wrapper would need first-class metadata for:

- launch transport kind
- upstream server identity
- auth/env loading policy
- Docker/image invocation details
- adapter indirection requirements
- platform-specific shell rendering

Without that metadata model, any generic collapse would just move hidden logic
from filenames into an untracked implicit dispatcher.

## Required Metadata Model

Any redesign wave must introduce an explicit per-server metadata model in
`scripts/ai/codex/setup_mcp.py` or a dedicated adjacent module.

Minimum required fields:

- `server_name`
- `launcher_kind`
  - `docker_gateway`
  - `docker_image`
  - `npx_package`
  - `remote_http`
  - `adapter_bridge`
- `platform_entrypoints`
  - explicit POSIX and Windows launcher targets
- `env_policy`
  - none / repo-env / required-secrets / fallback-from-container / mixed
- `auth_requirements`
  - named credentials or tokens required for launch
- `docker_spec`
  - gateway server name or image + args if Docker-backed
- `adapter_target`
  - explicit adapter path when protocol translation is required
- `config_surfaces`
  - which generated configs receive the server
- `validation_contract`
  - which tests or smoke checks assert this server's generated shape

## Migration Gates

No wrapper redesign should start before all of these are true:

1. The metadata model exists and can render all current MCP servers without
   losing behavior.
2. Generated config outputs are updated in one wave together:
   - `.mcp.json`
   - `.vscode/mcp.json`
   - `.gemini/settings.json`
   - `~/.codex/config.toml`
3. Tests stop asserting raw wrapper stems where the redesign intends to replace
   them, and instead assert the new rendered contract.
4. Neo4j memory adapter bridging is represented explicitly, not hidden behind
   one special wrapper.
5. Windows and POSIX launcher behavior are both preserved under the new model.

## Safe Work Before Redesign

Allowed before a full redesign:

- extract repeated shell logic into support helpers
- improve family-level smoke tests
- add comments or metadata near generated config rendering
- strengthen docs around per-family launch semantics

Not allowed before redesign:

- rename wrapper stems
- delete `.ps1` companions because `.sh` seems canonical
- replace all wrappers with one dispatcher script
- change generated config shape independently from tests

## Recommended Next Implementation Slice

If this redesign is ever prioritized, the first safe implementation slice is:

1. add a structured server metadata table beside `_canonical_servers()`
2. render current configs from that table without changing any output paths
3. move family-specific launch behavior description into the metadata
4. only after output parity is proven, discuss wrapper-path simplification

This keeps the first wave parity-only and prevents a contract rewrite from
hiding inside a filename cleanup.
