# Branch Consolidation Plan

*Date: 2026-02-24 | Author: Claude Code*

---

## 1. Current State Summary

| Metric | Value |
|--------|-------|
| Total remote branches | **2,159** |
| Merged into master | **2** |
| Based on current history (new) | **1** (`chore/github-templates`) |
| Based on OLD history (no common ancestor) | **~2,156** |
| master/main commit count | 88 / 94 |
| master/main start date | 2026-02-23 |
| Oldest branch date | 2025-12 |

### Branch Categories

| Source | Count | % |
|--------|-------|---|
| Claude Code | 1,586 | 73% |
| Codex | 266 | 12% |
| Bolt | 58 | 3% |
| Manual (feat/fix/refactor) | 78 | 4% |
| Copilot | 19 | 1% |
| Jules | 9 | <1% |
| Dependabot | 8 | <1% |
| Other (audit, arch, etc.) | 135 | 6% |

### Critical Finding

The repository underwent a **history reset** around 2026-02-23 (PR #2312). The current
`master`/`main` branches have **no common ancestor** with ~2,156 of 2,159 remote branches.
This means:

- Standard `git merge` will not work (unrelated histories)
- 91% of branches are 2,000+ commits "ahead" — but these are from a **different git tree**
- Branches contain massive duplication (e.g., 93 branches for "architecture-review-refactor")

---

## 2. Branch Triage Classification

### Tier 1: MERGE — Directly mergeable (common ancestor exists)

| Branch | Commits | Action |
|--------|---------|--------|
| `chore/github-templates` | +4 | Review & merge via PR |

### Tier 2: CHERRY-PICK — Potentially valuable changes from old history

Candidates for cherry-picking specific commits into current master:

| Category | Branches | Strategy |
|----------|----------|----------|
| `dependabot/*` (8) | Dependency updates | Re-run dependabot on current master instead |
| Recent `claude/fix-*` | Bug fixes | Evaluate if fixes still apply to current code |
| `claude/audit-*-refactor` (recently merged PRs) | Refactors | Already merged via PRs #2364-#2367 |

### Tier 3: ARCHIVE — Historical value only, no merge needed

| Category | Count | Reason |
|----------|-------|--------|
| `claude/architecture-review-refactor-*` | 93 | Duplicate iterations; value already captured |
| `claude/consolidate-refactoring-plans-*` | 36 | Planning branches; work superseded |
| `claude/audit-bioetl-architecture-*` | 36 | Audit reports; read-only artifacts |
| `claude/fix-lint-type-*` | 30 | Lint fixes; likely outdated against current code |
| `claude/fix-architecture-metrics-*` | 29 | Metrics fixes; superseded |
| `codex/conduct-architectural-audit-*` | 16 | Audit branches; read-only |
| Most `bolt-*` | 58 | Bolt.new experiments; independent work |
| All `copilot/*` | 19 | Copilot suggestions; not reviewed |
| All `jules/*` | 9 | Jules experiments; not reviewed |

### Tier 4: DELETE — No value, safe to remove

| Category | Count | Reason |
|----------|-------|--------|
| Failed/incomplete AI agent runs | ~1,500+ | Single-commit branches with only docs/reports |
| Duplicate iterations of same task | ~400+ | 93 branches for one task = 92 duplicates |
| Stale dependabot PRs | 8 | Superseded by newer dependency versions |

---

## 3. Recommended Consolidation Strategy

### Phase 1: Immediate Cleanup (safe, no data loss)

**Estimated branch reduction: ~2,100 branches**

```bash
# Step 1: Sync master with origin/main (master is 6 commits behind)
git checkout master
git pull origin main

# Step 2: Merge the one directly mergeable branch
gh pr create --base main --head chore/github-templates \
  --title "chore: add PR and issue templates" \
  --body "Branch consolidation - Tier 1 merge"

# Step 3: Tag old history for reference before cleanup
git tag archive/pre-consolidation-2026-02-24 origin/main
```

### Phase 2: Extract Value from Old Branches

Before deleting, extract any unique documentation or reports:

```bash
# For each Tier 2 branch, check if changes apply to current code:
for branch in <tier-2-list>; do
  git diff origin/main..origin/$branch -- src/ | head -100
  # If relevant, cherry-pick with --allow-unrelated-histories
done
```

Key areas to check:
- **Codex setup scripts** (`codex/create-setup-script-*`) — may have useful CI setup
- **Documentation improvements** (`claude/update-bioetl-docs-*`) — check for content
- **Test improvements** (`claude/optimize-bioetl-tests-*`) — check for test patterns

### Phase 3: Bulk Branch Deletion

```bash
# Delete all old-history branches in batches (by category)
# IMPORTANT: First create a local backup of branch list

git branch -a --no-merged master | grep 'remotes/origin/' \
  | sed 's|remotes/origin/||' > /tmp/branches-to-delete.txt

# Delete in batches of 50 to avoid API rate limits
cat /tmp/branches-to-delete.txt | xargs -n50 -I{} \
  git push origin --delete {}
```

Suggested deletion order (safest first):
1. `claude/architecture-review-refactor-*` (93 branches, pure duplicates)
2. `claude/consolidate-refactoring-plans-*` (36 branches)
3. `claude/audit-bioetl-architecture-*` (36 branches)
4. `claude/fix-lint-type-*` (30 branches)
5. `jules/*`, `copilot/*` (28 branches, unreviewed)
6. `bolt-*` (58 branches, experiments)
7. All remaining `claude/*` old-history branches
8. All remaining `codex/*` old-history branches
9. Other old-history branches

### Phase 4: Hygiene Rules Going Forward

1. **Auto-delete branches after PR merge** — enable in GitHub repo settings
2. **Branch naming convention** — enforce `{agent}/{task}-{id}` pattern
3. **Stale branch bot** — set up GitHub Actions to flag branches >7 days old with no PR
4. **Agent session limit** — limit AI agents to max 3 concurrent branches per task type

---

## 4. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Losing unique changes | MEDIUM | Phase 2 extraction before deletion |
| Breaking open PRs | LOW | Only 2 branches are merged; no open PRs found |
| Git tag reference loss | LOW | Tag old history before cleanup |
| GitHub API rate limit | LOW | Batch deletions in groups of 50 |

---

## 5. Expected Outcome

| Metric | Before | After |
|--------|--------|-------|
| Remote branches | 2,159 | ~10-20 |
| Mergeable branches | 1 | 0 (all merged) |
| Old-history branches | 2,156 | 0 (archived via tag) |
| Branch overhead | High (confusion, slow fetch) | Minimal |

---

## 6. Execution Checklist

- [ ] Sync `master` with `origin/main`
- [ ] Review and merge `chore/github-templates`
- [ ] Create archive tag `archive/pre-consolidation-2026-02-24`
- [ ] Extract Tier 2 value (codex scripts, docs, tests)
- [ ] Delete Tier 4 branches (batch 1: duplicates)
- [ ] Delete Tier 3 branches (batch 2: historical)
- [ ] Enable auto-delete on merge in GitHub settings
- [ ] Set up stale branch cleanup automation
- [ ] Verify `git fetch` performance after cleanup
