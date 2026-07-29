# Grafana Provenance readability issue pack

Runtime evidence:

- `reports/observability/grafana/gra-rt-closeout/matrix/matrix-manifest.json`
- fresh 1366×768 dark renders:
  `reports/observability/grafana/provenance-readability-audit-20260729/matrix/1366x768-dark/`

| ID | Scope | Priority | GitHub issue |
| --- | --- | --- | --- |
| GRA-PROV-00 | Shared visual and render contract | High | [#7226](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7226) |
| GRA-PROV-01 | 0. Trust | Medium | [#7227](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7227) |
| GRA-PROV-02 | 1. Overview clipping | High | [#7228](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7228) |
| GRA-PROV-03 | 2. Pipeline Diagnostics | Medium | [#7229](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7229) |
| GRA-PROV-04 | 3. Provider Health | Medium | [#7230](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7230) |
| GRA-PROV-05 | 4. Data Quality reference | Medium | [#7231](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7231) |
| GRA-PROV-06 | 5. Incident Workspace | Medium | [#7232](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7232) |
| GRA-PROV-07 | 6. Run Explorer scope/provenance | Medium | [#7233](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7233) |

Dependency order:

1. GRA-PROV-00 defines the contract.
2. GRA-PROV-05 updates the canonical Data Quality reference.
3. GRA-PROV-01/02/03/04/06/07 adopt the reference.
4. The complete render matrix closes the pack.
