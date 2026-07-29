# Architecture CodeRabbit Residual Issue Pack 2 — 2026-07-29

**Audit basis:** CodeRabbit CLI 0.7.0 full residual architecture review  
**Report:** `reports/grok/review_coderabbit_architecture_audit_20260728_1520_FINAL.md`  
**JSON:** `reports/grok/review_coderabbit_architecture_audit_20260728_1520.json`  
**Base:** `f7ec4386fda4549fa44faa071ab6627e219ba6c1` → HEAD  
**Playbook:** `docs/03-guides/coderabbit-audit-playbook.md`  
**Findings:** 111 unique (53 major / 20 minor / 38 trivial)

## Snapshot

| Signal | Value |
| --- | --- |
| Completed CR scopes | 16 |
| Unique findings | 111 |
| Prior wave | ARCH-CR (#6862–#6870) — closed |
| Constraints | No debt-budget growth; domain I/O-free; DI in composition only |

## Dedup posture vs ARCH-CR-01..08

| Theme | Prior | This pack |
| --- | --- | --- |
| Async storage off event loop | ARCH-CR-01 | **ARCH-CR2-01** residual bronze paths still flagged |
| Composite registry stubs | ARCH-CR-02 | Tests densification only (ARCH-CR2-05) |
| Health-server cleanup | ARCH-CR-03 | **ARCH-CR2-03** quarantine order residual |
| Provenance / vacuum | ARCH-CR-04 | **ARCH-CR2-02** hydration strictness + lifecycle errors |
| Checkpoint / identity tests | ARCH-CR-05/06 | **ARCH-CR2-05** expanded test densification |
| Docs SSOT | ARCH-CR-07 / DOC-GOV | **ARCH-CR2-07** residual (RULES 6.1.6, ADR-052/053) |
| CodeRabbit CI secret | ARCH-CR-08 | Not reopened |

## Issue codes

## Issue codes — published

| Code | Pri | Issue | URL |
|------|-----|------:|-----|
| ARCH-CR2-00 | meta | #7005 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7005 |
| ARCH-CR2-01 | P0 | #7006 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7006 |
| ARCH-CR2-02 | P0 | #7007 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7007 |
| ARCH-CR2-03 | P0 | #7008 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7008 |
| ARCH-CR2-04 | P1 | #7009 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7009 |
| ARCH-CR2-05 | P1 | #7010 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7010 |
| ARCH-CR2-06 | P1 | #7011 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7011 |
| ARCH-CR2-07 | P2 | #7012 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7012 |
| ARCH-CR2-08 | P2 | #7013 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7013 |
| ARCH-CR2-09 | P2 | #7014 | https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7014 |

Publish record: `reports/quality/architecture-coderabbit-2026-07-29-issue-publish.json`


## Acceptance (epic)

- [ ] All child issues closed or explicitly rejected with code evidence
- [ ] Re-run CR on fixed scopes shows net-new majors only (or zero)
- [ ] No quality debt budget growth
- [ ] Layer violations remain 0

## Source findings mapping

See publish JSON `reports/quality/architecture-coderabbit-2026-07-29-issue-publish.json`
and per-issue bodies for file anchors from the 20260728_1520 audit.
