---
id: prompt.audit.generic-nine.pack
version: 1.0.0
status: active
class: index
owner: BioETL Team
runtimes:
- any
tags:
- audit
- index
- operator
summary: Index of the nine-domain operator-paste audit kit (not runtime SSOT)
---
# Nine-domain audit pack

Operator **index** only. Runtime SSOT remains `.codex/**`, `.junie/**`, `.devin/**`.

| # | Prompt id | Card |
| --- | --- | --- |
| 1 | `prompt.docs.audit` | `library/doc/audit.md` |
| 2 | `prompt.audit.tests-system` | `library/test/system-audit.md` |
| 3 | `prompt.audit.tech-debt` | `library/audit/tech-debt.md` |
| 4 | `prompt.audit.repo-tree` | `library/audit/repo-tree.md` |
| 5 | `prompt.audit.github-actions` | `library/tests/cycle.md` |
| 6 | `prompt.audit.agents-runtime` | `library/audit/agents-runtime.md` |
| 7 | `prompt.audit.diagrams` | `library/audit/diagrams.md` |
| 8 | `prompt.audit.docs-pipeline` | `library/doc/pipeline.md` |
| 9 | `prompt.architecture.review` | `library/audit/architecture-review.md` |

Fan-out: `scripts/ai/grok/workflows/nine-domain-audit.rhai`. Orchestrator: `prompt.audit.orchestrator`.
