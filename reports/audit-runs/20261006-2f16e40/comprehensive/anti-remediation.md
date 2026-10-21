# Anti-remediation register — CF-056 removal

Historical path cited by #12059 (2026-10-07): this file.
The comprehensive register was gitignored by `/reports/*` and is absent from
git history, so entries 1–18 are not reconstructed here.

## Removed

- **#19 (CF-056).** Rule-level DQ outcome channel wiring is in place:
  record attribution, executable contract rules on the bound `DQConfig`,
  Gold `write_gold` consumption of `validate_with_outcomes()`, per-record
  quarantine routing, and deterministic outcome ordering.
  Removed in the #12095 implementation PR. Silver production writes remain
  on fail-closed `validate()`; that path was outside the Gold write-path
  acceptance scope.
