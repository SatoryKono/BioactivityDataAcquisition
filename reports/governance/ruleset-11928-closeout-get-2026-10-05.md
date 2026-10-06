# CircleCI ruleset activation readback — #11928

Captured on 2026-10-05 by read-only GitHub REST GET after activation.
Repository: SatoryKono/BioactivityDataAcquisition; branch: main.

| Ruleset | Enforcement | Required commit status contexts |
| --- | --- | --- |
| main (13643213) | active | ci/circleci: pr-gate-complete |
| root-hygiene-required-check (15730586) | active | ci/circleci: pr-gate-complete; ci/circleci: root-hygiene |

Both target only refs/heads/main, require strict freshness and have no bypass actors.
Deletion, non-fast-forward and pull-request protections are preserved.
CircleCI publishes legacy commit statuses; no GitHub App binding is available.

Main acceptance: pipelines 218, 219, 220, all 81 jobs successful on
`a34558b918b56984a185c0e4956d735b43483780`. Full job IDs and applied rule
objects are in the adjacent JSON readback.

Negative acceptance: isolated PR #11954 rejected missing, failed, stale-SHA
and canceled-CircleCI evidence with HTTP 405. Positive control was clean but
never merged. The test PR was closed and test ruleset 24517966 disabled.
Production settings were not used for destructive negative testing.

The older 2026-09-10 artifact is historical evidence for #10267 and is preserved.
This receipt does not attest Docker publication or completion of phase 3.
