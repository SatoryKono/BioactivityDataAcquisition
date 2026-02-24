# BioETL DQ v2 Panel Migration Anchors (P2.5)

Date: 2026-02-24
Scope: `grafana/dashboards/bioetl-dq-v2.json`

## 1) Explicit inventory before JSON changes

|  ID | Current title                                         | Intent (why panel exists)                                               | Migration decision                             |
| --: | ----------------------------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------- |
|  99 | Pipeline                                              | Show selected pipeline context for all DQ panels.                       | **Retain (mandatory)**                         |
| 100 | Run Type                                              | Show selected run type context for all DQ panels.                       | **Retain (mandatory)**                         |
|   1 | Data Flow: Bronze -> Silver -> Gold (Latest Run Only) | Stage-level flow view for latest run and stage comparison.              | Retain                                         |
|   2 | Data Quality Score                                    | Aggregate quality gauge based on processed totals.                      | **Superseded** by panel 5 + new panel 13       |
|   3 | Source Records (Bronze)                               | Input volume anchor for quality ratios and incident rates.              | **Retain (mandatory)**                         |
|   4 | Clean Records (Gold)                                  | Output quality volume anchor (clean records).                           | **Retain (mandatory)**                         |
|   5 | DQ Validation Score                                   | Validation quality gauge from DQ metric (`bioetl_dq_validation_score`). | **Retain (mandatory)**                         |
|   6 | Records Quarantined (24h)                             | Absolute DQ incident counter over 24h.                                  | **Retain (mandatory)**                         |
|   7 | Soft Threshold Exceeded (24h)                         | Count of soft-threshold breaches in 24h.                                | **Superseded** by new trend panel 14           |
|   8 | Data Freshness (seconds)                              | Freshness lag indicator for ingested data.                              | Retain                                         |
|   9 | Quarantine by Error Type (24h)                        | Error composition and dominant failure type analysis.                   | Retain                                         |
|  10 | Anomalies Detected (1h)                               | Critical anomaly detection timeline by severity/type.                   | **Retain (mandatory, critical no-regression)** |
|  11 | DQ Check Duration (p95)                               | Critical validation runtime/performance timeline (p95).                 | **Retain (mandatory, critical no-regression)** |
|  12 | Silver Validation Failures (24h)                      | Data contract/schema failure counter in Silver layer.                   | Retain                                         |
| 101 | Execution Timestamp                                   | Latest-run temporal anchor for incident analysis.                       | **Retain (mandatory)**                         |

## 2) Superseded vs retained decision (explicit)

### Superseded panels

- **ID 2 / `Data Quality Score`** → superseded by:
  - retained **ID 5 / `DQ Validation Score`** (primary quality gauge), and
  - new **ID 13 / `DQ Incident Rate (24h, %)`** (rate-oriented DQ risk metric).
- **ID 7 / `Soft Threshold Exceeded (24h)`** → superseded by:
  - new **ID 14 / `Soft Threshold Exceeded Trend (24h)`** (time trend instead of single aggregate stat).

### Retained panels

- Mandatory retained set: **99, 100, 3, 4, 5, 6, 10, 11, 101**.
- Additional retained set: **1, 8, 9, 12**.

## 3) Rewritten P2.5 acceptance criteria (replacing "total panels = 7")

### P2.5.A Mandatory retained panels (migration anchors)

The resulting dashboard **MUST** contain these existing anchors unchanged by identity (ID + title):

- `99 / Pipeline`
- `100 / Run Type`
- `3 / Source Records (Bronze)`
- `4 / Clean Records (Gold)`
- `5 / DQ Validation Score`
- `6 / Records Quarantined (24h)`
- `10 / Anomalies Detected (1h)`
- `11 / DQ Check Duration (p95)`
- `101 / Execution Timestamp`

### P2.5.B Mandatory new panels

The resulting dashboard **MUST** add these new anchors:

- `13 / DQ Incident Rate (24h, %)`
  - Intent: normalized DQ incident rate (e.g., quarantined vs bronze volume) for cross-run comparability.
- `14 / Soft Threshold Exceeded Trend (24h)`
  - Intent: temporal dynamics of soft-threshold breaches (trend visibility instead of only one aggregate).

### P2.5.C Explicitly deprecated panels

The resulting dashboard **MUST** deprecate and remove these legacy panels after new anchors are in place:

- `2 / Data Quality Score`
- `7 / Soft Threshold Exceeded (24h)`

### P2.5.D No overlap / no regression safeguards

- **No overlap**: each deprecated panel maps to exactly one retained/new successor:
  - `2` → `5` + `13`
  - `7` → `14`
- **No regression (critical existing views)**:
  - `10 / Anomalies Detected (1h)` MUST remain present and query-equivalent in intent.
  - `11 / DQ Check Duration (p95)` MUST remain present and query-equivalent in intent.
- **Identity lock**: migrations MUST validate panel anchors by `(id, title)` to avoid accidental deletions/renames.
