---
id: close-4909-4910-github-actions-policy
title: Close 4909 and 4910 GitHub Actions policy debt
task_id: close-4909-4910-github-actions-policy
created_at: '2026-06-01T14:06:15Z'
ttl_days: 14
confidence: episodic
source_refs:
- user-request-close-4909-4910
summary: 'Implemented GitHub Actions SHA pinning and permissions hardening. Replaced
  mutable setup-uv, github-script, labeler, and stale refs with full SHAs; expanded
  check_github_actions_runtime_policy.py to scan workflows and composite actions and
  fail on unknown/tag refs; added architecture regression tests; added least-privilege
  permissions to contract-tests.yml; updated governance docs. Validated policy checker,
  YAML parse, ruff, targeted pytest, repo-wide unpinned external uses scan, and scoped
  hygiene. Closed #4909 and #4910 completed via GitHub API.'
---

# Episodic summary

## Task

- Title: Close 4909 and 4910 GitHub Actions policy debt

## Outcome

- Implemented GitHub Actions SHA pinning and permissions hardening. Replaced mutable setup-uv, github-script, labeler, and stale refs with full SHAs; expanded check_github_actions_runtime_policy.py to scan workflows and composite actions and fail on unknown/tag refs; added architecture regression tests; added least-privilege permissions to contract-tests.yml; updated governance docs. Validated policy checker, YAML parse, ruff, targeted pytest, repo-wide unpinned external uses scan, and scoped hygiene. Closed #4909 and #4910 completed via GitHub API.

## Lessons learned

- Replace with durable follow-up if needed
