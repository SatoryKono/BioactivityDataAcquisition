---
id: prompt.docs.ai-audit-planning
version: 2.1.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [codex, grok, any]
params: [SCOPE, MODE, LANGUAGE]
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Treating docs mirrors as runtime SSOT
  - Full RULES dump in the paste
  - Editing .codex without mirror-sync plan
tags: [docs, audit, planning, operator]
summary: Plan an audit of docs/00-project/ai surfaces
---

# Docs / AI surface audit planning

Plan (and optionally execute) an audit of `docs/00-project/ai/**` and related
runtime mirrors without redefining runtime behavior.

## Params

| Param | Default |
| --- | --- |
| `SCOPE` | `docs/00-project/ai` (or narrower subtree) |
| `MODE` | `plan` \| `plan+execute` |
| `LANGUAGE` | `ru` |

## Goals

1. Inventory AI docs surfaces: agents, memory, prompts, skills, policy
2. Detect drift vs runtime (`.codex/**`, `.junie/**`) and governance SSOT
3. Produce a prioritized fix plan with evidence paths
4. If `MODE=plan+execute`: apply only docs/mirror fixes that do not change
   runtime behavior unless explicitly in SCOPE

## Method

1. Map entrypoints: `docs/00-project/ai/README.md`, agent/policy guides,
   prompts library README, skills indexes
2. Cross-check ownership:
   [AI_RUNTIME_MIRROR_OWNERSHIP.md](../../../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md)
3. Flag: broken links, stale versions, mirror/runtime divergence, prompts that
   look like behavior SSOT
4. Output: findings table + recommended PRs/issues; no secret material

## Deliverable

| Finding | Severity | Path | Evidence | Proposed action |
| --- | --- | --- | --- | --- |
