# Memory: py-config-bot

Status: active navigational memory. Parent: `agent-memory.md`.

## Role reminder

- Sandbox: workspace-write within authorized scope.
- Behavior owner: `.codex/agents/py-config-bot.md`.
- Entry skill: `.codex/skills/py-config-bot/SKILL.md`.
- Output: changed config/schema surfaces, generated parity, validation, skips,
  and debt outcome; use `CFG-*` only for a requested formal bundle.

## Navigation

- Hierarchy: `configs/base/`, `configs/providers/`, `configs/entities/`, and
  `configs/composites/`.
- Current schemas/generators: locate through repo search from the target config.
- Rules: current config sections in RULES plus applicable accepted ADRs.
- Validators: use the command exposed by `python -m scripts.schema --help` or
  the narrower owner documented beside the target.
- Debt: `configs/quality/debt_scorecard.yaml` and architecture exemptions.

## Checklist

1. Find consumers, schema, generator, tests, docs, and merge precedence.
1. Record current validator result before editing.
1. Edit the canonical owner; do not add legacy path overrides.
1. Refresh derived artifacts through their generator.
1. Run focused config/schema and related docs/architecture checks.
1. If the change also edits markdown links or `Owner:` / `Status:` / `Class:`
   headers, run `python -m scripts.docs generate-cleanup-inventory --update`
   in the same changeset.

Never place secrets or machine-local values in tracked config, change an `.env`
file without explicit approval, or increase a debt budget/threshold.
