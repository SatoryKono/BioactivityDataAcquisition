# Prompt Catalog (.claude/prompts)

This directory contains reusable prompt templates for Claude-driven workflows in BioETL.

## Status

- **Active source**: prompt files in this directory tree.
- **Scope**: task acceleration and repeatable operator workflows (audit, sync, documentation, cleanup).
- **Authority**: project rules are defined in `docs/00-project/RULES.md`; prompts must not override RULES.

## Structure

- `00-Audit/` — audit templates (architecture, file-structure, code inventory).
- `00-Documentation/` — documentation update and docstring templates.
- `01-documentation-update-prompt.md` — consolidated documentation update workflow.
- `02-Sync/` — synchronization templates (crosswalk, docs PR, schema review, manual EP).
- `03-repository-cleanup-assistant.md` — repository cleanup assistant prompt.

## Usage Notes

- Treat these prompts as starting points; adapt scope and constraints per task.
- Keep references to versions and dates current (RULES version, ADR count, sync date).
- Prefer canonical paths in instructions (`.claude/agents/`, `docs/00-project/`, `configs/`, `src/bioetl/`).
