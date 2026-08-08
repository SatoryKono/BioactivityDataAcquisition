# Memory: py-plan-bot

Status: active navigational memory. Parent: `agent-memory.md`.

## Role reminder

- Sandbox: read-only; planning does not authorize implementation.
- Behavior owner: `.codex/agents/py-plan-bot.md`.
- Entry skill: `.codex/skills/py-plan-bot/SKILL.md`.
- Output: bounded plan with scope, dependencies, validation, rollback, skips,
  and expected debt outcome; use `RF-*` for formal V3/V4 plans.

## Navigation

- Risk routing: `.codex/agents/ORCHESTRATION.md`.
- Target ownership: locate callers, tests, config, schemas, generators, docs,
  and mirrors through repository search.
- Architecture constraints: current RULES, requirements, and accepted ADRs.
- Boundary reminder: plans must not introduce direct
  `interfaces -> infrastructure` imports; route through Application or public
  Composition APIs.
- Broad structural evidence: topology and governance summary directories.
- Debt registries: scorecard and architecture exemption config.

## Checklist

1. State outcome, non-goals, authority, risk tier, and assumptions.
1. Map steps to real files/commands and an acyclic dependency order.
1. Separate implementation, tests, docs/mirrors, generated outputs, and closeout.
1. Include rollback for high-risk steps and exact approval boundaries.
1. Do not plan repo-wide work from counts alone or raise debt allowances.

V1/V2 may use a direct checklist; V3/V4 require explicit planning and
post-change gates.
