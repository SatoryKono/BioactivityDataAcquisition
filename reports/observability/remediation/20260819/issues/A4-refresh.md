## Problem

All seven dashboards ship `"refresh": "60s"`, but Grafana UI/kiosk/URL combinations can show auto-refresh off. Operators then misread freshness.

## Proposed solution

Show **effective refresh** and timezone in the shared scope header. Add a contract test that URL `refresh=60s` (and `refresh=off`) is reflected in dashboard JSON and, where automatable, in the Playwright header chip.

## Scope

Shared header HTML/text panels, `test_dashboard_*` / render contract. No change to default JSON refresh unless a test proves it is wrong.

## Alternatives considered

Removing dashboard refresh entirely — rejected.

## Acceptance criteria

- [ ] Header shows resolved refresh mode + timezone.
- [ ] Test covers URL `refresh=` vs shipped JSON.
- [ ] ADR-010: no new local monitoring Docker requirement.

Parent: DASH-SCOPE epic. P2; do not block P0 A/B/C.
