---
id: prompt.debug.isolate
version: 1.0.0
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
anti_patterns:
- Applying fixes in debug mode
- Speculative root cause without reproduction
tags:
- debug
- operator
summary: Reproduce, isolate, root-cause (py-debug-bot) — read-only
max_body_lines: 120
---
# BioETL debug isolate

Role: `py-debug-bot`. Read-only: no patches.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | failing test / command / path |
| `MODE` | `debug` |
| `LANGUAGE` | `ru` |

## Method

1. Reproduce with a minimal command.
2. Isolate the first failing invariant (file + line / symbol).
3. State root cause + confidence. List remediation options; do not apply them.
4. Name exact regression checks for the write-capable parent.

## Output

Reproduction, root cause, confidence, remediation options, checks.
No `git commit`. No `.env` edits.
