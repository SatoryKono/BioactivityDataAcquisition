# Memory: py-doc-bot

Status: active navigational memory. Parent: `agent-memory.md`.

## Role reminder

- Sandbox: workspace-write within authorized scope.
- Behavior owner: `.codex/agents/py-doc-bot.md`.
- Entry skill: `.codex/skills/py-doc-bot/SKILL.md`.
- Output: canonical/mirror changes, claim evidence, generated status,
  validation, skips, and debt outcome.

## Navigation

- Documentation map: `docs/00-project/00-map.md`.
- Terminology: `docs/00-project/glossary.md`.
- ADR policy and records: `docs/02-architecture/decisions/`.
- Runtime ownership: `docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md`.
- Post-change checks: `POST_CHANGE_VALIDATION.md` and `python -m scripts.docs --help`.
- Diagram contracts: `docs/02-architecture/diagrams/README.md` and the routed
  diagram/observability skill.

## Checklist

1. Verify each claim against its canonical code/config/runtime/ADR owner.
1. Edit canonical source before mirrors or generated output.
1. Refresh derived artifacts only with their owner command.
1. Re-scan links, terminology, freshness, navigation, and runtime parity.
1. Do not preserve remembered counts or present inventory as normative debt.

Never change normative behavior through a mirror, increase a debt threshold,
or modify an `.env` file without explicit approval.
