# CodeRabbit Full Residual — FINDINGS Pack 2026-08 (post #7696)

**Published:** 2026-08-06
**Epic:** [#7688](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7688)
**Task:** [#7696](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7696)
**Artifacts:** `reports/quality/coderabbit/20260806/`

## Severity summary (agent NDJSON raw)

| Severity | Count |
| --- | ---: |
| critical | 22 |
| major | 736 |
| minor | 253 |
| trivial | 457 |
| **total** | **1468** |

## Path-cluster issue inventory

| Metric | Count |
| --- | ---: |
| Open residual clusters before de-dupe | 268 |
| Canonical kept | 220 |
| Duplicates identified | 48 |
| Duplicates closed this run | 0 |
| Canonical critical (P0) | 12 |
| Canonical major (P1) | 208 |
| Canonical minor (P2) | 0 |
| Canonical trivial | 0 |

## Campaign parent issues

| Code | Issue | Status note |
| --- | ---: | --- |
| meta | #7688 | open |
| CR-FULL-00 | #7689 | preflight done |
| Wave A–D | #7690–#7693 | closed after residual CLI |
| Wave E/F | #7694–#7695 | open blocked #8031/#8032 |
| FINDINGS | #7696 | this pack |
| Closeout | #7697 | after implement |
| Secret | #7698 | owner |

## Canonical P0 critical issues

- [#7738](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7738) — `src/bioetl/composition/bootstrap/runtime` (34 findings, Wave A)
- [#7750](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7750) — `src/bioetl/application/services/control_plane` (73 findings, Wave A)
- [#7770](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7770) — `src/bioetl/application/core/base_transformer` (4 findings, Wave A)
- [#7779](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7779) — `src/bioetl/application/core/batch_checkpoint_recovery_service.py` (3 findings, Wave A)
- [#7793](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7793) — `src/bioetl/interfaces/http/health_server_http_mixin.py` (2 findings, Wave A)
- [#7809](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7809) — `src/bioetl/infrastructure/adapters/http` (2 findings, Wave A)
- [#7821](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7821) — `src/bioetl/infrastructure/adapters/crossref` (10 findings, Wave A)
- [#7840](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7840) — `src/bioetl/application/core/batch_transformer_streaming.py` (1 findings, Wave A)
- [#7887](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7887) — `src/bioetl/interfaces/http/run_report_ops.py` (2 findings, Wave A)
- [#7972](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7972) — `src/bioetl/application/pipelines/crossref` (9 findings, Wave B)
- [#7993](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7993) — `src/bioetl/infrastructure/storage/metadata` (3 findings, Wave B)
- [#8030](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/8030) — `tests/security` (5 findings, Wave D)

## De-dupe policy

1. One open issue per residual path (normalized).
2. Prefer Wave A over Wave B when same path (fixes mid-campaign filter mis-tag).
3. Prefer lower issue number / higher severity when still tied.
4. Implement only against canonical issue; closed dupes link back.
5. Do **not** grow tech-debt / quality budgets.

## Related artifacts

- `reports/quality/coderabbit/20260806/FINDINGS.md`
- `reports/quality/coderabbit/20260806/TRIAGE.md`
- `reports/quality/coderabbit/20260806/DE_DUPE_MAP.json`
- Wave raw: `reports/quality/coderabbit/20260805/` (or local `/tmp/bioetl-cr-artifacts/20260805/`)

## Errors during close

- none

