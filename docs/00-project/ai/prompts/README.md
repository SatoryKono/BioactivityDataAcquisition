# AI Prompts Surface

*Статус: internal-published (Internal / Extended)*

This directory stores prompt artifacts used for AI-oriented workflow support in
BioETL.

## Surface Types

- **Working prompts**: reusable internal prompts that may still be useful as
  operator aids or migration helpers.
- **Historical prompts**: older orchestration or audit prompts retained for
  traceability and comparison.
- **Collected prompts**: copied prompt artifacts gathered from other doc areas;
  these are discoverability copies, not source-of-truth workflow policy.

## Authority Rules

- Prompt files in this directory are not canonical project governance.
- Active project rules still live in `docs/00-project/RULES.md`.
- Runtime-specific behavior still lives in runtime trees and current agent
  guides under `docs/00-project/ai/agents/`.
- When a prompt conflicts with active docs or runtime instructions, active docs
  and runtime guidance win.

## Useful Entry Points

- [ai_workspace_setup.md](ai_workspace_setup.md) — internal setup and audit
  prompt for AI workspace configuration
- [COLLECTED_PROMPTS_INDEX.md](COLLECTED_PROMPTS_INDEX.md) — discoverability
  index for copied prompt artifacts
- Historical prompts in this folder explicitly marked `internal-only
  (historical prompt)` should be treated as reference material, not as current
  workflow policy
