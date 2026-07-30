# Grafana Provenance readability issue pack

Runtime evidence:

- `reports/observability/grafana/gra-prov-closeout/CLOSEOUT.md`
- fresh Playwright 1366×768 Dark terminal-state renders:
  `reports/observability/grafana/gra-prov-closeout/smoke-*/`
- fresh Grafana Render API matrix:
  `reports/observability/grafana/gra-prov-closeout/server-matrix/`

| ID | Scope | Priority | Status | GitHub issue |
| --- | --- | --- | --- | --- |
| GRA-PROV-00 | Shared visual and render contract | High | Closed | [#7226](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7226) |
| GRA-PROV-01 | 0. Trust | Medium | Closed | [#7227](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7227) |
| GRA-PROV-02 | 1. Overview clipping | High | Closed | [#7228](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7228) |
| GRA-PROV-03 | 2. Pipeline Diagnostics | Medium | Closed | [#7229](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7229) |
| GRA-PROV-04 | 3. Provider Health | Medium | Closed | [#7230](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7230) |
| GRA-PROV-05 | 4. Data Quality reference | Medium | Closed | [#7231](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7231) |
| GRA-PROV-06 | 5. Incident Workspace | Medium | Closed | [#7232](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7232) |
| GRA-PROV-07 | 6. Run Explorer scope/provenance | Medium | Closed | [#7233](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7233) |

Dependency order:

1. GRA-PROV-00 defines the contract.
2. GRA-PROV-05 updates the canonical Data Quality reference.
3. GRA-PROV-01/02/03/04/06/07 adopt the reference.
4. The post-change runtime render matrix closes the pack.
