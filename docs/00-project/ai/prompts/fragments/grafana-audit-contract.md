---
id: prompt.fragment.grafana-audit-contract
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Shared evidence, severity, and release-gate contract for Grafana audits
---

## Grafana audit contract

The audit is evidence-first and read-only by default. Do not edit dashboard
JSON, provisioning, queries, recording rules, tests, or docs; do not create
issues or PRs unless a separate operator workflow explicitly authorizes writes.

### Evidence precedence

| Claim | Minimum acceptable evidence |
| --- | --- |
| Shipped structure/config | actual `grafana/dashboards/*.json` or the retrieved dashboard resource |
| Render/readability | reproducible screenshot, panel render, or inspected DOM/CSS at a recorded viewport/theme |
| Datasource/query behavior | datasource identity plus executed panel request/result or exact blocker |
| Business/metric semantics | metric catalog, SLO/BI specification, accepted contract, or reference query |
| Regression | comparable baseline/candidate artifacts with the same time range, variables, viewport, and theme |

A screenshot may prove a visual defect but MUST NOT prove data correctness.
Dashboard JSON is required for layout and query configuration claims, but it
does not prove that a datasource returned correct data. Documentation is a
contract/drift source, not a substitute for shipped JSON or live evidence.

Do not assume a Grafana version or API model. Detect the actual version and
whether the dashboard uses V2 Resource, V1 Resource, or Classic JSON. Select
supported API/MCP tools from that evidence; an unavailable endpoint is a GAP,
not proof that the dashboard is defective.

### Required distinctions

Always distinguish:

- valid zero;
- expected empty/no matching rows;
- selection required or not applicable;
- missing/null/NaN series;
- stale or delayed telemetry;
- selector or variable interpolation error;
- query/transformation error;
- datasource/backend/auth failure;
- Grafana rendering failure.

Do not invent dashboard UIDs, panel IDs, metrics, labels, datasources,
environments, tenants, thresholds, or expected values. Mark unavailable facts
as `[неполные данные]` and record the exact evidence needed to resolve them.

### Finding contract

Each actionable finding must contain:

`dashboard`, `panel_id`, `panel_title`, `category`, `evidence_ids`, `expected`,
`actual`, `impact`, `severity`, `confidence`, `recommended_fix`, and
`verification_test`.

Evidence IDs use: `JSON-`, `SHOT-`, `DOM-`, `QUERY-`, `DS-`, `API-`, `REF-`,
`TEST-`, or `DOC-`. Label claims as `FACT`, `INFERENCE`, `GAP`, or
`CONTRADICTION`.

| Severity | Meaning |
| --- | --- |
| P0 | wrong data/time/aggregation semantics can cause an incorrect operational or BI decision |
| P1 | a critical signal, source/filter, or state is materially misleading or practically indistinguishable |
| P2 | diagnosis, navigation, performance, or maintenance is materially impaired without immediate wrong-decision risk |
| P3 | localized consistency/cosmetic defect with a concrete readability or task impact |

Confidence is `0..1`. A data P0/P1 needs reproducible query/reference evidence;
otherwise report it as provisional and place it in evidence gaps.

### BioETL overlay

- Shipped dashboard source: `grafana/dashboards/`.
- Use `.codex/skills/observability-dashboard/SKILL.md` for repository tooling.
- Current status, selected-range evidence, exact-run evidence, and telemetry
  confidence are different scopes and must not be presented as peers.
- Preserve the project verdict ontology and explicit zero/empty/unknown rules.
- Classic `gridPos` uses 24 columns; top-level panels must not overlap or leave
  unexplained gaps.
- Monitoring is optional. Do not start `docker-compose.monitoring.yml` unless
  `MONITORING=true` and UI/live-query evidence is necessary.
- Never expose tokens, datasource credentials, private URLs, or sensitive query
  results in reports or screenshots.

### Production-critical release gate

`PASS` requires all of the following when applicable and verifiable:

- `P0 == 0` and `P1 == 0`;
- critical-panel lineage coverage is `100%`;
- mandatory integrity tests pass at `100%`;
- critical text and graphical contrast pass the chosen WCAG AA gate;
- critical color-only status encoding count is `0`;
- baseline P0/P1 findings are retested at `100%`;
- new P0/P1 regressions are `0`.

Unavailable mandatory evidence yields `BLOCKED` or `NOT VERIFIABLE`, never a
synthetic PASS. Technical-debt budgets and exception limits must not increase.
