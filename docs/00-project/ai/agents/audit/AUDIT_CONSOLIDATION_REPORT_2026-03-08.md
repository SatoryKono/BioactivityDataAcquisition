# Audit & Consolidation Report: `docs/00-project/ai/agents`

Date: 2026-03-08
Scope: `docs/00-project/ai/agents/**`

## Critical Findings

1. `HIGH` — SSOT ambiguity for agent registries.
   - Problem: docs referenced only `.claude/agents` as canonical while Codex runtime registry exists in `.codex/agents`.
   - Risk: drift and incorrect maintenance assumptions.
   - Resolution: SSOT matrix added to `README.md`.

2. `HIGH` — Orchestration docs copy pointed only to Claude canonical source.
   - Problem: `orchestration/ORCHESTRATION.md` deprecation note did not mention Codex canonical orchestration file.
   - Risk: contributors follow wrong source for Codex workflows.
   - Resolution: deprecation header updated with both runtime canonicals.

3. `MEDIUM` — `collected/` snapshot status was implicit.
   - Problem: index did not explicitly mark snapshot as non-SSOT/generated.
   - Risk: manual edits in snapshot tree and accidental source-of-truth confusion.
   - Resolution: `COLLECTED_AGENTS_INDEX.md` now labels snapshot scope and edit policy.

## Validation Performed

1. Inventory audit:
   - `docs/00-project/ai/agents/snapshots/collected` files: 121
   - `.claude/agents/*.md`: 100
   - `snapshots/collected/.claude/agents/*.md`: 100
   - Result: snapshot parity for `.claude/agents` is complete.

2. Markdown links audit:
   - Checked local markdown links in `docs/00-project/ai/agents/**/*.md`.
   - Result: no missing link targets detected.

## Consolidation Decisions

1. Keep runtime SSOT external to docs:
   - Claude runtime SSOT: `.claude/agents/`
   - Codex runtime SSOT: `.codex/agents/`

2. Keep `docs/00-project/ai/agents/` as documentation layer, not executable registry.

3. Keep `snapshots/collected/` as immutable snapshot zone for audit/history, not an editable source.

## Residual Risks

1. Snapshot freshness is process-dependent (manual or script-driven refresh cadence).
2. Runtime files in `.codex/agents` are not mirrored into `snapshots/collected/` by current snapshot scope.
