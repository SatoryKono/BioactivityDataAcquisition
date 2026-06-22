---
id: close-5486-duplication-first-wave-20260622
title: Close issue 5486 duplication first wave
task_id: close-5486-duplication-first-wave-20260622
created_at: '2026-06-22T15:53:27Z'
ttl_days: 14
confidence: episodic
source_refs:
- https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5486
summary: 'Closed issue #5486 by executing the first duplication reduction wave for
  src/bioetl/interfaces/cli. Reused EXCEPTION_EXIT_CODES as the single source for
  run-status failure overrides, reducing CLI duplicate clusters from 13 to 12 and
  full-app duplicate clusters from 109 to 108. Added an architecture ratchet test
  for issue #5486, regenerated full-app duplication baseline, module coverage inventory,
  and architecture quality scorecard. Validation passed for duplication governance,
  architecture scorecard, CLI exit-code/unit boundary tests, ruff, and duplication
  max-cluster check; WSL module hash guard skipped by repo policy.'
---

# Episodic summary

## Task

- Title: Close issue 5486 duplication first wave

## Outcome

- Closed issue #5486 by executing the first duplication reduction wave for src/bioetl/interfaces/cli. Reused EXCEPTION_EXIT_CODES as the single source for run-status failure overrides, reducing CLI duplicate clusters from 13 to 12 and full-app duplicate clusters from 109 to 108. Added an architecture ratchet test for issue #5486, regenerated full-app duplication baseline, module coverage inventory, and architecture quality scorecard. Validation passed for duplication governance, architecture scorecard, CLI exit-code/unit boundary tests, ruff, and duplication max-cluster check; WSL module hash guard skipped by repo policy.

## Lessons learned

- Replace with durable follow-up if needed
