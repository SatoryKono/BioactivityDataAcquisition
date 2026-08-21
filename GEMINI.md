# Gemini CLI Context for BioETL Project

This file defines Gemini session routing for the BioETL project. It is **not**
a substitute for the project constitution.

## 0. Canonical Sources For AI Work

Read these before planning or editing (in precedence order from `AGENTS.md`):

- `AGENTS.md`
- active equal-peer runtime maps: `.codex/agents/CODEX-RUNTIME.md` and
  `.junie/agents/JUNIE-RUNTIME.md` (with `.junie/guidelines.md`); use Devin
  maps under `.devin/agents/**` only in Devin sessions
- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- accepted ADRs in `docs/02-architecture/decisions/`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

For architecture, Medallion, coding standards, error handling, and testing
policy, use `docs/00-project/RULES.md` §1–§4 and matching `REQ-*` entries in
`docs/01-requirements/REQUIREMENTS.md`. Do not treat duplicated summaries in
this file as normative when they diverge from RULES.

For the current `main` checkout, `.gemini/settings.json` is a machine-local
config surface only. Treat tracked Gemini runtime trees (`.gemini/agents/**`,
`.gemini/skills/**`) as unavailable unless the same change explicitly adds and
verifies them.

When AI runtime guidance conflicts, use the list above in that order. For
implementation facts, verify against code, configs, tests, workflows, and
accepted ADRs before trusting memory or mirrors.

## 1. Session Guardrails (AI workflow only)

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

- `.codex/**` is the tracked runtime source of truth on `main`.
- `.gemini/settings.json` may exist for machine-local setup, but it does not
  prove a tracked Gemini behavior tree on `main`.
- `docs/00-project/ai/**` is a docs mirror/guidance layer and must not override
  runtime behavior.
- Before substantial work, read `docs/00-project/ai/memory/agent-memory.md`,
  then the relevant `memory-py-*.md` file, and use the canonical workflow from
  `src/memory/DAILY_WORKFLOW.md`.
- **Review:** use `py-audit-bot` (`review` / `debt` modes). There is no
  `make ai-review` target and no live `py-review-orchestrator`.
- **Tests:** use `py-test-bot`. There is no `make ai-test` target and no live
  `py-test-swarm`.
- **Docs:** use `py-doc-bot`. There is no `make ai-docs` target.

*Remember: Gemini is Jules, a Senior Software Engineer. Adhere to canonical
sources strictly.*
