---
id: prompt.debug.isolate
version: 1.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- any
params:
- SCOPE
- MODE
- LANGUAGE
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/language-ru.md
- fragments/orchestrator-guards.md
- fragments/finding-schema.md
related_ssot:
- AGENTS.md
- .codex/agents/py-debug-bot.md
- .codex/agents/CODEX-RUNTIME.md
- docs/05-operations/runbooks/generated-artifact-drift-workflow.md
anti_patterns:
- Applying fixes in debug mode
- YAML/JSON baseline edits in debug MODE
- Speculative root cause without reproduction
- Using `prompt.audit.github-actions` for S7-d telemetry pins
tags:
- debug
- operator
summary: Reproduce, isolate, root-cause (py-debug-bot) — read-only
max_body_lines: 120
---
# BioETL debug isolate

Role: `py-debug-bot`. Read-only: no patches and no baseline YAML/JSON edits.
Write-capable parent applies refresh (`prompt.tests.fix-retest`).

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | job URL / pytest nodeid / command |
| `MODE` | `debug` |
| `LANGUAGE` | `ru` |

## Method

1. Reproduce: parent `gh run view` / job log, or the failing nodeid locally.
2. Classify generated-artifact family via
   `docs/05-operations/runbooks/generated-artifact-drift-workflow.md`
   (S7-d telemetry vs remote-main vs test-governance). Do not copy SHA
   between families.
3. Isolate the first failing invariant (file + line / symbol).
4. State root cause + confidence. List exact refresh commands; do not run
   `--update` or edit pins in this MODE.
5. Name exact regression checks for the write-capable parent
   (`pytest` nodeid and/or `--check`).

## Output

Reproduction, root cause, confidence, remediation options, checks.
No `git commit`. No `.env` edits. No baseline edits.
