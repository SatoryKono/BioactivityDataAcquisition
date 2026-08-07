# Memory: py-debug-bot

Status: active navigational memory. Parent: `agent-memory.md`.

## Role reminder

- Sandbox: read-only; do not apply remediation.
- Behavior owner: `.codex/agents/py-debug-bot.md`.
- Entry skill: `.codex/skills/py-debug-bot/SKILL.md`.
- Output: `DBG-*` reproduction, root cause/confidence, ruled-out hypotheses,
  remediation guidance, regression commands, and unresolved risk.

## Navigation

- Failing test and adjacent fixtures/callers are the first evidence anchors.
- Architecture symptoms: current RULES/ADRs and `tests/architecture/`.
- Config/data symptoms: owning config, schema, generator, and contract tests.
- External I/O: sanitized recordings, adapter contract, timeout/retry policy.
- Structural escalation: current topology and governance evidence summaries.

## Checklist

1. Reproduce narrowly or document the exact blocker.
1. Classify product, test, environment, flaky, or pre-existing failure.
1. Test one falsifiable hypothesis per iteration.
1. Stop after five evidence-producing iterations and escalate uncertainty.
1. Return the smallest remediation proposal to a write-capable parent.

Do not recommend state deletion, threshold increases, or `.env` changes as a
shortcut. Never expose secrets from traces or local runtime state.
