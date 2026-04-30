# MCP_LOCAL_RUNTIME_CONFIG.md

*Status: internal-published (AI runtime config strategy)*

## Purpose

Document how BioETL treats MCP/runtime config files that embed machine-local
paths and how those files should be described in contributor guidance.

## Scope

This policy applies to:

- `.mcp.json`
- `.codex/settings.json`
- `.gemini/settings.json`
- `.codex/config.toml`
- `.codex/config-headless.toml`
- `.gemini/config.toml`

## Current Classification

| Surface | Status | Notes |
| --- | --- | --- |
| `.mcp.json` | active local runtime config | checked-in config contains absolute local paths by design |
| `.codex/settings.json` | active local runtime config | mirrors `.mcp.json` strategy for Codex runtime |
| `.gemini/settings.json` | active local runtime config | verified in local checkout on 2026-04-30 |
| `.codex/config.toml` | local runtime config | syntax/behavior should be validated locally |
| `.codex/config-headless.toml` | local runtime config | headless variant; same portability caveat |
| `.gemini/config.toml` | local runtime config | verified in local checkout on 2026-04-30 |
| `.claude/**` | unavailable in current checkout | not an active source for Codex/Gemini behavior in this program |

## Strategy

1. Treat these files as local runtime templates, not portable universal config.
1. Contributor docs MUST say when a config depends on machine-local absolute
   paths.
1. Do not silently rewrite checked-in paths during unrelated work.
1. If portability work is required, introduce an explicit template/strategy
   change instead of implying that the current files are portable.

## Required Documentation Language

When AI docs mention these configs, they SHOULD state:

- the file is an active local runtime config
- absolute local paths are expected in the current strategy
- local verification may be required for Gemini-specific settings
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
