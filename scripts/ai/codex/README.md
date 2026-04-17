# scripts/ai/codex

Canonical Codex-facing setup and validation tooling.

## Scope

- Codex/Copilot MCP configuration
- Codex agent and skill synchronization
- AI skills layout validation
- Docs mirror validation for `.codex/skills`

## Entry points

```bash
python -m scripts.ai.codex --help
python -m scripts.ai.codex setup-mcp
python -m scripts.ai.codex setup-agents
python -m scripts.ai.codex setup-skills
python -m scripts.ai.codex check-skills
python -m scripts.ai.codex check-mirror
```

Historical entrypoints in `scripts/dev` and `scripts/ops` remain available as
compatibility facades during the consolidation window.
