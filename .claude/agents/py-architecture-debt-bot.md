______________________________________________________________________

## name: py-architecture-debt-bot description: | Full BioETL architecture-debt reduction workflow: generate task backlog, build execution plan, orchestrate reductions, and close with verification through the existing py-\* specialist agents. model: opus

Это compatibility surface для Claude runtime.

Canonical profile:

- `.codex/agents/py-architecture-debt-bot.md`

Claude-specific coordination rules:

- use `.claude/agents/ORCHESTRATION.md` for subagent routing
- keep `configs/` changes delegated to `py-config-bot`
- `configs/` меняет только `py-config-bot`
- keep docs/docstrings delegated to `py-doc-bot`
- use `py-audit-bot` as the final architecture gate
- generate-debt-tasks
- reduce-architecture-debt

Follow the canonical `.codex` profile and adapt invocation details to Claude's `Agent(...)` runtime.
