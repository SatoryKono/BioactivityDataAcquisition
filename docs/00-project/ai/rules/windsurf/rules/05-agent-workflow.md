---
trigger: always_on
description: "BioETL AI agent workflow, validation, and guardrails"
---

# Agent Workflow (AGENTS.md)

**Canonical references:** `AGENTS.md`, `docs/00-project/NORMATIVE_SOURCES.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, `docs/02-architecture/decisions/`.

## Precedence

1. Runtime source: .codex/agents/ + .junie/agents/ + .devin/agents/ (equal peers); use .gemini/** only when tracked and verified
1a. docs/00-project/NORMATIVE_SOURCES.md
2. docs/00-project/RULES.md
3. docs/01-requirements/REQUIREMENTS.md
4. Accepted ADRs in docs/02-architecture/decisions/

## Before Editing

- Read `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Read `docs/00-project/ai/memory/agent-memory.md`
- Run `python -m memory.tooling.workflow pre-task ...` when applicable

## After Code Changes

Follow `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`:

- Re-scan impacted code, configs, docs, tests
- After `src/bioetl/**/*.py` changes: refresh `reports/quality/module-coverage-inventory.json`
- After markdown/docs changes that add, remove, or retarget local links, or that change `Owner:` / `Status:` / `Class:` headers: run `python -m scripts.docs generate-cleanup-inventory --update` and commit `docs/reports/generated/documentation-cleanup-inventory.{json,md}` with the docs change. `--check` reads the working tree, not HEAD; skipping `--update` fails `test_documentation_cleanup_inventory_check_passes` and stops `architecture-fast`
- Report checks run, skipped checks, mirror-sync status

## Hard Guardrails

- **Never increase technical-debt budgets** — debt may only shrink or stay unchanged; no new/widened linter or Sonar exclusions (`sonar.exclusions`, ignore lists, coverage globs)
- **Never edit `.env` files** without explicit per-task user approval documented in task/PR (generic “we can edit .env” does not count)
- **No secrets** in code, docs, configs, tests, logs, or tracked non-code artifacts — scan high-entropy strings, PEM blocks, credential URLs, token prefixes (`sk_live_`, `AKIA`, `ghp_`, `xoxb-`)
- **No secrets in tracked `configs/**` YAML** — secret-valued fields only: placeholders, `${ENV_VAR}`, or secret-manager refs; ordinary non-secret config values remain allowed
- **Do not weaken `.env` protections** — keep `.gitignore` patterns; do not COPY/ADD `.env` into Docker/CI artifacts; do not log entire env maps
- **No silent breaking changes** to CLI/API/schema contracts
- BioETL stays **local-only by default** (no Docker/Redis unless task requires it)
- After `src/bioetl/**/*.py` changes: refresh `reports/quality/module-coverage-inventory.json` (`source_tree_sha256` MUST change)
- After markdown link or `Owner:` / `Status:` / `Class:` header changes: `python -m scripts.docs generate-cleanup-inventory --update` in the same changeset

## Response Language

- Answer in Russian when the user writes in Russian
- The GitHub review body and all inline review comments produced through
  `gh pr review` or an equivalent GitHub API **MUST** be written in Russian,
  regardless of the surrounding conversation language
- Keep code, paths, identifiers, and API field names in original form
