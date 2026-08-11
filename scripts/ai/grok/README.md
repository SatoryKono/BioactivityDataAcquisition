# Grok operator scripts

| Script | Purpose |
| --- | --- |
| `install_skills.ps1` | Copy tracked skills from `docs/00-project/ai/grok/skills/` into `~/.grok/skills` or project `.grok/skills` |
| `prepare_nine_domain_audits.ps1` | Render nine-domain audit operator prompts into `reports/audit-runs/<run_id>/prompts/` (does not run audits; pairs with `.grok/workflows/nine-domain-audit.rhai`) |

MCP dual-config apply remains under `scripts/ops/runtime/mcp/apply-shared-to-grok.ps1`.

See `docs/00-project/ai/grok/README.md` and `docs/00-project/ai/agents/guides/grok-operator-runbook.md`.
