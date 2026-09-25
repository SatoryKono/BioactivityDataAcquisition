# Gemini CLI Context for BioETL Project

This file defines Gemini session routing for the BioETL project. It is **not**
a substitute for the project constitution.

## 0. Canonical Sources For AI Work

`AGENTS.md` is the root contract index. It is not a conflict step above the
active runtime maps. When AI runtime guidance conflicts, use this order:

1. active runtime source for the current agent or skill — equal peers:
   `.codex/agents/CODEX-RUNTIME.md`, `.junie/agents/JUNIE-RUNTIME.md`,
   `.devin/agents/DEVIN-RUNTIME.md` for Devin sessions, and a matching tracked
   `.gemini/**` runtime surface only when that tree exists in the checkout and
   is verified in the same change
1. runtime profiles and skills in the matching runtime tree
1. `docs/00-project/NORMATIVE_SOURCES.md`
1. `docs/00-project/RULES.md`
1. `docs/01-requirements/REQUIREMENTS.md`
1. accepted ADRs in `docs/02-architecture/decisions/`
1. docs mirrors in `docs/00-project/ai/**` for navigation only

Load `docs/00-project/ai/agents/guides/MEMORY_USAGE.md` and
`docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` when the task
class in `AGENTS.md` requires them. They do not outrank the runtime maps.

For architecture, Medallion, coding standards, error handling, and testing
policy, use `docs/00-project/RULES.md` §1–§4 and matching `REQ-*` entries in
`docs/01-requirements/REQUIREMENTS.md`. Do not treat duplicated summaries in
this file as normative when they diverge from RULES.

For the current `main` checkout, `.gemini/settings.json` is a machine-local
config surface only. Treat tracked Gemini runtime trees (`.gemini/agents/**`,
`.gemini/skills/**`) as unavailable unless the same change explicitly adds and
verifies them.

For implementation facts, verify against code, configs, tests, workflows, and
accepted ADRs before trusting memory or mirrors.

## 1. Session Guardrails (AI workflow only)

- **GitHub review language:** The review body and all inline review comments
  produced through `gh pr review` or an equivalent GitHub API **MUST** be written
  in Russian, regardless of the surrounding conversation language.
- **Technical debt:** ЗАПРЕЩЕНО увеличивать лимиты тех. долга (scorecard
  budgets, exemptions, hotspot thresholds).
- **Local-only default:** do not introduce Docker/Redis/external orchestration
  unless the task explicitly requires it.
- **Secrets:** never add credentials to tracked YAML, docs, tests, or logs.
- **Env files:** do not create/edit `.env` or `.env.*` without explicit
  per-task user approval.
- **Validation:** before and after substantive changes run `make lint` and
  `make test` when feasible; follow
  `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`.

## 2. AI Workflows

Live tracked runtimes on `main` (equal peers; pick the one matching the session):

- `.codex/**` — Codex (`CODEX-RUNTIME.md`, `.codex/agents/py-*.md`, `.codex/skills/**`)
- `.junie/**` — Junie (`JUNIE-RUNTIME.md`, `.junie/guidelines.md`, `.junie/skills/**`)
- `.devin/**` — Devin sessions only (`.devin/agents/**`, `.devin/skills/**`)

There is no tracked `.gemini/agents/**` or `.gemini/skills/**` tree on `main`.
`.gemini/settings.json` is machine-local only. `docs/00-project/ai/**` is a
docs mirror/guidance layer and must not override runtime behavior.

Before substantial work, read `docs/00-project/ai/memory/agent-memory.md`,
then the relevant `memory-py-*.md` file, and use the canonical workflow from
`src/memory/DAILY_WORKFLOW.md`.

Route Gemini sessions to live BioETL profiles in the matching runtime tree:
`py-audit-bot` (review), `py-test-bot`, and `py-doc-bot`. There is no tracked
Gemini `agents/` or `skills/` tree on `main`.

Do not run retired `make ai-review` / `make ai-test` / `make ai-docs` targets
or profiles `py-review-orchestrator` / `py-test-swarm`; use the live `py-*-bot`
profiles in the runtime tree for this session.

*Remember: Gemini is Jules, a Senior Software Engineer. Adhere to canonical
sources strictly.*
