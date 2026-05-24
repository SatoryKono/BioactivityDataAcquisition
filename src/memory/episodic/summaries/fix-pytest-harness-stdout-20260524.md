---
id: fix-pytest-harness-stdout-20260524
title: Make pytest stdout/status reliable through current harness
task_id: fix-pytest-harness-stdout-20260524
created_at: '2026-05-24T13:53:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/dev/run_pytest.sh
summary: Verified that direct pytest invocation is unreliable in this mixed WSL checkout,
  while bash scripts/engineering/dev/run_pytest.sh --skip-preflight ... returns stable
  stdout and exit status through the harness because it constrains plugin autoload
  and normalizes the runtime.
---

# Episodic summary

## Task

- Title: Make pytest stdout/status reliable through current harness

## Outcome

- Verified that direct pytest invocation is unreliable in this mixed WSL checkout, while bash scripts/engineering/dev/run_pytest.sh --skip-preflight ... returns stable stdout and exit status through the harness because it constrains plugin autoload and normalizes the runtime.

## Lessons learned

- Replace with durable follow-up if needed
