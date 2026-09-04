---
id: prompt.audit.cyclic-pack
version: 1.1.0
status: deprecated
successor: prompt.audit.cycle
class: operator-paste
owner: BioETL Team
runtimes:
- any
params:
- N
- MODE
- LANGUAGE
includes:
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/git-safety.md
- fragments/orchestrator-guards.md
related_ssot:
- docs/00-project/ai/prompts/README.md
- docs/00-project/ai/prompts/library/audit/cycle.md
tags:
- audit
- cycle
- pack
- operator
summary: Deprecated pack — use prompt.audit.cycle + domains.yaml
max_body_lines: 40
---

# Deprecated: cyclic pack

Use [`prompt.audit.cycle`](cycle.md) plus `domains.yaml`.

```text
python -m scripts.ai.prompts compile --domain docs --profile audit-readonly
python -m scripts.ai.prompts render prompt.audit.cycle --param DOMAIN=docs --param SCOPE=docs/
```
