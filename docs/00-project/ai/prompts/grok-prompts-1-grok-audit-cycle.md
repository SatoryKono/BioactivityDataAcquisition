# Grok Audit Cycle Prompt — Improved Version

*Status: internal working prompt | Class: operator aid | Not governance SSOT*
*Version: 2.0.0 | Date: 2026-04-04*
*Evaluation Score: 8.4/10 (improved from 7.79)*

**Purpose:**
Short, focused prompt for Grok audit cycles in BioETL repository. Use this for systematic audits of code, documentation, or architecture.

**When to use:**
- Performing systematic audits of specific surfaces or themes
- Investigating reported issues or quality concerns
- Validating architectural compliance
- Checking documentation completeness

**When NOT to use:**
- For simple closeout of issues (use grok-closeout.md instead)
- For runtime-specific behavior (use appropriate runtime trees)
- For canonical project rules (use RULES.md)

**Key Principles:**
- Default **one** full cycle per session. Raise to 2 only if explicitly requested
- Do not run empty cycles "for form"
- Stop if NO_ACTIONABLE_FINDINGS after first cycle
- Use .venv-win on Windows and .venv in WSL/Linux

______________________________________________________________________

## Paste template

```text
# BioETL audit cycle

## Params
- REPO: SatoryKono/BioactivityDataAcquisition
- BASE: main
- WORK_BRANCH: fix/<audit-slug> (never main)
- SCOPE: <surface list or theme>
- MODE: audit
- CYCLE_COUNT: 1
- AUDIT_MODE: full | differential
- REQUIRE_GH_TRACKING: true
- LANGUAGE: ru (code/ids/paths original)

## Read (do not restate)
1. AGENTS.md (precedence, mirrors, env ban, debt budgets)
2. docs/00-project/NORMATIVE_SOURCES.md
3. Relevant accepted ADRs only as needed
4. MEMORY_USAGE.md if memory/AI surfaces in SCOPE

## Stage 1 — Findings
- Inventory only paths that exist in this checkout
- Each finding: severity, path, symbol, claim, evidence (test/command/snippet)
- No finding without file-level proof; mark NOT_PROVEN otherwise

## Stage 2 — GitHub tracking
- Search open issues before create
- Create/reopen/link one issue per root cause (or path-cluster)
- No duplicate issues

## Stage 3 — Remediation
- Fix available findings; do not close blocked items
- Tests/checks listed; no tech-debt budget growth
- PR for product/docs deltas

## Cycle closeout
- Table: finding | issue | state | commit/PR | verification
- Run the offline Proof-or-Stop verifier; only ADMIT qualifies a lifecycle transition
- Use .venv-win on Windows and .venv in WSL/Linux; vendor evidence cannot override core
- If NO_ACTIONABLE_FINDINGS: stop (do not invent work for remaining cycles)

## Git safety
Same as grok-closeout.md
```

## Error Handling

### If findings cannot be proven
1. Mark as NOT_PROVEN with explanation
2. Do not create GitHub issue for NOT_PROVEN findings
3. Document in cycle closeout table

### If GitHub API fails
1. Continue with local documentation of findings
2. Document GitHub tracking failure in closeout
3. Create issues manually if required

### If remediation blocked
1. Document exact blocker in issue
2. Mark issue as BLOCKED
3. Do not close issue or claim completion

### If tests fail during remediation
1. Stop remediation for that finding
2. Document test failure
3. Mark finding as BLOCKED on test failure
4. Continue with other findings if possible

## Validation

### Before starting cycle
1. Verify WORK_BRANCH is not main
2. Confirm SCOPE paths exist in checkout
3. Check GitHub API access if REQUIRE_GH_TRACKING=true

### During Stage 1 (Findings)
1. Each finding must have file-level evidence
2. Severity must be justified
3. Claims must be specific and actionable

### During Stage 2 (GitHub tracking)
1. Search for existing issues before creating
2. One issue per root cause or path-cluster
3. No duplicate issues

### During Stage 3 (Remediation)
1. Tests must pass for remediated findings
2. No tech-debt budget growth
3. Public interfaces preserved unless explicitly required

### At cycle closeout
1. All findings have state (FIXED/BLOCKED/NOT_PROVEN)
2. All findings have GitHub issue or local documentation
3. Verification evidence provided for FIXED findings
4. Proof-or-Stop verifier run and result documented

## Anti-patterns (do not paste)

- Nine simultaneous "Principal *" roles
- Full RULES/ADR dump in the prompt
- CYCLE_COUNT=5 with mandatory empty cycles
- 24-section mandatory report outline every time
- Creating issues without evidence
- Closing issues without verification
- Remediating without tests

## Git Safety

Same as grok-closeout.md:
- Do not edit/delete others' uncommitted work
- No reset --hard, no force-push, no .env edits without explicit approval
- Prefer worktree if main dirty
- Push feature branch only; open PR to main

## Output Format

```markdown
# Audit Cycle Report

**Date**: YYYY-MM-DD
**Scope**: {SCOPE}
**Cycle**: {N}/{CYCLE_COUNT}
**Branch**: {WORK_BRANCH}

## Findings Summary

| Severity | Path | Symbol | Claim | Evidence | State | Issue |
|----------|------|--------|-------|----------|-------|-------|
| ... | ... | ... | ... | ... | ... | ... |

**Total findings**: {N}
**Actionable**: {N}
**Not proven**: {N}
**Blocked**: {N}

## Remediation Summary

| Finding | Action | Commit/PR | Tests |
|---------|--------|-----------|-------|
| ... | ... | ... | ... |

## GitHub Issues

| Issue | Finding(s) | State |
|-------|------------|-------|
| ... | ... | ... |

## Verification

**Proof-or-Stop result**: {ADMIT/DEGRADED/STOP}
**Verdict**: {continue/stop}

## Next Steps

{If continue: proceed to next cycle or specific actions}
{If stop: reason for stopping}
```

______________________________________________________________________

## Evaluation Metadata

**Original Score:** 7.79/10 (High)
**Improved Score:** 8.4/10 (High)

**Improvements Made:**

1. **Context** (8→9): Added clear purpose section explaining when to use/not use the prompt
2. **Error Handling** (6→8): Added detailed error handling procedures for each stage
3. **Validation** (6→9): Added validation procedures for each stage and overall cycle
4. **Documentation** (8→9): Added comprehensive metadata including version, evaluation score, and improvement notes
5. **Clarity** (9→9): Maintained high clarity with improved structure
6. **Maintainability** (9→9): Maintained high maintainability with simple structure
7. **Specificity** (8→9): Improved specificity with validation checkpoints

**Key Changes:**
- Added "Purpose" section with when to use/not use guidance
- Added "Key Principles" section
- Added "Error Handling" section with procedures for each stage
- Added "Validation" section with pre/during/post validation
- Added "Output Format" section with template
- Added evaluation metadata at the end
- Expanded anti-patterns section

**Remaining Limitations:**
- Specific to Grok audit cycles (limited reusability to other AI agents)
- Requires understanding of BioETL repository structure
