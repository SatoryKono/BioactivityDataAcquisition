# Step 2 — grafana-audit.visual

JSON + static gate. Live WCAG ratios: **GAP** (no contrast meter this run). Screenshot does not prove data.

## DASH-AUTO (proposal, not SSOT)

| ID | Result | Note |
| --- | --- | --- |
| DASH-AUTO-001 | PASS | no includeAll with `$__all`/null |
| DASH-AUTO-002 | PASS | no table-wide `color-background` defaults |
| DASH-AUTO-012/013 | PASS (scanner) | not independently re-audited beyond visual-semantics |
| DASH-AUTO-015 | FAIL | nav HTML > 800 chars — expected shared bus; **not** a new issue |

**check-dashboard-visual-semantics:** FAIL on BASE (`9104` orange); PASS on candidate after gray restore.

**Typography:** authored 15px on DQ `9103` (#9343). Nav chips remain 16px / heading 19px (do not regress #9332).

Issues created this step: 0 (already #9342/#9343 from master wrapper).
