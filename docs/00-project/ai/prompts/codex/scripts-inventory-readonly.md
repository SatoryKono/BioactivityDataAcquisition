# Codex Prompt: Scripts Inventory, Consolidation, and Cleanup

Source: `docs/00-project/ai/prompts/scripts_inventory_consolidation_cleanup_prompt.md`
Purpose: read-only Codex prompt for script-layer auditing.

## Prompt

You are Codex acting as the script-layer auditor for BioETL.

Perform a read-only inventory and consolidation analysis for:

- `scripts/**`
- `src/tools/**`

### Hard constraints

- Do not modify files.
- No autofix, formatting, or deletion.
- Every conclusion must cite path-based evidence.

### Audit goals

1. Find every executable or utility script.
2. For each script determine:
   - purpose
   - expected invocation context
   - concrete invocation pattern
   - caller or owner
   - agent or skill usage, if any
   - lifecycle status
   - risks
3. Detect:
   - duplicates
   - orphans
   - poor placement or naming
   - architecture or governance drift

### Additional evidence sources

Inspect read-only:

- `AGENTS.md`
- `.codex/skills/**`
- CI and workflow definitions
- project automation entry points such as `pyproject.toml`, `Makefile`, `noxfile`, `justfile`, `tox.ini`
- docs and tests that reference scripts

### Required output

1. Executive summary
2. Markdown inventory table:
   `Script Path | Type | Purpose | Invocation | Caller/Owner | Agent Usage | Status | Evidence`
3. Agent-usage matrix
4. Issues grouped by severity
5. Consolidation plan by phase
6. Removal candidates
7. Consolidation candidates
8. Roadmap for 2 to 4 iterations

### Reporting rules

- Mark unknown usage explicitly; do not invent call sites.
- Do not recommend deletion unless backward-compatibility checks are addressed.
- Treat external agent orchestration usage as real when evidence is partial.
- End with a maturity score from `0` to `10` and the highest-ROI next actions.
