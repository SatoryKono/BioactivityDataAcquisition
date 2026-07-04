# BioETL Dashboard And Export RBAC Matrix

Last verified: 2026-06-30

This matrix governs the local-only Grafana, drilldown, and export surfaces used
by the observability rollout. It does not replace backend authorization; hidden
panels are not considered a security boundary.

| Role | Dashboard folders | Prometheus datasource | Quarantine Explorer drilldown | Governed export | Raw payload access |
| --- | --- | --- | --- | --- | --- |
| `viewer` | Read aggregate dashboards | Read aggregate metrics only | Summary selectors only | Redacted CSV/TSV/XLSX only | No |
| `investigator` | Read aggregate and forensic dashboards | Read aggregate metrics only | Record-level drilldown with audit | Export with default redaction; raw profile allowed by backend policy | Audited backend only |
| `exporter` | Read aggregate dashboards | Read aggregate metrics only | Summary selectors only | Export with raw profile when authorized | Audited backend only |
| `admin` | Manage local dashboards/provisioning | Manage datasource provisioning | Manage drilldown backend | Full governed export policy | Audited backend only |

Security rules:

- Grafana MUST NOT expose raw storage, raw Bronze/Silver payload tables, or
  filesystem paths as datasources.
- Prometheus labels MUST NOT include `run_id`, `record_id`, `payload_hash`,
  manifest IDs, execution fingerprints, file paths, or raw payload identifiers.
- `$run_id`, `$quarantine_run_id`, and `$payload_hash` are backend drilldown
  selectors, not global Prometheus labels.
- Direct raw payload access must be authorized by the backend/export surface and
  audited there; hiding a panel is not authorization.
- Service account tokens and secrets MUST NOT be committed in dashboard JSON,
  datasource provisioning, docs, or generated reports.

Enforcement references:

- Dashboard datasource and query contracts:
  `tests/integration/test_grafana_config.py`,
  `tests/integration/test_grafana_dashboard_query_governance.py`.
- Selector propagation contracts:
  `tests/integration/test_grafana_variable_reference.py`,
  `docs/03-guides/dashboards/variable-reference.md`.
- Export governance contracts:
  `src/bioetl/application/services/export_service.py`,
  `src/bioetl/application/services/export_manifests.py`,
  `docs/security/export-policy.md`.
