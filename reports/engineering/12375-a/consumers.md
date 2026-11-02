Git History Consumers in class-lane:
1. classify-changes: runs 'git diff --name-status base...head' and 'git merge-base origin/main HEAD'. Currently uses fetch-depth: 0.
2. class-lane -> pr-lane-results affected-tests: runs 'git diff --name-only base...head' and 'git show base:pyproject.toml'. Requires base commit to exist.
3. class-lane -> gitleaks: runs scanning over git history, so it needs commits from base to head.
Conclusion: class-lane requires fetch-depth: 0 because gitleaks needs commits and affected-tests needs 'git diff base...head' which requires the base commit to be reachable.
