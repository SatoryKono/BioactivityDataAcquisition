# Root Hygiene Audit Issue Pack 2026-04-29

*Status: Working planning artifact (non-normative)*
*Created: 2026-04-29*
*Scope: proposed GitHub issue breakdown from the 2026-04-29 root-structure audit*

## Purpose

This file converts the 2026-04-29 repository structure audit into a bounded,
issue-ready GitHub backlog.

It intentionally does **not** reopen the already closed remediation set cited
in [repository-file-structure-remediation-plan-2026-04-28.md](./repository-file-structure-remediation-plan-2026-04-28.md):

- `#3219` `RH-001 finalize remediation plan and baseline root evidence`
- `#3223` `RH-005 finish AI tooling root surface migration`
- `#3226` `RH-008 define bounded cleanup procedure for protected surfaces`
- `#3227` `RH-009 harden root hygiene enforcement and branch protection`

The audit conclusion was not "clean the repo broadly". The live machine-checked
baseline already passes. The remaining work is process hardening around
retention-sensitive cleanup, evidence export, regression prevention, and live
admin verification.

Primary supporting documents:

- [root-hygiene-cleanup-hardening-2026-04-29.md](./root-hygiene-cleanup-hardening-2026-04-29.md)
- [root-hygiene-review-lane-automation-2026-04-29.md](./root-hygiene-review-lane-automation-2026-04-29.md)
- [repository-file-structure-remediation-plan-2026-04-28.md](./repository-file-structure-remediation-plan-2026-04-28.md)
- [retention-sensitive-cleanup.md](../05-operations/runbooks/retention-sensitive-cleanup.md)

## Suggested dependency order

1. Add issue/PR template support for retention-sensitive cleanup proposals
1. Export deterministic cleanup classification evidence from tooling and CI
1. Prevent broad cleanup guidance from re-entering docs and scripts
1. Verify and record live branch protection state for `root-hygiene`

## Issue 1

### Title

`RH-010 Add a retention-sensitive cleanup proposal template for blocked surfaces`

### Suggested labels

- `enhancement`
- `documentation`
- `infrastructure`

### Suggested scope

`Infrastructure / DevOps`

### Problem

The published retention-sensitive cleanup runbook already requires every
cleanup PR or issue to include:

- candidate inventory
- classification table
- dry-run evidence
- reviewed apply/delete list
- verification output
- rollback or restore note

However, the repository does not yet expose that requirement as a dedicated
GitHub issue or PR template. The result is process drift risk: operators may
remember the runbook incompletely and open blocked-zone cleanup requests
without the mandatory evidence pack.

### Proposed solution

Add a dedicated GitHub issue template, or equivalent canonical staging
artifact, for cleanup proposals that touch blocked or retention-sensitive
surfaces such as:

- `data/**`
- `data/output/control/**`
- `data/output/checkpoints/**`
- `tests/fixtures/**`
- `tests/fixtures/vcr/**`
- `reports/**`
- `docs/reports/**`
- `docs/99-archive/**`

The template should encode the exact evidence fields required by the runbook.

### Scope

- add a GitHub issue template for retention-sensitive cleanup proposals
- mirror the runbook-required evidence fields in the template
- link the template from cleanup docs and root-hygiene governance docs
- explicitly distinguish `SAFE`, `REVIEW_REQUIRED`, and `BLOCKED` paths
- require the proposer to declare restore/rollback path

### Non-goals

- do not add auto-delete behavior for blocked zones
- do not allow broad deletion commands through the template
- do not replace the existing runbook with GitHub UI text

### Acceptance criteria

- a dedicated cleanup-proposal template exists
- the template requires candidate inventory, classification, dry-run evidence,
  reviewed apply list, verification output, and rollback note
- the template links to the retention-sensitive cleanup runbook
- blocked-zone cleanup requests opened without the template become
  procedurally non-compliant

## Issue 2

### Title

`RH-011 Export deterministic root-hygiene cleanup classification artifacts from tooling and CI`

### Suggested labels

- `enhancement`
- `infrastructure`

### Suggested scope

`Infrastructure / DevOps`

### Problem

`cleanup_repository.py --dry-run` and the review-lane registry now compute
useful bounded evidence, but the resulting classification is still mainly
operator-visible console output. That makes later review and comparison harder
than necessary and increases the chance of "I saw a clean output locally" style
claims without attached evidence.

### Proposed solution

Add a machine-readable export path for cleanup classification, and publish it
from CI as an artifact. The exported report should distinguish:

- `SAFE`
- `REVIEW_REQUIRED`
- `BLOCKED`

and should include the relevant review evidence fields where applicable.

### Scope

- add `--report-json` or equivalent export support to cleanup tooling
- include candidate classification in the report
- include review-lane evidence fields already synthesized by the tool
- wire the report into root-hygiene CI artifact publication
- document how operators attach the report to cleanup issues or PRs

### Non-goals

- do not add destructive behavior to the export path
- do not turn blocked-zone cleanup into an automated workflow
- do not duplicate the full repository inventory when only cleanup evidence is
  needed

### Acceptance criteria

- cleanup tooling can emit a machine-readable classification report
- CI publishes the report as an artifact in the root-hygiene lane
- the report distinguishes `SAFE`, `REVIEW_REQUIRED`, and `BLOCKED`
- a retention-sensitive cleanup issue or PR can link to one canonical evidence
  artifact rather than ad hoc terminal output

## Issue 3

### Title

`RH-012 Add governance checks that block broad cleanup instructions from docs and scripts`

### Suggested labels

- `enhancement`
- `documentation`
- `infrastructure`

### Suggested scope

`Documentation`

### Problem

The published cleanup policy forbids broad deletion patterns such as
repo-wide `git clean -fdx` and blanket `rm -rf` against protected roots.
That rule is documented, but it is not yet hardened as a dedicated regression
guard for repository prose and support scripts.

Without an explicit check, broad cleanup instructions can be reintroduced into
docs, copied into helper scripts, or proposed in onboarding material in ways
that directly contradict the repository's fail-closed retention model.

### Proposed solution

Add a narrow governance check that scans maintained docs and scripts for
disallowed broad cleanup commands, with a small allowlist for clearly marked
"disallowed example" sections inside normative runbooks.

### Scope

- define the forbidden instruction set
- add a maintained allowlist for legitimate quoted examples
- scan docs, scripts, and repo-root helper surfaces
- fail CI when a forbidden broad cleanup instruction appears outside an
  allowlisted context
- document how to quote a forbidden command safely in explanatory docs

### Non-goals

- do not ban every use of `rm -rf` universally
- do not block exact path-scoped cleanup examples already approved by policy
- do not rewrite historical archive material unless it is part of the active
  published surface

### Acceptance criteria

- a dedicated check fails when broad cleanup instructions are introduced into
  active docs or scripts
- policy-approved exact cleanup examples remain allowed
- quoted "disallowed pattern" examples can exist only in explicit allowlisted
  contexts
- root-hygiene guidance becomes machine-enforced rather than prose-only

## Issue 4

### Title

`RH-013 Verify and record live branch protection state for the root-hygiene required check`

### Suggested labels

- `enhancement`
- `infrastructure`
- `documentation`

### Suggested scope

`Infrastructure / DevOps`

### Problem

The repository already documents that `root-hygiene` must be a required check
for `main`, but the remediation plan also explicitly notes that the live admin
state was not fully provable from the available unauthenticated API snapshot.

That leaves one operational gap: the policy-as-docs claim exists, but the
owner/admin-confirmed GitHub configuration evidence is not yet recorded as a
fresh, auditable artifact.

### Proposed solution

Perform an owner/admin verification of branch protection for `main`, ensure
`root-hygiene` is required in the live GitHub configuration, and record the
verification date and evidence path in the canonical GitHub policy docs.

### Scope

- verify the current branch protection state with owner/admin access
- ensure `root-hygiene` is required on `main`
- record the verification date and evidence source
- update GitHub policy docs or related governance docs with the confirmed
  status
- define how often this verification must be repeated

### Non-goals

- do not widen branch protection requirements beyond the scoped check unless a
  separate governance decision is made
- do not rely on anonymous public API calls as the only proof source
- do not create a competing policy source outside the published governance docs

### Acceptance criteria

- owner/admin confirms the live `main` branch protection state
- `root-hygiene` is present as a required check in the live configuration
- the verification date is recorded in the canonical docs
- the repository no longer relies on stale or unverifiable branch-protection
  assumptions for this policy
