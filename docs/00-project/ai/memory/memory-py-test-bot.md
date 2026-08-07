# Memory: py-test-bot

Status: active navigational memory. Parent: `agent-memory.md`.

## Role reminder

- Sandbox: workspace-write within authorized test scope.
- Behavior owner: `.codex/agents/py-test-bot.md`.
- Entry skill: `.codex/skills/py-test-bot/SKILL.md`.
- Output: scope/rationale, commands, outcomes, `FAIL-*` classification,
  coverage/regression evidence when applicable, skips, and residual risk.

## Navigation

- Test suites: `tests/unit/`, `integration/`, `architecture/`, `contract/`,
  `e2e/`, `performance/`, `security/`, and `smoke/` as applicable.
- Current thresholds and conventions: RULES and REQUIREMENTS, never memory.
- Canonical runner/help: repository test wrapper and `pytest --help`.
- HTTP recordings: `.codex/skills/vcr-record/` and sanitized fixtures.
- Structural conclusions: topology/governance evidence plus concrete failures.

## Checklist

1. Start with the narrowest meaningful node, then expand by changed behavior.
1. Record phase, environment, command, outcome, and baseline comparison.
1. Classify new, pre-existing, flaky, blocked, and environment failures.
1. Never report skipped/timed-out checks as passing or weaken a gate to pass.
1. Keep tests deterministic and credentials/sensitive payloads out of evidence.

Do not modify an `.env` file without explicit approval or increase any debt,
coverage, exemption, or threshold allowance.
