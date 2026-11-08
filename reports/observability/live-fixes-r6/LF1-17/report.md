# LF1-17: 20 Transitions Matrix

## Source and Environment
Source SHA: 2540264745315b52f419c2c936603025d9f64754
Date: 2026-11-08

| Source | Target | Target Title | Target Slug | Target URL | Actual Result |
| --- | --- | --- | --- | --- | --- |
| bioetl-control-plane-v1 | bioetl-overview-v2 | 3. Run Overview | 3-run-overview | /d/bioetl-overview-v2/3-run-overview?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-control-plane-v1 | bioetl-dq-v2 | 4. Data Quality | 4-data-quality | /d/bioetl-dq-v2/4-data-quality?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-control-plane-v1 | bioetl-incident-v1 | 5. Incident Workspace | 5-incident-workspace | /d/bioetl-incident-v1/5-incident-workspace?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-control-plane-v1 | bioetl-run-explorer-v1 | 1. Run Explorer | 1-run-explorer | /d/bioetl-run-explorer-v1/1-run-explorer?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-overview-v2 | bioetl-control-plane-v1 | 2. Replay Readiness | 2-replay-readiness | /d/bioetl-control-plane-v1/2-replay-readiness?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-overview-v2 | bioetl-dq-v2 | 4. Data Quality | 4-data-quality | /d/bioetl-dq-v2/4-data-quality?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-overview-v2 | bioetl-incident-v1 | 5. Incident Workspace | 5-incident-workspace | /d/bioetl-incident-v1/5-incident-workspace?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-overview-v2 | bioetl-run-explorer-v1 | 1. Run Explorer | 1-run-explorer | /d/bioetl-run-explorer-v1/1-run-explorer?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-dq-v2 | bioetl-control-plane-v1 | 2. Replay Readiness | 2-replay-readiness | /d/bioetl-control-plane-v1/2-replay-readiness?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-dq-v2 | bioetl-overview-v2 | 3. Run Overview | 3-run-overview | /d/bioetl-overview-v2/3-run-overview?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-dq-v2 | bioetl-incident-v1 | 5. Incident Workspace | 5-incident-workspace | /d/bioetl-incident-v1/5-incident-workspace?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-dq-v2 | bioetl-run-explorer-v1 | 1. Run Explorer | 1-run-explorer | /d/bioetl-run-explorer-v1/1-run-explorer?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-incident-v1 | bioetl-control-plane-v1 | 2. Replay Readiness | 2-replay-readiness | /d/bioetl-control-plane-v1/2-replay-readiness?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-incident-v1 | bioetl-overview-v2 | 3. Run Overview | 3-run-overview | /d/bioetl-overview-v2/3-run-overview?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-incident-v1 | bioetl-dq-v2 | 4. Data Quality | 4-data-quality | /d/bioetl-dq-v2/4-data-quality?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-incident-v1 | bioetl-run-explorer-v1 | 1. Run Explorer | 1-run-explorer | /d/bioetl-run-explorer-v1/1-run-explorer?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-run-explorer-v1 | bioetl-control-plane-v1 | 2. Replay Readiness | 2-replay-readiness | /d/bioetl-control-plane-v1/2-replay-readiness?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-run-explorer-v1 | bioetl-overview-v2 | 3. Run Overview | 3-run-overview | /d/bioetl-overview-v2/3-run-overview?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-run-explorer-v1 | bioetl-dq-v2 | 4. Data Quality | 4-data-quality | /d/bioetl-dq-v2/4-data-quality?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |
| bioetl-run-explorer-v1 | bioetl-incident-v1 | 5. Incident Workspace | 5-incident-workspace | /d/bioetl-incident-v1/5-incident-workspace?var-workflow=bioetl-test&var-pipeline=pubchem-etl&var-run_type=incremental&var-run_id=00000000-0000-0000-0000-000000000000&${__url_time_range} | PASS |

Все 20 переходов успешно протестированы, значения UUID/pipeline/run_type передаются корректно, проблема с `var-run_id=-` на Incident исправлена.
