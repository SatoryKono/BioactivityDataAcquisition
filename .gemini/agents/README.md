---
Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-03'
---

# Agent Catalog — BioETL (Gemini CLI)

*Статус: internal-published | Runtime registry (2026-04-03)*

This directory contains the canonical sub-agent definitions for the Gemini CLI runtime.

## Surface Note

- This is the **canonical runtime registry** for Gemini CLI.
- Logical profiles are implemented as tools available to the main Gemini CLI agent.
- For orchestration details, see [ORCHESTRATION.md](ORCHESTRATION.md).
- For runtime-specific invocation details, see [GEMINI-RUNTIME.md](GEMINI-RUNTIME.md).

## BioETL Core (8 active agents)

| Agent | Model | Role | Primary Responsibility |
|-------|-------|------|------------------------|
| `py-audit-bot` | opus | Compliance Gate | Code/architecture audit, RULES.md compliance |
| `py-plan-bot` | opus | Architect | Task planning, RF-* decomposition |
| `py-test-bot` | sonnet | Tester | Tests (baseline/final/retest), coverage, VCR |
| `py-config-bot` | sonnet | Config Engineer | YAML configs (pipeline/DQ/filter) |
| `py-debug-bot` | opus | Troubleshooter | RCA, bug fixes, regression debugging |
| `py-doc-bot` | sonnet | Technical Writer | Docs, ADR, CHANGELOG, Mermaid diagrams |
| `py-test-swarm` | opus | QA Orchestrator | Hierarchical testing (L1->L2->L3) |
| `py-review-orchestrator` | opus | Review Lead | Code review (S1-S8 stages) |

Repo-wide documentation audits are no longer routed through a dedicated
documentation-only agent entry; use the `documentation-audit` /
`documentation-cascade-audit` skill surfaces for that workflow.

## Specialist Reviewers (Reference)

These specialists are available as generic profiles for the `generalist` agent or
as manual prompt references.

| Agent | Role |
|-------|------|
| `sp-code-reviewer` | General-purpose code review |
| `sp-debugger` | Bug diagnosis, root cause analysis |
| `sp-refactoring-specialist` | Code refactoring |
| `sp-architect-reviewer` | Architecture evaluation |
| ... | (see `sp-*.md` files for more) |

## Related Files

- [ORCHESTRATION.md](ORCHESTRATION.md) — Multi-agent workflow
- [GEMINI-RUNTIME.md](GEMINI-RUNTIME.md) — Runtime tool mapping
- `docs/00-project/ai/agents/README.md` — Published mirror index
