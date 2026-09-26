# Drive BioETL technical debt to zero

**Status**: local_mirror
**Priority**: P0
**Labels**: `architecture`, `tech-debt`, `governance`, `epic`
**GitHub Issue**: [#4811](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4811)
**Issue State**: closed
**Task ID**: `tech-debt-zero-001`
**Last synced**: 2026-06-01
**Authoritative status source**: live GitHub issue state plus governed quality artifacts
**Source command**: `curl -H "Authorization: Bearer ${GITHUB_TOKEN}" https://api.github.com/repos/SatoryKono/BioactivityDataAcquisition/issues/{4861..4872}`
**Stale-warning policy**: this file is a local mirror only. If GitHub state or governed debt budgets change, treat this file as stale until it is resynchronized. Do not use it as the sole execution authority.

## Mirror Contract

1. Epic closeout is blocked by the remaining live technical-debt queue on GitHub, not by this file alone.
2. Quality artifacts remain authoritative for evidence:
   - `reports/quality/hotspot-duplication-baseline.md`
   - `reports/quality/compatibility-importer-census.md`
   - `reports/quality/contract-coverage-matrix.md`
   - `reports/quality/dead-code-inventory.md`
   - `reports/observability/runtime_cardinality_inventory.json`
   - `configs/quality/test_governance_audit.yaml`
3. Closed Stream A/B sub-issues stay here only as historical closeout evidence.

## Resynced Baseline

1. P0 duplicate wave `#4812/#4813/#4814/#4815` is closed. The follow-up live owner for residual control-plane duplicates is `#4862`; the current regenerated duplicate baseline is `0` for all tracked families including `application/services/control_plane`.
2. Tracked twin families remain `3`; no-growth compatibility census is the active ratchet.
3. Contract coverage matrix remains `26/26` Gold-enabled surfaces covered.
4. `compatibility_test_file_max` is `53` in `configs/quality/test_governance_audit.yaml`; older local mirror values such as `56` are stale and must not return.
5. Runtime cardinality governance now has an explicit CI review artifact/status path via `reports/observability/runtime_cardinality_review.json` in `quality-metrics-gate`.
6. Deterministic identity policy now distinguishes semantic replay anchors from allowed operational correlation artifacts in `configs/quality/determinism_identity_policy.yaml`.
7. Config discrepancy governance now publishes `0` actionable drift and `106` sanctioned partial variance parameters via `docs/config-discrepancies-report.md` and `reports/quality/config-discrepancy-baseline.json`.
8. Specialized duplication artifacts `control-plane-duplication.*` and `runtime-builders-duplication.*` are synchronized with the canonical hotspot baseline and drift-guarded by `tests/architecture/test_duplication_report_governance.py`.
9. Live GitHub technical-debt queue check on 2026-06-01 returned the active closeout wave `#4861` through `#4872`; `#4610` and `#4811` remain closed and must not be used as active owners.

## Closed Stream A Sub-Issues

| Issue | State | Evidence anchor |
| --- | --- | --- |
| [#4812](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4812) | closed | `runtime_builders` duplicate baseline `0` |
| [#4813](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4813) | closed | `application/core` duplicate baseline `0` |
| [#4814](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4814) | closed | `composition/bootstrap/runtime` duplicate baseline `0` |
| [#4815](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4815) | closed | helper-duplicate wave closed; follow-up residual owner is `#4862`, and regenerated hotspot evidence is `0` |
| [#4816](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4816) | closed | tracked twin-family ratchet pinned at `3` |
| [#4817](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4817) | closed | test-governance closeout recorded on GitHub |
| [#4818](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4818) | closed | config-contract drift closeout recorded |
| [#4819](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4819) | closed | observability alias closeout recorded |
| [#4820](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4820) | closed | dead-code inventory governance closeout recorded |
| [#4821](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4821) | closed | migration alias window closeout recorded |
| [#4825](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4825) | closed | owner-trace dependency artifact closed |
| [#4826](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4826) | closed | compatibility test-file ownership closed |
| [#4827](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4827) | closed | importer no-growth enforcement closed |
| [#4828](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4828) | closed | config compatibility alias burn-down reached zero |

## Active Closeout Queue

Live GitHub state on 2026-06-01 reintroduced the following technical-debt owners after the `#4610/#4811` closeout. GitHub remains authoritative until each issue is closed with evidence:

| Issue | Owner surface | Required evidence |
| --- | --- | --- |
| [#4861](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4861) | governance mirrors | this mirror and the v4 blueprint match live GitHub state |
| [#4862](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4862) | control-plane duplication | duplicate baseline `0` plus touched control-plane tests |
| [#4863](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4863) | control-plane shims | dead-code inventory and importer census proof |
| [#4864](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4864) | compatibility facades/twins | census no-growth and measured-only ratchet proof |
| [#4865](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4865) | config partial variance | config matrix/check with sanctioned variance reduced to `106` |
| [#4866](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4866) | composite Gold strictness | strict composite contracts and empty waiver registry |
| [#4867](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4867) | security env-prefix policy | env-prefix test passes without xfail |
| [#4868](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4868) | test-governance budgets | at least one live budget ratcheted downward |
| [#4869](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4869) | replay identity guards | semantic anchors forbid occurrence fields |
| [#4870](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4870) | observability release gate | degraded live review fails in release mode |
| [#4871](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4871) | zero-import inventory | candidate count reduced and triage regenerated |
| [#4872](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4872) | git-lfs/VCR preflight | missing LFS and dirty VCR states fail-fast |

If GitHub later shows additional open technical-debt issues, GitHub wins and this mirror must be resynced again before execution continues.
