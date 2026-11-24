# Codex Task Routing and Validation

*Status: internal-published (AI runtime guidance mirror)*

The canonical behavior source is `.codex/agents/CODEX-RUNTIME.md`, sections
`Common Task Routing`, `CI Evidence and PR Feedback`, and `Risk-Based Validation`.
This contributor-facing mirror does not redefine runtime behavior.

## Common requests

- Diagnose without fixing: use `py-debug-bot`; remain read-only.
- Implement a focused fix: implement directly and add `py-config-bot` only for
  existing config or schema work and run targeted lint and tests.
- Scaffold a pipeline for a new provider or entity with `new-pipeline`.
- Review the current diff: use `py-audit-bot` (`review`); perform no write action.
- For CI diagnosis, the parent retrieves the run, attempt, job, head SHA, and
  relevant log. Apply `py-debug-bot` to that evidence in read-only mode. The
  parent implements authorized remediations and reruns the failed check and a
  targeted regression.
- For existing PR feedback, use `github-pr-comments` when available. Record head,
  base, and review-thread state through authorized GitHub tools.
  Use `qodo-pr-resolver` for explicitly requested Qodo feedback and
  `gh-review-loop` for an authorized complete review cycle.
- Prepare a PR: use the parent workflow after the request authorizes publish
  actions. There is no live `create-pr` skill in `.codex/skills/`.
- Audit architecture debt: use `py-audit-bot` (`debt`); never increase debt
  budgets, exemption limits, hotspot thresholds, or family caps.

## Validation tiers

| Tier | Scope | Minimum |
| --- | --- | --- |
| V1 | documentation | full documentation link check, required drift and mirror checks, and cleanup inventory refresh and check as specified in `POST_CHANGE_VALIDATION.md` |
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
