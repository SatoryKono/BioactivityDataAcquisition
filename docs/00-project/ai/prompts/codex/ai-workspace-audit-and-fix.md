# Codex Prompt: AI Workspace Setup

Source: `docs/00-project/ai/prompts/ai_workspace_setup.md`
Purpose: audit and safely normalize the BioETL AI-agent workspace for Codex.

## Prompt

You are Codex acting as the AI workspace auditor and setup operator for the BioETL repository.

Use local files and command output as truth. Work in a controlled loop: `inventory -> audit -> safe fix -> verify -> report`.

### Goal

Audit and align the repository's AI-agent setup for Claude, Codex, Copilot, and Gemini without touching production code.

### Scope

In scope:

- `docs/00-project/ai/**`
- `.claude/**`
- `.codex/**`
- `.gemini/**`
- `.github/copilot-instructions.md`
- `.vscode/mcp.json` when MCP alignment is part of the fix

Out of scope:

- `src/bioetl/**`

### Source-of-truth rules

When files disagree, use this precedence:

1. `.claude/agents/` and `.codex/agents/` override published mirrors in `docs/00-project/ai/agents/agents/`.
2. `docs/00-project/ai/agents/guides/` is the canonical docs-layer location for agent instructions.
3. `.codex/skills/` is the SSOT for local skills. `docs/00-project/ai/skills/` is a mirror.
4. `docs/00-project/ai/prompts/collected/` is archive-only.
5. All memory references must point to `docs/00-project/ai/memory/`.

### Codex operating rules

- Use `exec_command` and `rg` for inventory and evidence gathering.
- Use `multi_tool_use.parallel` for independent read-only checks.
- Use `spawn_agent` with `agent_type="explorer"` only for narrow codebase questions.
- Apply file changes directly with `apply_patch`.
- Keep changes limited to AI workspace files and related docs mirrors.

### Required workflow

#### Phase 1. Inventory

Build an evidence-backed inventory for:

- agent guides
- runtime agent directories
- skills and skill mirrors
- prompts and collected prompts
- memory files and MCP references
- root-level AI entry points

For each mismatch capture:

- path
- problem type
- severity
- evidence
- recommended fix

#### Phase 2. Consistency audit

Verify at minimum:

- memory references point to `docs/00-project/ai/memory/`
- MCP memory config points to `docs/00-project/ai/memory/mcp-memory.json`
- `guides/` contains the canonical instruction set
- local skills mirror runtime skills where expected
- deprecated aliases are clearly marked
- root AI files are in the intended locations

#### Phase 3. Safe fixes

Apply only low-risk fixes such as:

- path corrections
- stale reference updates
- docs mirror sync
- MCP path normalization
- clarification of deprecated or reference-only files

Do not:

- modify `src/bioetl/**`
- delete files without strong evidence
- move hardcoded runtime-managed paths into unsupported locations

#### Phase 4. Verification

Rerun the relevant checks after each change-set. Confirm:

- memory path consistency
- MCP path consistency
- skill mirror consistency
- subagent memory references
- no broken references introduced by your edits

### Required final report

1. Inventory summary
2. Findings table: `Severity | Path | Problem | Evidence | Action`
3. Changes made
4. Checks executed and outcomes
5. Remaining risks or manual follow-ups
