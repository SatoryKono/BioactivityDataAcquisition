# Step 1 — grafana-audit.master

Read-only audit then issue/close wrapper. JSON SSOT: `grafana/dashboards/*.json`.

**Identity:** repo `SatoryKono/BioactivityDataAcquisition`, BASE `b38cf2d489`, Grafana **12.0.0**, timezone browser, refresh 60s.

**Page goals (one line)**

| UID | Goal |
| --- | --- |
| Trust | Is replay/resume safe for the selected pipeline right now? |
| Overview | Is the fleet OK, and what is the first action? |
| Runtime | Which pipeline stage is failing and why? |
| Provider | Which provider is non-OK, and is telemetry present? |
| DQ | What is current DQ status vs thresholds? |
| Incident | What is firing and who are the ranked suspects? |
| Run Explorer | Which recent runs exist, and what is the selected-run identity? |

**Backlog (PROVEN P0–P2)**

1. **#9342** DASH-STATE-002 panel 9104 null→orange (P1) — fix on branch, closeout BLOCKED vs origin/main. Related closed #9330 not reopened.
2. **#9343** DASH-TYPOGRAPHY-001 panel 9103 15px (P1) — fix on branch.
3. **#9340** DASH-FIT-004 panel 1000 Dark 200% — existing, no second ticket.

**surface_score:** 2 (acceptable). Visual-semantics gate broken on BASE; inventory/perf/density green.

**grafana-six:** not executed.
