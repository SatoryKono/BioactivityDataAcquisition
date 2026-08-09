# Agent Memory — Navigation Entry Point

## Evaluation Metadata
- **Category:** Memory Sheets
- **Weighted Score:** 7.88 / 10
- **Overall Rating:** High
- **Path:** docs/00-project/ai/memory/agent-memory.md

## Evaluation Breakdown
- Clarity: 9/10 (weight: 0.15)
- Completeness: 8/10 (weight: 0.15)
- Specificity: 7/10 (weight: 0.12)
- Context: 9/10 (weight: 0.10)
- Guardrails: 7/10 (weight: 0.10)
- Maintainability: 8/10 (weight: 0.08)
- Reusability: 8/10 (weight: 0.08)
- Error Handling: 6/10 (weight: 0.08)
- Validation: 6/10 (weight: 0.07)
- Documentation: 9/10 (weight: 0.07)

## Original Content

______________________________________________________________________

Version: 2.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Last verified: '2026-08-07'

______________________________________________________________________

# Agent memory — navigation entry point

This file is a compact navigation aid, not a behavioral or governance source.
When memory conflicts with the current checkout, follow the precedence in
`AGENTS.md` and `docs/00-project/NORMATIVE_SOURCES.md`.

## Minimum task bootstrap

Before planning, auditing, or editing:

1. Read `AGENTS.md`.
1. Read `docs/00-project/NORMATIVE_SOURCES.md` and select only the rules,
   requirements, ADRs, and policies relevant to the task.
1. Read `docs/00-project/ai/agents/guides/MEMORY_USAGE.md` and this file.
1. If using a named role, read its profile, wrapper skill, and matching
   `memory-py-*.md` sheet.
1. Run the `pre-task` command from `src/memory/DAILY_WORKFLOW.md`.

V1/V2 tasks use a direct single-agent route unless the user or an active
contract requires more. V3/V4 tasks use explicit planning and the orchestration
and post-change gates in `.codex/agents/ORCHESTRATION.md`.

Role memory sheets: `memory-py-audit-bot.md`, `memory-py-config-bot.md`,
`memory-py-debug-bot.md`, `memory-py-doc-bot.md`, `memory-py-plan-bot.md`, and
`memory-py-test-bot.md`.

## Canonical owner map

| Question | Read |
| --- | --- |
| Runtime precedence and safety | `AGENTS.md` |
| Normative stack | `docs/00-project/NORMATIVE_SOURCES.md` |
| Engineering rules | `docs/00-project/RULES.md` |
| Testable requirements | `docs/01-requirements/REQUIREMENTS.md` |
| Architecture decisions | `docs/02-architecture/decisions/` |
| Codex routing | `.codex/agents/CODEX-RUNTIME.md`, `.codex/agents/ORCHESTRATION.md` |
| Role behavior | `.codex/agents/py-*.md` |
| Skill entry contracts | `.codex/skills/**` |
| Post-change obligations | `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` |
| Memory lifecycle | `src/memory/DAILY_WORKFLOW.md` |

Docs under `docs/00-project/ai/**` are mirrors/navigation unless an ownership
policy explicitly makes a file canonical. Runtime behavior is changed in its
active runtime source first and mirrors are synchronized afterward.

## Repository navigation

- Product code: `src/bioetl/`
- Tests: `tests/`
- Configuration: `configs/`
- Architecture evidence: `docs/reports/evidence/`
- Quality/debt governance: `configs/quality/`, `reports/quality/`
- Runtime tooling: `scripts/ai/`, `scripts/ops/`
- Documentation map: `docs/00-project/00-map.md`
- Glossary: `docs/00-project/glossary.md`

Use repository search and current generators/checkers. Do not rely on memory for
file counts, provider counts, ADR ranges, coverage thresholds, command aliases,
or current dependency versions.

## Platform-specific Python environments

- On native Windows and in PowerShell, agents MUST use the repository-local
  `.venv-win` environment. Activate it with
  `.\.venv-win\Scripts\Activate.ps1` or invoke
  `.\.venv-win\Scripts\python.exe` directly.
- Do not reuse a Linux/WSL `.venv` from Windows. Create or refresh the Windows
  environment with `.\scripts\engineering\dev\setup_env_windows.ps1`.
- WSL/Linux agents must continue to follow the platform-specific environment
  guidance in `docs/03-guides/getting-started.md`; `.venv-win` is reserved for
  native Windows processes.

## Durable invariants to verify at source

- Respect layer boundaries and constructor injection.
- Direct `interfaces -> infrastructure` imports are forbidden; interfaces route
  through Application services or public Composition entrypoints.
- Preserve deterministic writes and current config/schema contracts.
- Keep the default BioETL runtime local-only; optional infrastructure remains
  opt-in.
- Do not expose secrets or sensitive data in code, config, recordings, logs, or
  reports.
- Do not create or modify `.env` files without explicit per-task approval.
- Technical-debt budgets, exemptions, thresholds, and hotspot caps may not be
  increased.
- Preserve unrelated worktree changes and use canonical generators for derived
  artifacts.

These bullets are reminders only; cite and apply the current normative source.

## Evidence anchors

For repo-wide structural claims, start at:

- `docs/reports/evidence/project-file-structure/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/SUMMARY.md`
- `docs/reports/evidence/governance-signals/SUMMARY.md`

Package/file count alone is descriptive, not proof of debt. Prefer current
family-level topology plus governance signals and executable checks.

## Memory loop and closeout

Use the canonical commands and identity variables documented in
`src/memory/DAILY_WORKFLOW.md`. Episodic records belong under
`src/memory/episodic/`; durable lessons require curated promotion. Never write
secrets, credentials, raw sensitive payloads, or machine-specific tokens into
memory.

After write-capable work:

1. Re-scan touched and related surfaces.
1. Run proportionate validation and required mirror/generator checks.
1. Run the canonical `post-task` workflow.
1. Report commands/results, exact skips, mirror status, and debt outcome as
   `improved`, `unchanged`, or `worsened`.

`worsened` is not made acceptable by raising a budget. If a hard guardrail
would be violated, stop and escalate.
