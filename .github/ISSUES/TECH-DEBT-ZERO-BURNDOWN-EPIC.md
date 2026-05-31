# Drive BioETL technical debt to zero

**Status**: in_progress
**Priority**: P0
**Labels**: `architecture`, `tech-debt`, `governance`, `epic`
**GitHub Issue**: [#4811](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4811)
**Issue State**: open
**Task ID**: `tech-debt-zero-001`
**Last synced**: 2026-05-31

## Текущие статусы issue (GitHub)

| Issue | State | Ключевой сигнал |
| --- | --- | --- |
| [#4812](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4812) | closed | `runtime_builders` duplicate baseline: `0` |
| [#4813](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4813) | closed | `application/core` duplicate baseline: `0` |
| [#4814](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4814) | closed | `composition/bootstrap/runtime` duplicate baseline: `0` |
| [#4815](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4815) | closed | `application/services/control_plane` duplicate baseline: `0` |
| [#4816](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4816) | closed | tracked twin families ratcheted to `3`; no-growth guard verified against live census |
| [#4817](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4817) | closed | `compatibility_test_file_max` closeout recorded on GitHub |
| [#4818](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4818) | closed | config-contract drift closeout recorded; release invariants green |
| [#4819](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4819) | closed | observability alias closeout: zero `alias_emitters` |
| [#4820](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4820) | closed | dead-code inventory governance closeout verified; zero untriaged repo-wide candidates |
| [#4821](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4821) | closed | migration-supported alias windows closed |
| [#4825](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4825) | closed | owner-trace dependency artifact closed on GitHub |
| [#4826](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4826) | closed | compatibility test-file debt ownership closeout recorded |
| [#4827](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4827) | closed | importer no-growth enforcement closed on GitHub |
| [#4828](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4828) | closed | config compatibility shape burn-down reached zero migration aliases |

## Current Baseline

1. Базовая архитектурная инвариантность на уровне слоёв подтверждена: `Layer policy violations = 0`.
2. P0 duplicate wave `#4812/#4813/#4814/#4815` закрыта на GitHub `2026-05-31`; targeted duplication baseline now reports `0` clusters across `application/core`, `composition/bootstrap/runtime`, `application/services/control_plane`, and `composition/runtime_builders`.
3. Compatibility surface остаётся санкционированным, но не закрытым: `14` retained entrypoints, `23` removed compatibility surfaces with `0` remaining first-party importers, `14` twin pairs, `3` tracked twin families.
4. Infrastructure config root facade сохраняет `0` first-party src importers for `Settings`, `get_settings`, and `load_pipeline_contract_policy`.
5. Contract governance improved: active contract coverage matrix reports `26/26` Gold-enabled entity surfaces covered.
6. Config drift по-прежнему остаётся residual governance topic: current discrepancy report shows `26` configs and `508` unique parameters.
7. Composite Gold strictness теперь требует explicit waiver metadata; GitHub issue `#4768` closed after policy closeout verification on `2026-05-31`.
8. Test-governance residual remains bounded, and the owner-tracked closeout wave for `compatibility_test_file_max` is already closed on GitHub.

## Остаточная очередь внутри epic

Остаточная очередь после closeout wave:

1. epic `#4811` final closure after the remaining open technical-debt queue is exhausted

## Evidence Anchors

- `reports/quality/hotspot-duplication-baseline.md`
- `reports/quality/compatibility-importer-census.md`
- `reports/quality/contract-coverage-matrix.md`
- `reports/quality/dead-code-inventory.md`
- `docs/config-discrepancies-report.md`
- `configs/quality/compatibility_twin_module_ratchet.yaml`
- `configs/quality/test_governance_audit.yaml`
- `configs/quality/composite_gold_strictness_waivers.yaml`
- `tests/architecture/test_hotspot_duplication_family_ratchets.py`
- `tests/architecture/test_compatibility_importer_census_governance.py`
- `tests/architecture/test_contract_coverage_matrix_drift.py`
- `tests/architecture/test_gold_strict_validation_policy.py`

## Closeout Rule

Epic [#4811](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4811)
закрывается только когда:

- remaining open technical-debt queue outside the already closed Stream A
  sub-issues is exhausted;
- no-growth governance stays green for twin families and sanctioned facades;
- duplicate baseline remains at `0` for the closed P0 wave;
- no new non-sanctioned technical debt is introduced into the tracked surfaces.
