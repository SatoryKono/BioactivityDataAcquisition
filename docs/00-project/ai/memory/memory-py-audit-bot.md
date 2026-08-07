# Memory: py-audit-bot

Status: active navigational memory. Parent: `agent-memory.md`.

## Role reminder

- Sandbox: read-only.
- Output: evidence-led findings with `AUD-*` IDs, severity, governing source,
  exact location, verification, remediation, residual risk, and skipped checks.
- Behavior owner: `.codex/agents/py-audit-bot.md`.
- Entry skill: `.codex/skills/py-audit-bot/SKILL.md`.

## Navigation

- Architecture/import rules: current RULES, accepted ADRs, `.importlinter`, and
  `tests/architecture/`.
- Config/schema rules: owning configs, schemas, generators, and config tests.
- Docs/runtime parity: ownership policy, drift checks, and runtime mirror gate.
- Structural claims: `docs/reports/evidence/project-file-structure/`,
  `project-package-topology/`, and `governance-signals/` summaries.
- Debt semantics: `configs/quality/debt_scorecard.yaml` and
  `configs/quality/architecture_metric_exemptions.yaml`.

## Checklist

1. Establish current baseline and scope.
1. Verify blockers twice when feasible.
1. Separate valid-by-design, pre-existing, environment, and introduced issues.
1. Do not infer debt from counts alone or raise any budget/threshold.
1. Report `improved`, `unchanged`, or `worsened` debt outcome.

Do not duplicate the import matrix, scoring table, thresholds, or command
catalog here; read their current canonical owners.
