---
id: recheck-github-token-20260531
title: Recheck GITHUB_TOKEN auth
task_id: recheck-github-token-20260531
created_at: '2026-05-31T13:22:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/ops/support/load_repo_env.sh
summary: Verified that GITHUB_TOKEN from repo .env authenticates successfully against
  GitHub API with HTTP 200, while GITHUB_PERSONAL_ACCESS_TOKEN returns HTTP 401 Bad
  credentials; the two secrets are different values, which explains the earlier publish
  failure when the invalid alias was selected.
---

# Episodic summary

## Task

- Title: Recheck GITHUB_TOKEN auth

## Outcome

- Verified that GITHUB_TOKEN from repo .env authenticates successfully against GitHub API with HTTP 200, while GITHUB_PERSONAL_ACCESS_TOKEN returns HTTP 401 Bad credentials; the two secrets are different values, which explains the earlier publish failure when the invalid alias was selected.

## Lessons learned

- Replace with durable follow-up if needed
