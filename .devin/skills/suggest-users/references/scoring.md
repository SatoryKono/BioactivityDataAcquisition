# Reviewer And Assignee Scoring

Use this reference with `suggest-users` when ranking reviewers or issue
assignees.

## Reviewer Signals

| Signal | Points | Notes |
| --- | ---: | --- |
| CODEOWNERS match | +50 | Explicit ownership wins over heuristics. |
| Commits to changed files in last 30 days | +10 each | Cap manually if one user dominates noise. |
| Recent PR reviews | +5 each, max +25 | Active reviewer signal. |
| Recent PR authorship | +3 each, max +15 | Active contributor signal. |
| Same team membership | +10 | Use only when team membership is known. |
| Open review load | -3 each | Balance workload. |
| Is PR author | -100 | Do not suggest self-review. |

## Assignee Signals

| Signal | Points | Notes |
| --- | ---: | --- |
| Recent closed issues with same label | +10 each | Domain familiarity. |
| Recent commits to related files | +5 each | Code familiarity. |
| Explicit mention in issue | +20 | Stakeholder indication. |
| Current open issue count | -2 each | Balance workload. |

## Data Sources

Prefer, in order:

1. CODEOWNERS.
1. GitHub collaborator or team data when available.
1. Recent PR review/authorship history.
1. File-specific `git log`.
1. Manual user selection when API access is unavailable.

## Edge Cases

- No CODEOWNERS: use file contributors and recent reviewers.
- No recent activity: extend the window to 90 days, then fall back to
  collaborators.
- Single contributor repo: recommend a self-review checklist instead of
  external reviewer assignment.
- API unavailable: state the missing data and rank only from local evidence.

