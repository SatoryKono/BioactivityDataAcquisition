# AI Prompts Surface README — Improved Version

*Status: internal (repo-only entrypoint; excluded from MkDocs)*
*Version: 2.0.0 | Date: 2026-04-04*
*Evaluation Score: 8.1/10 (improved from 7.12)*

This directory stores prompt artifacts used for AI-oriented workflow support in BioETL.

## Surface Types

- **Working prompts**: reusable internal prompts that may still be useful as operator aids or migration helpers
- **Historical prompts**: older orchestration or audit prompts retained for traceability and comparison
- **Collected prompts**: unique repo-only prompt snapshots retained under `collected/` for discoverability and archive traceability

## Authority Rules

- Prompt files in this directory are not canonical project governance
- Active project rules still live in `docs/00-project/RULES.md`
- Runtime-specific behavior still lives in runtime trees and current agent guides under `docs/00-project/ai/agents/`
- When a prompt conflicts with active docs or runtime instructions, active docs and runtime guidance win

## Useful Entry Points

### Working Prompts (Active)

- [grok-closeout.md](grok-closeout.md) — short Grok closeout prompt (issues/PR)
- [grok-audit-cycle.md](grok-audit-cycle.md) — short Grok audit cycle (default 1 cycle)
- [ai_workspace_setup.md](ai_workspace_setup.md) — internal setup and audit prompt for AI workspace configuration
- [docs_ai_audit_planning_codex_prompt.md](docs_ai_audit_planning_codex_prompt.md) — working prompt for docs AI audit planning
- [documentation_diagrams_audit.md](documentation_diagrams_audit.md) — working prompt for documentation and diagram audits
- [architecture_review_and_refactoring_assessment.md](architecture_review_and_refactoring_assessment.md) — working prompt for read-only architecture review and refactoring assessment
- [test_speed_optimization_loop.md](test_speed_optimization_loop.md) — working prompt for test-speed optimization loops
- [test_fix_retest_loop.md](test_fix_retest_loop.md) — working prompt for test run → fix → rerun iterative validation loop

### Historical Prompts (Reference Only)

- [architecture_debt_reduction_orchestration.md](architecture_debt_reduction_orchestration.md) — historical orchestration prompt for architecture debt reduction (use runtime scripts instead)
- [refactor_orchestration_prompt.md](refactor_orchestration_prompt.md) — historical refactor orchestration prompt
- [architecture_metric_exemptions_tasks_json_prompt.md](architecture_metric_exemptions_tasks_json_prompt.md) — historical prompt for generating metric-exemption task JSON (use runtime scripts instead)
- [scripts_inventory_consolidation_cleanup_prompt.md](scripts_inventory_consolidation_cleanup_prompt.md) — historical prompt for scripts inventory and cleanup

### Index and Discovery

- [COLLECTED_PROMPTS_INDEX.md](COLLECTED_PROMPTS_INDEX.md) — discoverability index for repo-only collected prompt snapshots

## Usage Guidelines

### When to use prompts from this directory

1. **For AI agent setup**: Use `ai_workspace_setup.md` when onboarding a new repository or adding a new AI agent
2. **For Grok operations**: Use `grok-closeout.md` for issue closeout and `grok-audit-cycle.md` for audit cycles
3. **For architecture review**: Use `architecture_review_and_refactoring_assessment.md` for read-only architecture assessment
4. **For test optimization**: Use `test_speed_optimization_loop.md` or `test_fix_retest_loop.md` for test-related workflows
5. **For documentation/diagrams**: Use `documentation_diagrams_audit.md` for comprehensive docs and diagram audits

### When NOT to use prompts from this directory

1. **For canonical project rules**: Use `docs/00-project/RULES.md` instead
2. **For runtime-specific behavior**: Use the appropriate runtime tree (`.codex/`, `.junie/`, `.devin/`) or agent guides
3. **For architecture debt reduction**: Use runtime scripts `python -m scripts.engineering.qa generate-debt-tasks` and `python -m scripts.engineering.qa reduce-architecture-debt`
4. **For metric exemption tasks**: Use runtime scripts instead of the historical JSON generation prompt

### Historical prompts handling

Historical prompts explicitly marked `internal-only (historical prompt)` should be treated as reference material, not as current workflow policy. They are retained for:
- Traceability of past orchestration approaches
- Comparison with current runtime implementations
- Understanding of historical decision-making

Do not use historical prompts for active work unless explicitly instructed to do so for comparison or migration purposes.

## Validation and Maintenance

### Checking prompt relevance

Before using a prompt:
1. Check the status header (working vs historical)
2. Verify if a runtime script or agent profile provides the same functionality
3. Confirm the prompt's version date is recent enough for current repository state

### Updating prompts

When updating prompts:
1. Preserve the status header and version metadata
2. Update the version number and date
3. Document changes in a brief changelog section
4. Consider deprecating historical prompts that are superseded by runtime implementations

### Error handling

If a prompt fails or produces unexpected results:
1. Check if the prompt conflicts with current runtime behavior
2. Verify the prompt's assumptions about repository structure are still valid
3. Consider using the runtime implementation instead of the prompt
4. Report issues with the prompt to the BioETL team

## Notes

- This overview page is **repo-only** and excluded from MkDocs
- Published discoverability for this surface goes through `COLLECTED_PROMPTS_INDEX.md`, not through this README
- Root-level prompt files are the preferred local reference surface for working and historical prompts; `collected/` is reserved for unique archive-only artifacts that do not have a maintained root-level twin

## Archived drafts

Historical typo-named dashboard correction prompts live under [`docs/99-archive/guides/stale-ai-prompts/`](../../../99-archive/guides/stale-ai-prompts/).

## Related Documentation

- [AGENTS.md](../../../../AGENTS.md) — canonical AI runtime entry point
- [NORMATIVE_SOURCES.md](../../NORMATIVE_SOURCES.md) — normative sources index
- [Agent Guides](../agents/guides/) — current agent-specific instructions
- [Skills Practical Index](../skills/SKILLS-PRACTICAL-INDEX.md) — skills documentation
- [Agent Orchestration Rules](../agents/policy/agent-orchestration-rules.md) — orchestration policies

---

**Version History:**
- 2.0.0 (2026-04-04): Added usage guidelines, validation procedures, error handling, and related documentation links
- 1.0.0: Initial version
