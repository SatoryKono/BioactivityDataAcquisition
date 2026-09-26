# Diagram freshness verification for #7316

Date: 2026-07-31

## Outcome

- Baseline: 86 diagram sources exceeded the 150-day error threshold.
- Reverified: 11 `views/*-full.mermaid` sources had an existing
  `%% Synced: 2026-07-08` evidence marker and passed the executable
  parent/body equality guard.
- Remaining: 75 sources still exceed 150 days. Their dates were not changed
  because the repository does not provide a source-identity or generated
  provenance anchor sufficient to claim current semantic verification.
- Remaining findings within the error-level stale subset: 75 `STALE-001`,
  14 `SIZE-002`, 2 decomposed-parent `SIZE-003`, 3 `LABEL-001`, and one
  `CLASS-003` warning.

## Evidence

The refreshed full views declare their canonical parent via `%% Parent source`
and already recorded synchronization on 2026-07-08. The architecture test
`test_full_mermaid_matches_foundation_mmd` confirms exact diagram-body parity
between every full view and its declared parent. Metadata was normalized to
that recorded synchronization date, not to the current date.

Validation:

```text
/home/fedor/.venvs/bioetl/bin/python -m pytest \
  tests/architecture/test_diagram_drift_and_embed_guards.py::test_full_mermaid_matches_foundation_mmd \
  tests/architecture/test_diagram_lint_policy_rules.py -q
17 passed
```

The remaining canonical architecture, class, and foundation sources require
owner review against their live code/config/ADR surfaces. Timestamp-only bulk
refresh would hide rather than resolve semantic drift and was intentionally
not performed.

The four tractable label/signature warnings were evaluated, but their source
edits were not retained because the repository requires synchronized render
baselines and the local Mermaid CLI is 11.12.0 while ADR-040 pins 10.6.1.
The renderer correctly failed closed on this version mismatch. Those warnings
remain for a follow-up in an environment with the pinned renderer.
