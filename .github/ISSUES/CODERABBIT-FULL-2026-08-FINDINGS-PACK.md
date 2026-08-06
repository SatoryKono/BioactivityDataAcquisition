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

## Path-cluster inventory (after de-dupe)

| Metric | Count |
| --- | ---: |
| Canonical open residual issues | 220 |
| Duplicates closed | 48 |
| P0 critical | 12 |
| P1 major | 208 |
| P2 minor | 0 |
| trivial open | 0 |

## Canonical P0 critical

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

1. One open issue per residual path.
2. Prefer Wave A over later waves for same path.
3. Prefer higher severity, then lower issue number.
4. Implement only canonical issues.
5. No tech-debt budget growth.

## Files

- `reports/quality/coderabbit/20260806/FINDINGS.md`
- `reports/quality/coderabbit/20260806/TRIAGE.md`
- `reports/quality/coderabbit/20260806/DE_DUPE_MAP.json`

## Campaign parents

| Issue | Note |
| ---: | --- |
| #7688 | epic open |
| #7690–#7693 | Wave A–D closed after residual CLI |
| #7694–#7695 | E/F blocked #8031/#8032 |
| #7696 | this pack (complete) |
| #7697 | FINAL after implement |
| #7698 | CI secret owner |
| #7946 | domain rate-limit retry |

