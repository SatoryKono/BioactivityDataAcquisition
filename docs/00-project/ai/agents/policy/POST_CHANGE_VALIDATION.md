# POST_CHANGE_VALIDATION.md

*Status: internal-published (AI runtime validation policy)*

## Purpose

Define the minimum validation protocol after AI-assisted changes to code,
configs, docs, contracts, prompts, diagrams, and runtime instruction surfaces.

## Applies To

- production code
- tests
- configs
- docs and diagrams
- prompts
- runtime AI files in `.codex/**`, `.gemini/**`, and `AGENTS.md`

## Required Protocol

1. Re-scan impacted surfaces before finalizing.
1. Use memory plus repo search to locate related tests, docs, contracts,
   configs, workflows, diagrams, reports, golden data, and mirrors.
1. Run the smallest sufficient verification set for the touched surface.
1. If runtime behavior changed, update the runtime tree first and the docs
   mirror second.
1. Record executed checks, skipped checks, and unresolved uncertainty in the
   final report.

## Minimum Surface Checks

### Runtime AI files

- verify canonical links and stale-path cleanup
- verify runtime-source-first precedence language remains aligned across
  `AGENTS.md`, runtime maps, and memory policy
- run `python -m scripts.docs check-drift --runtime-mirrors --freshness`
- run the AI-surface drift check when available in `scripts.docs check-drift`

### Docs, guides, prompts, diagrams

- verify doc claim surfaces and cited runtime/code/config targets
- verify runtime/mirror consistency when AI guidance or published examples changed
- run `python -m scripts.docs check-links --links --specs --configs`
- run `python -m scripts.docs check-drift --runtime-mirrors --freshness`

### Code and tests

- locate impacted tests before deciding validation scope
- include golden, architecture, contract, and regression tests when the touched
  surface can affect them
- run targeted unit/integration/architecture tests appropriate to the change

### Configs and contracts

- locate related config validators, contract tests, and docs references
- run the narrowest relevant config/contract validation commands

### MCP runtime settings and local-only surfaces

- validate JSON/TOML syntax of changed runtime config files
- confirm local-only classification and portability notes stay accurate
- do not silently rewrite machine-specific paths without an explicit strategy

## Final Report Requirements

The closeout MUST include:

1. changed files or change areas
1. related tests, golden tests, architecture tests, contract tests, docs, ADRs,
   diagrams, configs, and reports found through memory plus repo search
1. checks run
1. command outcomes
1. skipped checks with reason and the exact command to run later
1. mirror-sync status when AI runtime files or docs mirrors changed
1. explicit callout if any stale guidance remains for follow-up

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
