# Test System Architecture Audit Issue Pack — 2026-07-29

**Audit basis:** Architecture-strict test-system audit (fact inventory)
**Report:** `reports/grok/review_test_system_architecture_audit_20260729_FULL.md`
**Branch / SHA (audit):** `main` @ `73bc2ac3c6`
**Scope:** `tests/**`, `configs/quality/test_*`, fixtures, coverage inventory, scorecard
**Constraints:** No debt-budget growth; domain I/O-free; DI in composition only; keep determinism/idempotency/replay gates; no global xdist by default

## Snapshot

| Signal | Value |
| --- | --- |
| Test files (~) | 2115 (`unit` 65% / `architecture` 22% / `integration` 8% / `e2e` 1%) |
| Module coverage | 0 uncovered / 2310–2311 modules; 744 partial |
| Scorecard | integral 9.41; testability 9.9 |
| VCR mass | ~139 MB / 402 cassettes |
| Bronze fixtures | ~1.7 MB / 40 (ChEMBL 26) |
| Parallel policy | serial default; 13/15 shards `workers_override: 0` |
| Prior related | TEST-AUDIT-001..019; ARCH-CR2-05 (#7010) |

## Dedup posture vs prior TEST-AUDIT / ARCH-CR2

| Theme | Prior | This pack |
| --- | --- | --- |
| Closeout retirement | TEST-AUDIT-012/019 (#5500, #5931) | **TEST-SYS-03** continues with ~16% arch closeout residual + nightly split |
| Coverage tail | TEST-AUDIT-016 (#5928), TDX coverage | **TEST-SYS-07** focused on norm/hash/identity &lt;80% |
| Observability emission | TEST-AUDIT-017 (#5929) | **TEST-SYS-09** MetricsPort/TracingPort unit interaction |
| E2E PR/nightly split | TEST-AUDIT-018 (#5930) | Referenced; not reopened unless residual remains |
| Repo-backed vs unit | TEST-AUDIT-002 | **TEST-SYS-05** unit-parallel-safe + enforce exclusion |
| Test densification CP | ARCH-CR2-05 (#7010) | **TEST-SYS-02** continues residual nominal unit coverage |
| Non-ChEMBL fixtures | NONCHEMBL-*, CHEMBL-014 | **TEST-SYS-01** bronze exact-replay promotion (medallion) |
| VCR governance | fixture ledger / matrix | **TEST-SYS-06** size/age budget + recert workflow truth |
| S7 shard fan-out | shards config | **TEST-SYS-04** collapse redundant architecture shards |

## Issue codes — published

| Code | Pri | Issue | URL |
|------|-----|------:|-----|
| TEST-SYS-00 | meta | #7020 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7020 |
| TEST-SYS-01 | P0 | #7022 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7022 |
| TEST-SYS-02 | P0 | #7024 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7024 |
| TEST-SYS-03 | P1 | #7025 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7025 |
| TEST-SYS-04 | P1 | #7026 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7026 |
| TEST-SYS-05 | P1 | #7027 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7027 |
| TEST-SYS-06 | P1 | #7028 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7028 |
| TEST-SYS-07 | P1 | #7029 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7029 |
| TEST-SYS-08 | P2 | #7030 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7030 |
| TEST-SYS-09 | P2 | #7031 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7031 |
| TEST-SYS-10 | P2 | #7032 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7032 |

Publish record: `reports/quality/test-system-audit-2026-07-29-issue-publish.json`

## Acceptance (epic)

- [x] All child issues closed or explicitly rejected with code/evidence
- [x] Architecture closeout surface reduced (PR path lighter) without losing live invariants
- [x] Non-ChEMBL bronze exact-replay improved for claimed families
- [x] unit-parallel-safe expanded; pure unit lane hygiene enforced
- [x] No quality debt budget growth
- [x] Domain purity / determinism gates remain green

**Closeout:** `reports/quality/test-sys-2026-07-29-closeout.md` (2026-07-29)

## Source findings mapping

See audit §10–§14 in `reports/grok/review_test_system_architecture_audit_20260729_FULL.md`
and per-issue bodies under `.github/ISSUES/TEST-SYS-*.md`.

## Recommended execution order

1. **TEST-SYS-00** (epic tracking)
2. **TEST-SYS-01**, **TEST-SYS-02** (P0 correctness / replay)
3. **TEST-SYS-03**, **TEST-SYS-04**, **TEST-SYS-05** (CI velocity)
4. **TEST-SYS-06**, **TEST-SYS-07** (fixture cost + coverage quality)
5. **TEST-SYS-08**, **TEST-SYS-09**, **TEST-SYS-10** (P2 quality/hygiene)

## Publish

```bash
python scripts/engineering/repo/publish_test_sys_issues.py --apply --update-pack
```
