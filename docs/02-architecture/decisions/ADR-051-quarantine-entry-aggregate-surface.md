______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Last verified: '2026-07-27'

______________________________________________________________________

# ADR-051: QuarantineEntry wide constructor as intentional aggregate surface

**Date:** 2026-07-27
**Status:** Accepted
**Linked issue:** #6685 (TD-R-09)
**Note:** Numbered ADR-051 because ADR-050 is already assigned to the
Silver structural / Gold semantic filter boundary decision.

## Context

`QuarantineEntry` is a Domain aggregate root that freezes identity and
immutability invariants for quarantine records. Its constructor currently
takes 9 arguments and is listed in `configs/quality/constructor_waivers.yaml`
with `max_args: 9`.

## Decision

Treat the 9-argument constructor as an **intentional_exception**, not a
generic tech-debt waiver to burn to zero via anemic extraction:

1. Fields form one explicit identity/snapshot surface (entry_id, pipeline,
   error_code, payload, hashes, run/batch ids, created_at, metadata).
2. Domain purity is preserved (no I/O, defensive copies, immutable hash).
3. `max_args` is **frozen** (no growth). Further fields require a new ADR.
4. Decomposition into VOs is optional and may proceed only if it preserves
   aggregate invariants without pushing policy into infrastructure.

## Consequences

- Waiver remains until optional decomposition lands.
- Classification `intentional_exception` + this ADR link is the permanent
  governance record for residual constructor budget on this type.
- Related residual constructor burn-down (#6679) excludes this type from
  the path-to-zero count unless a future decomposition removes the waiver.

## Alternatives considered

- Force VO extraction immediately: rejected as risk of anemic domain.
- Raise max_args: **forbidden** (shrink-only policy).
