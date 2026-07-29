Parent: #7167

Task ID: `GRA-RT-04`
Priority: `P2`

## Problem

The optional Quarantine Explorer backend was unavailable during render
preflight while every required Grafana panel still reached a valid terminal
state. Current evidence cannot distinguish an intentionally absent optional
backend from an unexpected outage, so the audit must retain `UNKNOWN`.

## Evidence

- `reports/observability/grafana/render-audit-20260729/AUDIT.md`
- canonical Grafana audit preflight output from 2026-07-29
- 1440×900 full-page Playwright manifest with 193/193 checked panels

Evidence source: `RUNTIME_RENDER`, `BROWSER_INSPECTION`

Confidence: `FACT`

## Scope

1. Define whether Quarantine Explorer is applicable for each supported local
   runtime profile.
2. Represent backend state as `AVAILABLE`, `UNAVAILABLE`, `NOT_APPLICABLE`, or
   `UNKNOWN`.
3. Record the applicability decision and health probe outcome in render
   manifests without exposing endpoint credentials.
4. Ensure optional absence does not fail unrelated dashboard rendering.
5. Ensure an expected-but-unavailable backend produces an actionable preflight
   failure.

## Acceptance criteria

- [ ] Applicability is derived from a canonical runtime contract, not guessed
      from connection failure.
- [ ] Render manifests use the four explicit states.
- [ ] `NOT_APPLICABLE` is not reported as an error.
- [ ] `UNAVAILABLE` includes the failed probe class and an operator-safe action.
- [ ] Dashboard panel completion and backend health remain separate fields.
- [ ] ADR-010 optional-monitoring semantics remain intact.
- [ ] No `.env` file is modified as part of the implementation.

## Validation

```bash
.venv/bin/python -m scripts.ops check-grafana-audit-preflight
.venv/bin/python -m pytest -q tests/integration/test_grafana_render_*.py
```

## Out of scope

- making Quarantine Explorer mandatory;
- restoring retired Loki, Tempo, or Quarantine UI surfaces;
- changing retention or technical-debt budgets.

