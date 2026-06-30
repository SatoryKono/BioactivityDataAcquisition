# Issue: Add Cache Directories to .gitignore

## Type
- [ ] Feature
- [ ] Bug
- [x] Technical Debt
- [ ] Cleanup

## Priority
- [ ] P0 (Critical)
- [ ] P1 (High)
- [x] P2 (Medium)
- [ ] Low

## Context
Based on the file structure audit (2025-01-30), two cache directories are not in .gitignore despite being transient regenerable artifacts.

## Problem
- `.import_linter_cache/` (1.2 MB) not in .gitignore
- `.coverage-sharded-current-main/` (0 KB) not in .gitignore
- These are transient cache directories that should be ignored
- Inconsistent with other cache directories (all in .gitignore)
- Potential disk waste (~1.2 MB)

## Impact
- Disk waste (~1.2 MB)
- Inconsistent .gitignore coverage
- Potential accidental tracking of cache artifacts
- CI/CD may include cache artifacts in builds

## Proposed Solution
Add both directories to .gitignore:
```bash
echo ".import_linter_cache/" >> .gitignore
echo ".coverage-sharded-current-main/" >> .gitignore
git add .gitignore
git commit -m "chore: add cache directories to .gitignore"
```

## Implementation Steps
1. Verify directories are cache (not source)
2. Add to .gitignore
3. Clean up local cache
4. Commit changes
5. Verify CI passes

## Acceptance Criteria
- [ ] `.import_linter_cache/` added to .gitignore
- [ ] `.coverage-sharded-current-main/` added to .gitignore
- [ ] Local cache cleaned
- [ ] .gitignore committed
- [ ] CI passes
- [ ] No accidental tracking of cache artifacts

## Evidence
- File structure audit 2025-01-30
- `.import_linter_cache/` = 1.2 MB
- `.coverage-sharded-current-main/` = 0 KB
- Other cache directories in .gitignore: .pytest_cache/, .ruff_cache/, .hypothesis/, .benchmarks/

## Related Issues
- File structure audit 2025-01-30
- Scripts governance audit (#5765)

## Labels
`cleanup`, `technical-debt`, `gitignore`

## Estimate
1 hour
