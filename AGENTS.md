# BioETL AI Runtime Entry Point

This file is the root operating contract for AI runtime surfaces in this
repository.

## Canonical Precedence

For AI runtime behavior and workflow conflicts, use this priority:

1. active runtime source for the current agent or skill — equal peers:
   - `.codex/agents/CODEX-RUNTIME.md`
   - `.junie/agents/JUNIE-RUNTIME.md`
   - `.devin/agents/DEVIN-RUNTIME.md` for Devin sessions
   - a matching tracked `.gemini/**` runtime surface only when that tree exists
     in the current checkout and is verified in the same change
1. runtime profiles and skills in the matching runtime tree
   (`.codex/agents/py-*.md`, `.codex/skills/**`, `.junie/agents/py-*.md`,
   `.junie/skills/**`, `.devin/agents/*/AGENT.md`, `.devin/skills/**`)
1. `docs/00-project/NORMATIVE_SOURCES.md` (normative stack index)
1. `docs/00-project/RULES.md`
1. `docs/01-requirements/REQUIREMENTS.md`
1. accepted ADRs in `docs/02-architecture/decisions/`
1. docs mirrors and helper AI docs in `docs/00-project/ai/**` for navigation
   and guidance only

Docs mirrors MUST NOT redefine runtime behavior on their own.

## Required AI Context

Before planning, auditing, or editing:

1. Read `docs/00-project/NORMATIVE_SOURCES.md`.
1. Read `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`.
1. Read `docs/00-project/ai/memory/agent-memory.md`.
1. Read the relevant `docs/00-project/ai/memory/memory-py-*.md` file when a
   role-specific memory sheet exists.
1. Use the canonical memory workflow from `src/memory/DAILY_WORKFLOW.md`
   through `python -m memory.tooling.workflow pre-task ...` and
   `python -m memory.tooling.workflow post-task ...`.

## Environment Configuration

All AI agents and skills MUST use tokens and parameters from the repository root
`.env` file. The `.env` file is machine-local and secret-bearing:

- **MCP integrations:** Use MCP server tokens from `.env` (e.g., `DEEPWIKI_API_KEY`,
  `DEEPWIKI_ORGANISATION_ID`, `CONTEXT7_API_KEY`, `NEEDLE_API_KEY`, etc.)
- **GitHub operations:** Use GitHub tokens from `.env` (e.g., `GITHUB_TOKEN`,
  `GITHUB_PERSONAL_ACCESS_TOKEN`, `GITHUB_CDX_PERSONAL_ACCESS_TOKEN`)
- **LLM providers:** Use API keys from `.env` (e.g., `OPENAI_API_KEY`, `GROK_API_TOKEN`)
- **Search providers:** Use search API keys from `.env` (e.g., `BRAVE_API_KEY`)
- **Code quality tools:** Use tool tokens from `.env` (e.g., `QODO_API_KEY`, `SONARQUBE_TOKEN`)
- **Docker registry:** Use Docker Hub credentials from `.env` (e.g., `DOCKER_API_KEY`,
  `DOCKER_USERNAME`, `HUB_PAT_TOKEN`)

**Env file guardrail:** Agents and contributors MUST NOT create, edit, rename, move,
overwrite, or delete any `.env` file without explicit per-task user approval. Reading
`.env` files is permitted. If a task requires changes to `.env`, the agent MUST stop
and request explicit user permission first.

For the current consolidated environment configuration, see the consolidation
history in `docs/env/` (note: `docs/env/consolidated.env` was moved to `.env`).

## Response Language

- By default, answer the user in Russian when the user writes in Russian.
- Keep code, commands, file paths, identifiers, API field names, and other
  technical literals in their valid original form.
- Switch away from Russian only when the user explicitly requests another
  language.

## Post-Change Validation

For any write-capable task, follow
`docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`.

Minimum expectation:

1. Re-scan impacted code/config/doc/runtime surfaces before finalizing.
1. Use repo search plus memory/evidence anchors to find related tests, docs,
   contracts, configs, and workflows.
1. Edit runtime source first, then sync docs mirrors when behavior or
   contributor guidance changed.
1. **Runtime mirror parity:** after changes under `.codex/agents/**`,
   `.codex/skills/**`, `.junie/agents/**`, or `.junie/skills/**`, run
   `bash scripts/ai/junie/check_junie_mirror.sh --check` and report the
   result. Divergences MUST be resolved before submit.
1. After changes under `src/bioetl/**/*.py`, refresh
   `reports/quality/module-coverage-inventory.json` field `source_tree_sha256`
   via `python -m scripts.engineering.qa report-module-coverage --allow-missing-coverage-xml`
   and run the architecture hash guard when feasible.
1. Report checks run, skipped checks, and mirror-sync status explicitly.

## Guardrails

- **Root scratch ban (RH5/RH6):** do not create root-level `_tmp_*.py`, `/_cr_*.py`,
  `/_publish_*.py`, ad-hoc `test_*.py`, or Windows device-name files such as
  `nul` / `NUL`. Prefer `scripts/**` or `reports/**`. Tracked root must stay
  ≡ `.github/root-allowlist.txt` (37 files). Local clutter: registry +
  `scripts/engineering/repo/cleanup_root_local_clutter.py`. See
  `docs/00-project/governance/root-local-clutter-cleanup.md`.
- BioETL remains local-only by default; do not introduce Docker, Redis, or
  external orchestration requirements unless the task explicitly requires them.
- `.codex/**` is the canonical Codex runtime source.
- `.junie/**` is the canonical JetBrains Junie runtime source and an equal peer
  to `.codex/**`. Tracked runtime subtrees MUST remain covered by the
  Codex–Junie parity contract; machine-local Junie history/state/cache remains
  untracked.
- `.devin/agents/**` and `.devin/skills/**` are the canonical tracked Devin
  runtime sources. Devin-specific behavior starts there and remains subordinate
  to the repository-wide governance stack; it MUST NOT be silently replaced by
  a Codex-only profile.
- `.gemini/settings.json` may exist as a machine-local Gemini config surface,
  but the current `main` checkout does not contain a tracked Gemini
  `agents/` or `skills/` runtime tree.
- Treat `docs/00-project/ai/**` Gemini references as mirrors or historical
  guidance unless a future task adds and verifies tracked `.gemini/agents/**`
  or `.gemini/skills/**` surfaces on `main`.
- `.claude/**` is not an active runtime source for Codex/Junie/Gemini behavior in
  this change program and is treated as unavailable until a local checkout
  proves otherwise.
- `docs/00-project/ai/memory/mcp-memory.json` and
  `docs/00-project/ai/memory/gemini-memory.json` are machine-readable memory
  artifacts, not human source of truth.
- **УВЕЛИЧИВАТЬ бюджеты тех. долга ЗАПРЕЩЕНО** — технический долг может только уменьшаться или оставаться неизменным, увеличение бюджетов запрещено.

## Dashboard Skill Routing

- Monitoring/Grafana is **optional** (ADR-010). Do **not** start
  `docker-compose.monitoring.yml` unless the user explicitly requests
  dashboard/render work. Default Docker surface is **main only** (health on
  `:8000`). Loki, Tempo, and Quarantine Explorer UI were removed.
- For BioETL Grafana screenshot refresh, render preflight, panel-audit,
  render-blocker diagnosis, dashboard JSON, query, variable, navigation, or
  operator-facing UX work, agents **SHOULD** use
  `.codex/skills/observability-dashboard/`.
- For Prometheus alert or recording-rule edits, tests, or query diagnosis,
  agents **SHOULD** use `.codex/skills/observability-prometheus/`.

## Related Files

- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md`

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Reading `.env` files is permitted.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.
