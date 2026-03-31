---
Version: 1.1.0
Status: active
Class: internal-published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-31'
---

# Collected Prompts Index

*Статус: internal-published (Internal / Extended)*

This page is a curated discoverability index for prompt artifacts copied into
`docs/00-project/ai/prompts/collected/`.

These files are **not** the canonical source of project governance or runtime
workflow policy. Prefer:

- [RULES.md](../../RULES.md)
- current agent guides under `docs/00-project/ai/agents/`
- runtime orchestration docs and active skill surfaces

The collected prompt folder remains a **repo-only / historical helper surface**:
use it to find prior orchestration text, not to override current guidance.

## Current Inventory

- Target folder: `docs/00-project/ai/prompts/collected/`
- Collected files: **14**
- Surface role: copied prompt artifacts, working aids, and historical prompt snapshots

## Grouped Prompt Families

### Workspace and AI Surface Setup

- [ai_workspace_setup.md](collected/ai_workspace_setup.md)
- [ai_workspace_setup1.md](collected/ai_workspace_setup1.md)

Use for repository AI-surface bootstrap, workspace audits, and onboarding of
multi-agent configuration.

### Docs, Diagrams, and AI Audit Planning

- [docs_ai_audit_planning_claude_prompt.md](collected/docs_ai_audit_planning_claude_prompt.md)
- [docs_ai_audit_planning_codex_prompt.md](collected/docs_ai_audit_planning_codex_prompt.md)
- [documentation_diagrams_audit.md](collected/documentation_diagrams_audit.md)
- [PROMPT-diagram-expansion.md](collected/docs/02-architecture/mmd-diagrams/docs/PROMPT-diagram-expansion.md)
- [PROMPT-diagram-expansion_RU.md](collected/docs/02-architecture/mmd-diagrams/docs/PROMPT-diagram-expansion_RU.md)

Use as historical/reference material for docs and diagram expansion waves.
Active documentation policy still lives in governance docs and current skills.

### Refactor and Architecture Remediation

- [architecture_debt_reduction_orchestration.md](collected/architecture_debt_reduction_orchestration.md)
- [architecture_metric_exemptions_tasks_json_prompt.md](collected/architecture_metric_exemptions_tasks_json_prompt.md)
- [refactor_orchestration_prompt.md](collected/refactor_orchestration_prompt.md)
- [refactor_orchestration_prompt_1-2.md](collected/refactor_orchestration_prompt_1-2.md)
- [scripts_inventory_consolidation_cleanup_prompt.md](collected/scripts_inventory_consolidation_cleanup_prompt.md)

These prompts are useful as prior-wave operator aids when analyzing large
refactor or cleanup campaigns.

### Archived / Variant Copies

- [diagram-optimization-prompts-v3.md](collected/docs/plans/diagram-optimization-prompts-v3.md)
- [diagram-optimization-prompts-v3_RU.md](collected/docs/plans/diagram-optimization-prompts-v3_RU.md)

These are retained as historical/variant copies and should be treated as
reference-only artifacts.

## Usage Rules

1. Do not treat collected prompts as source-of-truth policy.
2. If a collected prompt conflicts with active docs, active docs win.
3. Prefer using this page as the single published entrypoint for the collected
   prompt surface instead of promoting raw prompt dumps into MkDocs nav.

## Related Entry Points

- [AI Prompts Surface README](README.md)
- [Skills Practical Index](../skills/SKILLS-PRACTICAL-INDEX.md)
- [Agent Orchestration Rules](../agents/policy/agent-orchestration-rules.md)
