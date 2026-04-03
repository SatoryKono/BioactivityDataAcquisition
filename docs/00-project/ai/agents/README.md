---
Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-03'
---

# Agent Catalog — BioETL (Mirror)

*Статус: internal-published | Docs mirror (2026-04-03)*

Этот каталог является зеркалом документации по агентам для разных рантаймов AI в BioETL.

## Surface Note

- Это **публикуемое зеркало** документации.
- Актуальные runtime-определения живут в `.gemini/agents/` (для Gemini CLI).
- Логические профили `py-*` реализованы как инструменты в Gemini runtime.

## BioETL Core (8 активных агентов)

| Agent | Role | Primary Responsibility |
|-------|------|------------------------|
| `py-audit-bot` | Compliance Gate | Code/architecture audit, RULES.md compliance |
| `py-plan-bot` | Architect | Task planning, RF-* decomposition |
| `py-test-bot` | Tester | Tests (baseline/final/retest), coverage, VCR |
| `py-config-bot` | Config Engineer | YAML configs (pipeline/DQ/filter) |
| `py-debug-bot` | Troubleshooter | RCA, bug fixes, regression debugging |
| `py-doc-bot` | Technical Writer | Docs, ADR, CHANGELOG, Mermaid diagrams |
| `py-test-swarm` | QA Orchestrator | Hierarchical testing (L1->L2->L3) |
| `py-review-orchestrator` | Review Lead | Code review (S1-S8 stages) |

## Related Files

- [ORCHESTRATION.md](agents/ORCHESTRATION.md) — Multi-agent workflow
- [AGENT.md](guides/AGENT.md) — Core Engineering Guide
- [GEMINI.md](guides/GEMINI.md) — Gemini CLI specific guide
