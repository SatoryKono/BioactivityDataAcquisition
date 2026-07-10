# Suggest Users Workflow

Use this reference when `suggest-users` needs concrete command patterns or an
output template. Prefer local evidence and GitHub API results from the current
repository.

## Reviewer Data Collection

```bash
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
gh pr view {PR_NUMBER} --json files --jq '.files[].path'
gh api repos/$REPO/contents/.github/CODEOWNERS --jq '.content' 2>/dev/null | base64 -d
gh api repos/$REPO/contents/CODEOWNERS --jq '.content' 2>/dev/null | base64 -d
gh api repos/$REPO/collaborators --jq '.[] | select(.permissions.push) | .login'
gh pr list --state merged --limit 30 --json author,reviews --jq '.[].author.login, .[].reviews[].author.login'
git log --format='%an' --since="30 days ago" -- {changed_files}
```

## Issue Assignee Data Collection

```bash
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
gh api repos/$REPO/collaborators --jq '.[] | select(.permissions.push) | .login'
gh issue list --state closed --limit 30 --label "{label}" --json assignees --jq '.[].assignees[].login'
gh issue list --state open --json assignees --jq '.[].assignees[].login'
```

## CODEOWNERS Notes

- More specific patterns take precedence over broad patterns.
- Multiple owners may be listed for one pattern.
- Team owners (`@org/team`) require team membership lookup before ranking
  individual users; if membership is unavailable, report the team as owner.

## Integration Points

- PR creation: rank reviewers from changed files and ownership.
- PR re-review: start with previous reviewers and comment authors, then apply
  workload and availability filters.
- Issue triage: use labels, title terms, linked files, and prior issue
  assignees.

## Output Template

```markdown
## User Suggestions

Context: {PR/Issue} #{number}
Data used: {sources}
Missing data: {sources or none}

| Rank | User | Score | Reasons |
| ---: | --- | ---: | --- |
| 1 | @{user1} | {score} | {primary reasons} |
| 2 | @{user2} | {score} | {primary reasons} |
| 3 | @{user3} | {score} | {primary reasons} |

Recommendation: @{user1}
Confidence: {high/medium/low}
Fallback: {manual selection note when needed}
```
