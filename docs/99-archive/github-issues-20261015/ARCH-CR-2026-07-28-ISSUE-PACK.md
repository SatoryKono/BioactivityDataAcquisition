# Architecture CodeRabbit Residual Issue Pack — 2026-07-28

**Audit basis:** CodeRabbit CLI 0.7.0 exhaustive architecture review (post ARCH-REF).
**Report:** `reports/grok/review_coderabbit_architecture_audit_20260728_1203_FINAL.md`
**Base range:** `f7ec4386fd~1` → main (ARCH-RES / ARCH-CONT / ARCH-REF program)
**Findings:** 41 unique (22 major / 8 minor / 11 trivial); no security/critical class

## Snapshot (evidence at pack time)

| Metric | Value | Source |
|---|---|---|
| Scorecard integral | **9.41** | `architecture-quality-scorecard.json` |
| Debt gates | **45/45 pass** | `debt-governance-gates.json` |
| Layer violations | **0** | scorecard / dep-map |
| Services root | **82/82** | `application_services_root_ratchet.yaml` |
| control_plane fan-in | **3/3 at_budget** | hotspot baseline |
| Partial modules | **744** | `module-coverage-inventory.json` |
| CR scopes completed | application, composition, infrastructure, interfaces | CR agent JSONL |
| CR scopes rate-limited | configs/quality, tests/architecture, docs/** | CR agent JSONL |

## Issue codes

## Issue codes — published

| Code | Pri | Issue | URL |
|------|-----|------:|-----|
| ARCH-CR-00 | meta | #6862 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6862 |
| ARCH-CR-01 | P0 | #6863 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6863 |
| ARCH-CR-02 | P0 | #6864 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6864 |
| ARCH-CR-03 | P0 | #6865 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6865 |
| ARCH-CR-04 | P0 | #6866 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6866 |
| ARCH-CR-05 | P1 | #6867 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6867 |
| ARCH-CR-06 | P1 | #6868 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6868 |
| ARCH-CR-07 | P2 | #6869 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6869 |
| ARCH-CR-08 | P3 | #6870 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6870 |

Publish record: `reports/quality/architecture-coderabbit-2026-07-28-issue-publish.json`


| Code | Pri | Title theme |
|------|-----|-------------|
| ARCH-CR-00 | meta | Epic: CodeRabbit residual architecture remediation |
| ARCH-CR-01 | P0 | Async storage I/O off event loop |
| ARCH-CR-02 | P0 | Composite registry stub trust boundary |
| ARCH-CR-03 | P0 | Health-server lifecycle cleanup correctness |
| ARCH-CR-04 | P0 | Control-plane provenance + medallion vacuum correctness |
| ARCH-CR-05 | P1 | Identity / lazy facade / checkpoint test densification |
| ARCH-CR-06 | P1 | PipelineObserverIdentity migration/compat posture |
| ARCH-CR-07 | P2 | Docs SSOT residual (RULES version + DQ skip vs quarantine) |
| ARCH-CR-08 | P3 | Enable CodeRabbit CI secret + optional coalesce vectorization |

## Constraints

1. **No technical-debt budget growth.**
2. Domain I/O-free; DI only in `composition/`.
3. Prefer extract helpers / bags over layer exceptions.
4. Do not reopen closed ARCH-QA / ARCH-RES / ARCH-CONT / ARCH-REF issues; this is a **new residual wave**.
5. Layer violations must remain **0**.
6. control_plane fan-in budget stays ≤3; services root ≤82.

## Prior closed waves

- ARCH-QA (#6740–#6748)
- ARCH-RES (#6749–#6755)
- ARCH-CONT (#6757–#6764)
- ARCH-REF (#6817–#6825)
