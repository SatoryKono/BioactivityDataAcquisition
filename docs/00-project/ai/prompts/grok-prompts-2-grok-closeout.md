# Grok Closeout Prompt — Improved Version

*Status: internal working prompt | Class: operator aid | Not governance SSOT*
*Version: 2.0.0 | Date: 2026-04-04*
*Evaluation Score: 8.5/10 (improved from 7.88)*

**Purpose:**
Short, focused prompt for Grok closeout operations in BioETL repository. Use this instead of 45–70 KB multi-cycle megaprompts.

**When to use:**
- Closing out GitHub issues with fixes
- Verifying already-resolved issues
- Completing remediation from audit cycles
- Finalizing PRs for issue resolution

**When NOT to use:**
- For systematic audits (use grok-audit-cycle.md instead)
- For runtime-specific behavior (use appropriate runtime trees)
- For canonical project rules (use RULES.md)

**Key Principles:**
- Canonical rules stay in `AGENTS.md` / `docs/00-project/NORMATIVE_SOURCES.md`
- Use .venv-win on Windows and .venv in WSL/Linux
- Only ADMIT at the required trust tier qualifies closeout
- Optional vendor evidence cannot override the offline core verifier

______________________________________________________________________

## Paste template

```text
# BioETL closeout

## Params
- REPO: SatoryKono/BioactivityDataAcquisition
- BASE: main
- WORK_BRANCH: create fix/<slug> if on main; never commit to main
- SCOPE: issues <list> OR path cluster <paths>
- MODE: closeout
- CYCLE_COUNT: 1
- LANGUAGE: ru (code/ids/paths original)

## Read (do not restate)
1. AGENTS.md
2. docs/00-project/NORMATIVE_SOURCES.md
3. docs/00-project/ai/agents/guides/MEMORY_USAGE.md (if AI/memory surfaces)

## Git / safety
- Do not edit/delete others' uncommitted work
- No reset --hard, no force-push, no .env edits without explicit approval
- Prefer worktree if main dirty
- Push feature branch only; open PR to main

## Execution
For each issue in SCOPE:
1. Confirm against current origin/main (code wins)
2. Fix product root cause OR mark VERIFIED_ALREADY_RESOLVED with evidence
3. Run focused tests/checks for the surface
4. PR if product/docs delta; else evidence-only
5. Use .venv-win/Scripts/python.exe on Windows or .venv/bin/python in WSL/Linux
6. Run proof-or-stop assemble + verify; prose is a claim, not DONE state
7. Only ADMIT at the required trust tier qualifies closeout; DEGRADED/STOP stay open
8. Optional vendor evidence cannot override the offline core verifier
9. Issue comment with acceptance + commands; close if admitted and done
Blocked: leave issue OPEN with exact blocker and acceptance gaps

## Done table
| Issue | Verdict | SHA/PR | Checks |
```

## Error Handling

### If issue already resolved on main
1. Mark as VERIFIED_ALREADY_RESOLVED
2. Provide evidence (commit SHA, test results)
3. Comment on issue with verification details
4. Close issue if verification passes

### If fix cannot be applied
1. Document exact blocker in issue comment
2. Mark issue as BLOCKED
3. List acceptance gaps
4. Do not close issue

### If tests fail after fix
1. Stop closeout for that issue
2. Document test failure in issue comment
3. Mark issue as BLOCKED on test failure
4. Continue with other issues if possible

### If proof-or-stop returns DEGRADED or STOP
1. Do not close issue
2. Document verifier result in issue comment
3. Mark issue as BLOCKED on verification failure
4. Require manual review before retry

### If GitHub API fails
1. Continue with local documentation
2. Document GitHub failure in closeout report
3. Manually update issues when API available

## Validation

### Before starting closeout
1. Verify WORK_BRANCH is not main
2. Confirm SCOPE issues exist and are open
3. Check git status (no uncommitted work from others)

### During execution
1. Each fix must pass relevant tests
2. Each fix must preserve public interfaces
3. Each fix must not grow tech-debt budgets
4. Evidence must be verifiable (not just prose)

### At issue closeout
1. Proof-or-Stop verifier must return ADMIT
2. Tests must pass for fixed issues
3. Verification evidence documented
4. Issue comment with acceptance criteria

### At session closeout
1. All issues have verdict (FIXED/VERIFIED_ALREADY_RESOLVED/BLOCKED)
2. All FIXED issues have PR or commit
3. All BLOCKED issues have documented blockers
4. Done table complete

## Git Safety

### Branch management
- Never commit to main directly
- Create feature branch: `fix/<slug>`
- Use worktree if main has uncommitted work
- Push feature branch only, never force-push

### File safety
- Do not edit/delete others' uncommitted work
- No `git reset --hard` without explicit approval
- No `.env` edits without explicit user approval
- Preserve existing file permissions

### PR management
- Open PR to main only
- Include tests in PR
- Include verification evidence in PR description
- Link PR to issue(s)

## Output Format

```markdown
# Closeout Report

**Date**: YYYY-MM-DD
**Scope**: {SCOPE}
**Branch**: {WORK_BRANCH}

## Issues Summary

| Issue | Verdict | SHA/PR | Checks | State |
|-------|---------|--------|--------|-------|
| ... | ... | ... | ... | ... |

**Total issues**: {N}
**Fixed**: {N}
**Verified already resolved**: {N}
**Blocked**: {N}

## Verification Details

### Issue {N}: {title}
**Verdict**: {FIXED/VERIFIED_ALREADY_RESOLVED/BLOCKED}
**Evidence**: {evidence summary}
**Tests**: {test results}
**Proof-or-Stop**: {ADMIT/DEGRADED/STOP}
**Comment**: {issue comment summary}

## Next Steps

{For FIXED: PR review and merge}
{For VERIFIED_ALREADY_RESOLVED: close issue}
{For BLOCKED: manual review required}
```

## Notes

- Prefer VERIFIED_ALREADY_RESOLVED when main already fixed
- Do not grow tech-debt / quality budgets
- Ship-profile (`permission_mode=always-approve`) is optional and short-lived; default operator profile is ask — see `docs/00-project/ai/agents/guides/grok-operator-runbook.md`
- Prose claims are not DONE state; only ADMIT from verifier qualifies

______________________________________________________________________

## Evaluation Metadata

**Original Score:** 7.88/10 (High)
**Improved Score:** 8.5/10 (High)

**Improvements Made:**

1. **Context** (8→9): Added clear purpose section explaining when to use/not use the prompt
2. **Error Handling** (6→8): Added detailed error handling procedures for each scenario
3. **Validation** (7→9): Added validation procedures for pre/during/post closeout
4. **Documentation** (8→9): Added comprehensive metadata including version, evaluation score, and improvement notes
5. **Clarity** (9→9): Maintained high clarity with improved structure
6. **Maintainability** (9→9): Maintained high maintainability with simple structure
7. **Specificity** (8→9): Improved specificity with validation checkpoints

**Key Changes:**
- Added "Purpose" section with when to use/not use guidance
- Added "Key Principles" section
- Added "Error Handling" section with procedures for each scenario
- Added "Validation" section with pre/during/post validation
- Added "Output Format" section with template
- Added evaluation metadata at the end
- Expanded "Git Safety" section with detailed procedures
- Expanded "Notes" section

**Remaining Limitations:**
- Specific to Grok closeout operations (limited reusability to other AI agents)
- Requires understanding of BioETL repository structure
- Requires access to proof-or-stop verifier
