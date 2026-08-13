# Codex Task Routing and Validation

*Status: internal-published (AI runtime guidance mirror)*

The canonical behavior source is `.codex/agents/CODEX-RUNTIME.md`, sections
`Common Task Routing` and `Risk-Based Validation`. This contributor-facing
mirror does not redefine runtime behavior.

## Common requests

- Diagnose without fixing: use `py-debug-bot`; remain read-only.
- Implement a focused fix: implement directly and add `py-config-bot` only for
  config impact; run targeted lint and tests.
- Review the current diff: use `py-audit-bot` (`review`); perform no write action.
- Diagnose CI: use `py-debug-bot` (read-only). Implement the remediations in
  the parent workflow, then rerun failed checks and a targeted regression.
- Prepare a PR: use the parent workflow after the request authorizes publish
  actions. There is no live `create-pr` skill in `.codex/skills/`.
- Audit architecture debt: use `py-audit-bot` (`debt`); never increase debt
  budgets, exemption limits, hotspot thresholds, or family caps.

## Validation tiers

| Tier | Scope | Minimum |
| --- | --- | --- |
| V1 | documentation | targeted links/drift and required mirror sync |
| V2 | focused code/tooling | targeted Ruff and related unit tests |
| V3 | configuration/runtime contract | schema/contract checks and related tests |
| V4 | broad/architecture | architecture gates, lint/type checks, relevant broad tests |

Final reports list checks run, skipped checks and follow-up commands, mirror
status, and the technical-debt outcome. Selecting a lower tier never disables
an applicable mandatory gate.

## Guardrails

- Templates never expand user authorization.
- `.codex/**` remains the Codex runtime source of truth.
- Do not create or modify `.env` files without explicit per-task approval.
- Monitoring and Docker remain optional.
