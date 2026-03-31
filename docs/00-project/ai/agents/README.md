---
Version: 1.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-31'
---

# AI Agents Context

*Статус: internal-published (Internal / Extended)*

Этот каталог содержит документацию по агентам для разных рантаймов AI в BioETL.

## Surface Types

- **Runtime source**: live orchestration and profile behavior live in runtime
  trees such as `.claude/agents/` and `.codex/agents/`.
- **Published docs mirror**: `docs/00-project/ai/agents/` keeps discoverable
  mirrors, guides, policy notes, and runtime-facing helper docs.
- **Guides**: assistant-facing operating instructions under `guides/`.
- **Policy and audit docs**: consolidation, naming, and orchestration policy
  materials under `policy/`.
- **Runtime helper docs**: runtime-facing prompts and orchestrator notes under
  `runtime/`.
- **Memory surface**: project and role-specific memory notes under
  `docs/00-project/ai/memory/`.

## Canonical Sources

| Runtime | Canonical path | Notes |
| --- | --- | --- |
| Claude Code | `.claude/agents/` | Основной реестр профилей Claude |
| Codex | `.codex/agents/` | Основной реестр профилей Codex |
| Docs mirror | `docs/00-project/ai/agents/` | Публикуемый документационный слой, включая Codex mirror pages |

При расхождении между runtime-реестрами (`.claude/agents/`, `.codex/agents/`)
и docs приоритет у runtime-реестра соответствующего рантайма.
Для текущего Codex workflow статус `py-code-bot` определяется по `.codex/agents/ORCHESTRATION.md`: production-код пишет orchestrator, а `py-code-bot` трактуется как deprecated compatibility reference.

## Structure

| Zone | Path | Purpose |
| --- | --- | --- |
| Guides | [guides/AGENT.md](guides/AGENT.md) | Инструкции для конкретных ассистентов |
| Runtime docs | [runtime/agent-memory.md](runtime/agent-memory.md) | Канонические docs-артефакты агентных prompt/workflow |
| Memory | [../memory/README.md](../memory/README.md) | Project memory entry point and role-specific memory snapshots |
| Agent scripts | [scripts/diagrams/py-doc-bot-4.sh](scripts/diagrams/py-doc-bot-4.sh) | Оркестратор диаграммного агентного цикла |
| Policy | [policy/AGENT_NAMING_POLICY_AND_RENAME_PLAN_2026-03-08.md](policy/AGENT_NAMING_POLICY_AND_RENAME_PLAN_2026-03-08.md) | Политики именования и стандарты |

## Canonical Documents

| Document | File | Purpose |
| --- | --- | --- |
| Jules Guide | [guides/AGENT.md](guides/AGENT.md) | Основной инженерный гайд и workflow |
| Claude Guide | [guides/CLAUDE.md](guides/CLAUDE.md) | Практики для Claude при работе с репозиторием |
| Codex Guide | [guides/CODEX.md](guides/CODEX.md) | Инструкции Architecture Auditor + Implementation Engineer |
| Gemini Guide | [guides/GEMINI.md](guides/GEMINI.md) | Профильный набор правил и ограничений для Gemini |
| QA Orchestrator | [runtime/py-qa-orchestrator.md](runtime/py-qa-orchestrator.md) | Prompt для иерархического QA-оркестратора |
| Diagram Docs Orchestrator | [runtime/py-diagram-docs-orchestrator.md](runtime/py-diagram-docs-orchestrator.md) | Оркестратор обновления/rerender диаграммных docx/pdf |
| Agent Memory (quick) | [runtime/agent-memory.md](runtime/agent-memory.md) | Краткая оперативная память по проекту |
| Team Orchestration | [agents/ORCHESTRATION.md](agents/ORCHESTRATION.md) | Публикуемое Codex docs mirror для `.codex/agents/ORCHESTRATION.md` |

## Evidence Anchors

Для структурных утверждений про repo layout, package topology и hotspot calibration сначала опирайся на актуальные evidence packs:

- [Project File Structure Summary](../../../reports/evidence/project-file-structure/SUMMARY.md)
- [Project File Structure Decisions](../../../reports/evidence/project-file-structure/04-decisions/SUMMARY.md)
- [Project Package Topology Summary](../../../reports/evidence/project-package-topology/SUMMARY.md)
- [Topology Synthesis](../../../reports/evidence/project-package-topology/03-synthesis/SYN-project-package-topology.md)
- [Topology vs Governance Cross-Synthesis](../../../reports/evidence/project-package-topology/03-synthesis/CROSS-SYNTHESIS-topology-vs-governance-signals.md)
- [Package Topology Decisions](../../../reports/evidence/project-package-topology/04-decisions/SUMMARY.md)
- [Governance Signals Summary](../../../reports/evidence/governance-signals/SUMMARY.md)
- [Governance Signals Decisions](../../../reports/evidence/governance-signals/04-decisions/SUMMARY.md)

## Policy & Audit Reports

- [policy/AGENT_NAMING_POLICY_AND_RENAME_PLAN_2026-03-08.md](policy/AGENT_NAMING_POLICY_AND_RENAME_PLAN_2026-03-08.md)
- [policy/AGENT_CONSOLIDATION_MATRIX_2026-03-08.md](policy/AGENT_CONSOLIDATION_MATRIX_2026-03-08.md)
- [policy/SPECIALIST_PROFILE_TEMPLATE.md](policy/SPECIALIST_PROFILE_TEMPLATE.md)
- [policy/CONSOLIDATION_VALIDATION.md](policy/CONSOLIDATION_VALIDATION.md)

## Navigation Entry Points

- [Profiles Catalog](agents/README.md)
- [Agent Orchestration Rules](policy/agent-orchestration-rules.md)
- [Agent Naming Policy and Rename Plan (2026-03-08)](policy/AGENT_NAMING_POLICY_AND_RENAME_PLAN_2026-03-08.md)
- [Consolidation Validation](policy/CONSOLIDATION_VALIDATION.md)
- [Agent Consolidation Matrix (2026-03-08)](policy/AGENT_CONSOLIDATION_MATRIX_2026-03-08.md)
- [AI Prompts Surface](../prompts/README.md)
- [Collected Prompts Index](../prompts/COLLECTED_PROMPTS_INDEX.md)
- [Shared Agent Memory](../memory/agent-memory.md)
- [Codex Orchestration Mirror](agents/ORCHESTRATION.md)

## Notes

- `docs/00-project/RULES.md` остаётся canonical source RFC 2119 требований.
- Этот каталог полезен как internal-published navigation layer, но не заменяет
  runtime source-of-truth files.
- При конфликте инструкций приоритет: System/Developer/User > локальные инструкции агента.
