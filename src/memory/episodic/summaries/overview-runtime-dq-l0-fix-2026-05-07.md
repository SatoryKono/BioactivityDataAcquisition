---
id: overview-runtime-dq-l0-fix-2026-05-07
title: Fix Overview runtime and DQ L0 status materialization
task_id: overview-runtime-dq-l0-fix-2026-05-07
created_at: '2026-05-07T18:22:45Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Rewrote bioetl_l0_input_status runtime rule to normalize stage-scoped blocker
  signals before aggregation and rewired dq rule to project canonical bioetl_dq_current_status
  onto the overview run_type universe. promtool check/test passed, live Prometheus
  now materializes runtime=2/2/0/0 and dq=0/0/0/0 instead of UNKNOWN fallback in L0
  Inputs. Broader overview pytest pack still has two unrelated pre-existing contract
  failures outside this rule change.
---

# Episodic summary

## Task

- Title: Fix Overview runtime and DQ L0 status materialization

## Outcome

- Rewrote bioetl_l0_input_status runtime rule to normalize stage-scoped blocker signals before aggregation and rewired dq rule to project canonical bioetl_dq_current_status onto the overview run_type universe. promtool check/test passed, live Prometheus now materializes runtime=2/2/0/0 and dq=0/0/0/0 instead of UNKNOWN fallback in L0 Inputs. Broader overview pytest pack still has two unrelated pre-existing contract failures outside this rule change.

## Lessons learned

- Replace with durable follow-up if needed
