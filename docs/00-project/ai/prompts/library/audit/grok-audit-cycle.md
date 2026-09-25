---
id: prompt.audit.grok-cycle
version: 2.2.0
status: archived
successor: prompt.audit.cycle
class: historical
owner: BioETL Team
runtimes:
- grok
- codex
- any
params:
- REPO
- BASE
- WORK_BRANCH
- SCOPE
- MODE
- CYCLE_COUNT
- AUDIT_MODE
- REQUIRE_GH_TRACKING
- LANGUAGE
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/language-ru.md
related_ssot:
- AGENTS.md
- docs/00-project/NORMATIVE_SOURCES.md
- docs/00-project/ai/agents/guides/MEMORY_USAGE.md
- docs/00-project/ai/agents/guides/grok-operator-runbook.md
- docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
- Nine simultaneous Principal roles
- Full RULES/ADR dump in the prompt
- CYCLE_COUNT=5 with mandatory empty cycles
- 24-section mandatory report outline every time
- Closing issues without code/evidence on origin/main
tags:
- audit
- grok
- operator
summary: Archived pointer — use prompt.audit.cycle
max_body_lines: 40
---
# Archived: grok audit cycle

Use [`prompt.audit.cycle`](cycle.md).

```text
python -m scripts.ai.prompts render prompt.audit.cycle --param DOMAIN=docs --param SCOPE=docs/
```
