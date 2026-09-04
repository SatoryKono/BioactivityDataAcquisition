---
id: prompt.config.validate
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- any
params:
- SCOPE
- MODE
- LANGUAGE
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/language-ru.md
- fragments/finding-schema.md
related_ssot:
- AGENTS.md
- .codex/agents/py-config-bot.md
- configs
anti_patterns:
- Editing .env
- Silent schema drift
- Raising quality budgets to pass gates
tags:
- config
- schema
- operator
summary: Config, schema, and contract validation or remediation (py-config-bot)
max_body_lines: 120
---
# BioETL config validate

Role: `py-config-bot`. Configs and schemas are SSOT; code must match.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | `configs/` and related schemas |
| `MODE` | `audit` \| `remediate` |
| `LANGUAGE` | `ru` |

## Method

1. Inventory YAML / JSON Schema / Pandera / `column_order` in SCOPE.
2. Prove drift with commands, not memory.
3. Remediate only when MODE=`remediate`; keep determinism and atomic writes.
4. Never create/edit `.env`. Never raise quality budgets.

## Output

`report.md` + `findings.json` under `reports/audit/config/`.
