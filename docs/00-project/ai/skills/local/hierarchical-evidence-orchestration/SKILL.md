---
name: hierarchical-evidence-orchestration
description: Orchestrate hierarchical evidence work for a BioETL topic by decomposing it into shard packs, delegating `collecting-evidence` across those shards, and then running `synthesizing-pillars` on completed packs before assembling a cross-synthesis.
---

# hierarchical-evidence-orchestration

## Objective
Run the hierarchical evidence orchestration workflow as defined in the runtime skill.

## Source Of Truth
- Primary runtime skill: `../../../../../../.codex/skills/hierarchical-evidence-orchestration/SKILL.md`
- Shared evidence collector: `../collecting-evidence/SKILL.md`
- Shared synthesis skill: `../synthesizing-pillars/SKILL.md`

## Workflow
1. Open and follow the runtime skill at `../../../../../../.codex/skills/hierarchical-evidence-orchestration/SKILL.md`.
2. Use `collecting-evidence` for shard collection and `synthesizing-pillars` for shard synthesis.
3. Keep child shard output roots disjoint and reserve parent cross-synthesis for the orchestrator layer.
