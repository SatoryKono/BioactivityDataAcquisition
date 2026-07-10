> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/hierarchical-evidence-orchestration/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "hierarchical-evidence-orchestration"
description: "Orchestrate hierarchical evidence work for a BioETL topic by decomposing it into shard packs, delegating `collecting-evidence` across those shards, and then running `synthesizing-pillars` on completed packs before assembling a cross-synthesis. Use when users ask for repo-wide or multi-package evidence programs, recursive topology studies, naming/documentation drift waves, or coordinated evidence-then-synthesis workflows."
---

# Hierarchical Evidence Orchestration

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Shared evidence/decision contract: [../collecting-evidence/references/evidence-decision-contract.md](../collecting-evidence/references/evidence-decision-contract.md)

## Core Role

Act as the L1 orchestrator for evidence programs that are too large for one linear pass.
Use this skill to coordinate a topic-level evidence wave, not to replace the shard-level
skills:

- shard collection -> `collecting-evidence`
- shard synthesis -> `synthesizing-pillars`

## When To Use

Use this skill when:

- the topic spans multiple layers, packages, provider families, or doc domains
- the user explicitly asks for hierarchical, recursive, parallel, or multi-agent evidence collection
- one parent topic needs multiple child evidence packs and then a consolidated synthesis

Do not use this skill for a single small pillar that fits cleanly into one `collecting-evidence` pass.

## Startup Sequence

Read, in this order:

1. `../../../docs/00-project/ai/memory/agent-memory.md`
1. `../../../docs/00-project/ai/agents/agents/ORCHESTRATION.md`
1. `../collecting-evidence/SKILL.md`
1. `../synthesizing-pillars/SKILL.md`
1. [references/orchestration-contract.md](references/orchestration-contract.md)
1. [references/shard-task-briefs.md](references/shard-task-briefs.md)

## Input Contract

Confirm these inputs before orchestration starts:

- `topic_id` (required): parent topic, e.g. `project-package-topology`
- `mode` (required): `collect | synthesize | full`
- `shard_strategy` (required): `by-layer | by-package-family | by-doc-domain | custom`
- `output_root` (optional, default): `docs/reports/evidence/<topic_id>/`
- `shards` (optional): explicit shard list if the user already knows the decomposition

## Artifact Contract

Parent pack:

- `docs/reports/evidence/<topic_id>/ORCHESTRATION.md`
- `docs/reports/evidence/<topic_id>/SUMMARY.md`
- `docs/reports/evidence/<topic_id>/03-synthesis/CROSS-SYNTHESIS-<topic_id>.md` (for `synthesize` or `full`)

Child shard packs:

- `docs/reports/evidence/<shard-topic>/01-pillars/PILLARS.md`
- `docs/reports/evidence/<shard-topic>/02-evidence/<shard-topic>/EV-*.yaml`
- `docs/reports/evidence/<shard-topic>/02-evidence/<shard-topic>/RAW-<shard-topic>-<date>.md`
- `docs/reports/evidence/<shard-topic>/SUMMARY.md`
- `docs/reports/evidence/<shard-topic>/03-synthesis/SYN-<shard-topic>.md` (after synthesis)

## L1 Workflow

Use TodoWrite to track these mandatory steps:

<required>
1. Define parent topic and shard map
2. Create parent orchestration artifact
3. Create or validate shard pillar files
4. Launch shard collectors
5. Validate shard evidence gates
6. Launch shard synthesizers for completed packs
7. Build parent cross-synthesis
8. Publish parent summary and gate status
</required>

### Step 1: Define Shard Map

Decompose the topic into non-overlapping shards where possible.

Preferred shard shapes:

- layers: `application`, `composition`, `domain`, `infrastructure`, `interfaces`
- package families: `application/core`, `application/pipelines`, `composition/bootstrap`, `composition/factories`
- doc domains: project/AI, architecture, reference/guides, operations/generated
- custom families driven by the user's explicit request

Avoid shards that overlap heavily in write scope or duplicate the same claims.

### Step 2: Create Parent Orchestration Artifact

Write `ORCHESTRATION.md` in the parent topic pack with:

- topic scope
- chosen shard strategy
- shard list
- owner/agent assignment
- child output roots
- mode (`collect`, `synthesize`, `full`)

Use the template guidance in [references/orchestration-contract.md](references/orchestration-contract.md).

### Step 3: Prepare Shard Packs

For each shard:

- create `01-pillars/PILLARS.md`
- define in-scope / out-of-scope
- name the shard topic explicitly
- keep shard output roots disjoint

If `mode = synthesize`, skip creation and validate that shard packs already exist and passed evidence gate.

### Step 4: Run Shard Collection

For `mode = collect` or `mode = full`:

- delegate each shard to `collecting-evidence`
- require minimum 5 `EV-*.yaml` per shard unless the topic is explicitly narrow
- require `SUMMARY.md`
- require `git diff --check -- docs/reports/evidence/<shard-topic>`

Do not perform synthesis in the child shard during collection unless the mode is `full` and the evidence gate is already satisfied.

### Step 5: Validate Shard Gates

Each shard must report:

- evidence object count
- gate status
- YAML validation status
- `git diff --check` status

If a shard fails gate:

- mark it as `incomplete`
- do not promote it to synthesis
- record the gap in the parent summary

### Step 6: Run Shard Synthesis

For `mode = synthesize` or `mode = full`:

- delegate each completed shard to `synthesizing-pillars`
- require `03-synthesis/SYN-<shard-topic>.md`
- require evidence citations by `EV-*` id
- require explicit contradictions and gaps

Do not create decisions in this workflow unless the user explicitly asks for `making-decisions`.

### Step 7: Build Parent Cross-Synthesis

After shard synthesis is complete, create:

- `docs/reports/evidence/<topic_id>/03-synthesis/CROSS-SYNTHESIS-<topic_id>.md`

Parent cross-synthesis should:

- summarize strongest patterns across shards
- call out contradictions across shard boundaries
- distinguish breadth from confirmed hotspot/debt signals
- list unresolved gaps

This document is not a decision memo. Stop at synthesis unless the user explicitly asks for decisions.

### Step 8: Publish Parent Summary

Write `SUMMARY.md` in the parent pack with:

- shard list
- evidence counts per shard
- synthesis status per shard
- top 3-5 cross-topic findings
- gate status for the full wave

## Delegation Rules

Use subagents only when the user explicitly requested hierarchical, delegated, or parallel evidence work.

Recommended split:

- `1-3` shards: orchestrator may self-run
- `4-6` shards: delegate collection in parallel
- `>6` shards: batch into waves and avoid excessive overlap

Keep child write scopes disjoint:

- one shard -> one evidence package root
- no child should edit the parent cross-synthesis

## Constraints

MUST:

- keep evidence collection separate from synthesis
- use shard-local evidence IDs and summaries
- cite evidence IDs in every synthesis insight
- preserve uncertainties and contradictions
- treat package count, file count, and breadth as observations, not defects by themselves

MUST NOT:

- skip the evidence gate and jump straight to synthesis
- collapse multiple unrelated claims into one YAML object
- produce `DEC-*` artifacts unless the user explicitly asks for decision work
- let child shards overwrite each other's output roots

## Completion Criteria

Treat the hierarchical wave as complete only when:

- parent `ORCHESTRATION.md` exists
- each completed shard has `SUMMARY.md`
- each synthesized shard has `SYN-<shard-topic>.md`
- parent `CROSS-SYNTHESIS-<topic_id>.md` exists for `synthesize` or `full`
- parent `SUMMARY.md` reports gate status and remaining gaps

## References

- Shared evidence and decision chain contract: [../collecting-evidence/references/evidence-decision-contract.md](../collecting-evidence/references/evidence-decision-contract.md)
- Orchestration artifact and gate contract: [references/orchestration-contract.md](references/orchestration-contract.md)
- Collector and synthesizer shard briefs: [references/shard-task-briefs.md](references/shard-task-briefs.md)
