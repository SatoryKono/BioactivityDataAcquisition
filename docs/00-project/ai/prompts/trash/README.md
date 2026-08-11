# AI Prompts Surface

*Статус: internal (repo-only entrypoint; excluded from MkDocs)*

This directory stores prompt artifacts used for AI-oriented workflow support in
BioETL.

## Surface Types

- **Working prompts**: reusable internal prompts that may still be useful as
  operator aids or migration helpers.
- **Historical prompts**: older orchestration or audit prompts retained for
  traceability and comparison.
- **Collected prompts**: unique repo-only prompt snapshots retained under
  `collected/` for discoverability and archive traceability.

## Authority Rules

- Prompt files in this directory are not canonical project governance.
- Active project rules still live in `docs/00-project/RULES.md`.
- Runtime-specific behavior still lives in runtime trees and current agent
  guides under `docs/00-project/ai/agents/`.
- When a prompt conflicts with active docs or runtime instructions, active docs
  and runtime guidance win.

## Useful Entry Points

- [grok-closeout.md](../grok-closeout.md) — short Grok closeout prompt (issues/PR)
- [grok-audit-cycle.md](../grok-audit-cycle.md) — short Grok audit cycle (default 1 cycle)

- [docs_ai_audit_planning_codex_prompt.md](../docs_ai_audit_planning_codex_prompt.md)
  — internal planning prompt for AI documentation audits
- [documentation_diagrams_audit.md](../archive/campaigns/documentation_diagrams_audit.md) —
  working prompt for full documentation and diagram audits aligned to the live
  BioETL repo structure
- [architecture_review_and_refactoring_assessment.md](../architecture_review_and_refactoring_assessment.md)
  — working prompt for read-only architecture review and refactoring assessment
- [test_speed_optimization_loop.md](../archive/campaigns/pre-library-test_speed_optimization_loop.md) —
  working prompt for test-speed optimization loops
- [test_fix_retest_loop.md](../archive/campaigns/pre-library-test_fix_retest_loop.md) — working prompt for
  test run → fix → rerun iterative validation loop
- [COLLECTED_PROMPTS_INDEX.md](../COLLECTED_PROMPTS_INDEX.md) — discoverability
  index for repo-only collected prompt snapshots
- Historical prompts in this folder explicitly marked `internal-only (historical prompt)` should be treated as reference material, not as current
  workflow policy

## Notes

- This overview page is **repo-only** and excluded from MkDocs.
- Published discoverability for this surface goes through
  `COLLECTED_PROMPTS_INDEX.md`, not through this README.
- Root-level prompt files are the preferred local reference surface for working
  and historical prompts; `collected/` is reserved for unique archive-only
  artifacts that do not have a maintained root-level twin.

## Archived drafts

Historical typo-named dashboard correction prompts live under
[`docs/99-archive/guides/stale-ai-prompts/`](../../../../99-archive/guides/stale-ai-prompts/).
