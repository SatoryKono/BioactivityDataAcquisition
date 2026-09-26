# Issue: .devin/ Directory Governance Decision

## Type
- [ ] Feature
- [ ] Bug
- [x] Technical Debt
- [ ] Governance

## Priority
- [ ] P0 (Critical)
- [x] P1 (High)
- [ ] P2 (Medium)
- [ ] Low

## Context
Based on the file structure audit (2025-01-30), the `.devin/` directory is tracked (63 files, 369 KB) but lacks documented governance. Other vendor AI directories (.ai/, .agents/, .junie/, .qodo/, .sonarlint/, .windsurf/) are properly ignored.

## Problem
- `.devin/` contains 63 tracked files (369 KB)
- No documented governance decision in AGENTS.md or similar
- Unclear ownership and lifecycle
- Inconsistent with other vendor AI directories (all in .gitignore)
- Potential namespace pollution

## Impact
- Unclear ownership and maintenance responsibility
- Inconsistent governance across vendor AI runtimes
- Potential security risk if contains machine-local config
- Disk waste if not actively used

## Proposed Solution

### Option A: Add to .gitignore (if machine-local)
If `.devin/` is machine-local runtime:
```bash
echo ".devin/" >> .gitignore
git rm -r --cached .devin/
git add .gitignore
git commit -m "chore: ignore .devin/ directory (machine-local runtime)"
```

### Option B: Document as canonical runtime (if team uses it)
If `.devin/` is canonical team runtime:
1. Add governance documentation to AGENTS.md
2. Document ownership and lifecycle
3. Update .github/root-allowlist.txt if needed
4. Document in docs/00-project/ai/agents/

### Option C: Move to .codex/ (if Codex runtime)
If `.devin/` is Codex runtime:
```bash
mv .devin/ .codex/devin/
git add .devin/ .codex/devin/
git commit -m "refactor: move .devin/ to .codex/devin/ (canonical runtime)"
```

## Implementation Steps
1. Review `.devin/` contents with team
2. Determine appropriate option (A, B, or C)
3. Execute chosen option
4. Update governance documentation
5. Verify .gitignore consistency

## Acceptance Criteria
- [ ] Governance decision documented
- [ ] `.devin/` either ignored or documented as canonical
- [ ] AGENTS.md updated (if Option B)
- [ ] .github/root-allowlist.txt updated (if Option B)
- [ ] Consistency with other vendor AI directories
- [ ] CI passes

## Evidence
- File structure audit 2025-01-30
- `.devin/` contains 63 files (369 KB)
- Other vendor AI directories in .gitignore: .ai/, .agents/, .junie/, .qodo/, .sonarlint/, .windsurf/

## Related Issues
- File structure audit 2025-01-30
- Scripts governance audit (#5765)

## Labels
`governance`, `technical-debt`, `cleanup`, `ai-runtime`

## Estimate
2 hours (decision) + 1 hour (implementation)
