## Parent

_TBD_ (DSA-00)

## Problem

Audit proposes shadow portfolio + cutover + legacy retirement. Repo policy (ADR-053, DS2): **7 UIDs remain** until parity + usage evidence; Trust+DQ physical merge is Wave 5 only; Scenes is optional presentation adapter.

This issue tracks **measured cutover**, not an immediate delete plan.

## Tracking checklist

- [ ] Dual-path: JSON provisioned + optional Scenes routes (ADR-053)
- [ ] Parity tests: counts/status/reasons/links for same scope/time
- [ ] Usage evidence before any UID retirement
- [ ] Redirects ≥1 release if route renames
- [ ] Query-usage audit before deleting recording rules
- [ ] Incident write-path only after separate ADR + backend
- [ ] No MTT* as cutover KPI

## Supersedes / related

- #6914 DS2-13 (closed not_planned)
- #6924 DSS-09 (closed not_planned)

## Acceptance (to start cutover PR)

- [ ] A0–A2 residual green or explicitly waived
- [ ] Parity evidence attached
- [ ] Rollback plan documented

## Priority

P3 tracking — no unsolicited UID deletion.
