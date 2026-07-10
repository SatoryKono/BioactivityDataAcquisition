---
name: "py-audit-bot"
description: "Execute the BioETL py-audit-bot profile for baseline, final, or targeted audits of code, config, docs, architecture, runtime guidance, and regression risk. Use when the user asks for an audit/review gate or when orchestration requires an independent compliance check."
---

# py-audit-bot

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Primary profile: `../../agents/py-audit-bot.md`
- Team orchestration: `../../agents/ORCHESTRATION.md`
- Shared wrapper contract: [references/wrapper-contract.md](references/wrapper-contract.md)
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Shared project context: `../../../docs/00-project/ai/memory/agent-memory.md`
- Role memory: `../../../docs/00-project/ai/memory/memory-py-audit-bot.md`

## Trigger Scope

Use this wrapper for read-only baseline, final, or targeted audit work. It is
not the implementation profile; return findings, risk calls, missing tests,
architecture drift, and validation gaps.

## Workflow

1. Follow the shared wrapper contract.
1. Read and apply `../../agents/py-audit-bot.md`.
1. Classify the audit as `baseline`, `final`, or `targeted`.
1. Ground every finding in file:line evidence or a concrete command result.
1. Do not raise technical-debt budgets or create new exemptions.

## Expected Output

- Audit report path when a report is written:
  `reports/{LLM}/review_py-audit-bot_{YYYYMMDD}_{HHMM}_{phase}.md`.
- Findings first, ordered by severity, with exact references.
- Explicit residual risk and skipped checks.

## Validation

Use the smallest suite that matches the audited surface. Common gates include
architecture tests, docs drift checks, config validators, and targeted pytest
nodes named by the profile or touched files.

## Fallback

If `../../agents/py-audit-bot.md` is unavailable, stop and report runtime drift.
