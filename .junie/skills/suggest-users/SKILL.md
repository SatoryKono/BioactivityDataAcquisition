---
name: "suggest-users"
description: "Use when creating PRs to suggest reviewers, when creating issues to suggest assignees, or when re-requesting review after addressing comments. Ranks users by CODEOWNERS match, file expertise, recent activity, and workload balancing."
allowed-tools:
  - Bash
  - Read
context: "fork"
agent: "Explore"
---

# Suggest Users

Suggest reviewers or assignees from repository ownership, activity, expertise,
and workload signals. Use this skill only for suggestion/ranking; the caller
still decides whether to request review, assign an issue, or leave ownership
manual.

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- CODEOWNERS and GitHub permissions when available

## Progressive Disclosure

Read only the references needed for the current request:

- [references/scoring.md](references/scoring.md) - signal weights, data source
  order, and edge cases.
- [references/workflow.md](references/workflow.md) - command patterns,
  CODEOWNERS matching notes, integration points, and output shape.

## Workflow

1. Identify context: PR reviewer suggestion, issue assignee suggestion, or
   reviewer re-engagement.
1. Gather available signals in parallel: changed files, CODEOWNERS,
   collaborators, recent PR/issue activity, file-specific commit history, and
   current review/issue load.
1. Score candidates with [references/scoring.md](references/scoring.md).
1. Exclude invalid candidates such as the PR author, unavailable users, or
   users without required repository access.
1. Present the top candidates with concise reasons and any missing-data caveats.
1. If all signals are weak, recommend manual selection instead of pretending the
   ranking is strong.

## Output Contract

Return:

- context (`PR`, `issue`, or `review re-request`)
- data sources used and missing
- top 3 candidates with scores and primary reasons
- recommendation with confidence
- fallback/manual-selection note when confidence is low

## Guardrails

- Do not invent repository permissions, team membership, or ownership.
- Do not suggest self-review for a PR author.
- Do not use activity volume alone as ownership proof.
- Always allow the user to override the recommendation.
