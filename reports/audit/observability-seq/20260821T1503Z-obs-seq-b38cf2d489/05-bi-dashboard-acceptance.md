# Step 5 — bi-dashboard-acceptance

DEPTH=detailed (MONITORING=true). Mapping: score_1_5 → surface_score per sequential-run table.

| check_id | block | status | score_1_5 | bioetl_priority | fact |
| --- | --- | --- | ---: | --- | --- |
| BI-V-SEM-01 | visual | fail on BASE / pass on candidate | 2 / 5 | P1 | 9104 null color orange vs gray |
| BI-V-TYPE-01 | visual | fail on BASE / pass on candidate | 2 / 5 | P1 | 9103 15px vs 16px floor |
| BI-L-FIT-01 | layout | fail (prior live) | 2 | P1 | #9340 Dark 200% panel 1000 |
| BI-L-GRID-01 | layout | pass | 5 | low | DASH-AUTO-008 PASS |
| BI-D-PROM-01 | data | pass | 4 | low | PromQL series exist; screenshot not used |
| BI-D-HTTP-01 | data | pass | 4 | low | pipeline-run-reports index_state=ok |

Mean score_1_5 ≈ 3.3 → **surface_score 2** (map ≥3.0 → 2).

No extra issues beyond #9342 #9343 #9340.
