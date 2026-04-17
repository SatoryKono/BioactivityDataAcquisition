# scripts/ai/codex

Canonical Codex-facing setup, launch, and validation tooling.

## Scope

- Codex/Copilot MCP configuration
- Codex agent and skill synchronization
- Codex interactive, full-auto, and headless launch flows
- Codex WSL diagnostics and setup verification launchers
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
python -m scripts.ai.codex launch --help
python -m scripts.ai.codex exec --help
python -m scripts.ai.codex headless --help
python -m scripts.ai.codex diagnose-wsl --help
```

Historical entrypoints in `scripts/dev` and `scripts/ops` remain available as
compatibility facades during the consolidation window.
