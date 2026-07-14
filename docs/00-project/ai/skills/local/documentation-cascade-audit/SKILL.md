> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/documentation-cascade-audit/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "documentation-cascade-audit"
description: "Run a hierarchical documentation audit for BioETL using cascade decomposition across doc domains (architecture, providers, contracts, operations, onboarding), aggregate findings into one prioritized report, and generate an actionable remediation plan. Use when users request large-scale doc audits, stale-doc cleanup, or coordinated doc reconciliation after major refactors/releases."
---

# Documentation Cascade Audit

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`

## Overview

Coordinate a multi-scope documentation audit where each scope is analyzed separately and then merged into a single decision-ready report.
Use this skill when a single-pass manual review is too large or error-prone.

## Startup Context

Read, in this order:

1. `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
1. `../../../docs/00-project/ai/memory/agent-memory.md`
1. `../../../.codex/agents/ORCHESTRATION.md`
1. `../documentation-audit/SKILL.md`
1. `../documentation-audit/references/audit-checklist.md`
1. `../documentation-audit/references/report-template.md`

## Cascade Workflow

1. Build audit shards.

- Create shard scopes by domain:
  - `docs/01-overview*`, `README.md`, `mkdocs.yml`
  - architecture/ADR docs
  - provider docs
  - contracts/schemas docs
  - operations/monitoring/runbook docs
- Keep shards non-overlapping when possible.

2. Execute shard audits in parallel (conceptually or via subagents if available).

- For each shard, apply the checklist from `documentation-audit`.
- Use memory plus repo search to find doc claim surfaces, linked runtime
  guidance, related diagrams, and validation gates for each shard.
- Capture findings with severity and evidence (`file + lines + command`).

3. Normalize findings.

- Deduplicate repeated findings across shards.
- Merge equivalent root causes under one canonical finding.
- Keep conflicting findings in a dedicated `Needs Clarification` section.

4. Produce consolidated outputs.

- Consolidated audit report.
- Prioritized remediation backlog (`P1/P2/P3`).
- Sequenced update plan with effort estimate.

## Deliverables

Required artifacts:

1. Итоговый отчёт: `reports/{LLM}/review_documentation-cascade-audit_{YYYYMMDD}_{HHMM}.md`
   (включает сводку и приоритеты; LLM = вызывающая модель)
1. При необходимости дополнительные вложения (remediation/open questions) сохраняй рядом
   в той же директории с тем же префиксом.

## Quality Gates

- Every high-severity claim has evidence.
- Every proposed doc change maps to a concrete file path.
- RULES/REQUIREMENTS/ADRs consistency is explicitly checked.
- Runtime-vs-mirror consistency is explicitly checked when AI guidance files are touched.
- The final plan distinguishes factual drift vs style improvements.

## Constraints

MUST:

- Prefer documenting current system behavior over intended behavior.
- Mark unresolved uncertainties as `Requires Manual Review`.
- Keep architecture statements verifiable against code.

MUST NOT:

- Modify production code in this workflow.
- Delete documentation without explicit user approval.
- Hide contradictions between docs and code.

SHOULD:

- Group edits into small, reviewable change sets.
- Provide before/after snippets for high-impact doc changes.

## Handoff Format

Return:

1. Status: `Completed | Partially Completed | Blocked`
1. Top findings by severity
1. File list for proposed changes
1. Open questions requiring user decisions
1. Link to `cascade-audit-report.md`
