______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-11-27'

______________________________________________________________________

# Recovering from an Actions billing lock

## Trigger

A burst of failed runs completing in seconds with zero job steps can indicate
that GitHub never provisioned runners. Inspect the affected check-run annotations:
`account locked due to a billing issue` confirms the billing-lock signature.
A zero-step failure alone is not proof of a billing problem. The nightly Actions
health job reports affected run IDs; it cannot run or send an alert if GitHub
blocks that job too. Monitor failed or missing nightly runs independently.

## Impact

Jobs may never start and CodeQL analyses may be missing for affected commits.

## Preconditions

Use an account with Actions and code-scanning read access; billing remediation
requires an account or organization billing administrator.

## Procedure

1. Pause merges and record the affected run IDs and the time window. Inspect the
   failed jobs and check-run annotations in GitHub; distinguish billing locks
   from other provisioning failures.
2. An account or organization billing administrator should inspect GitHub
   billing, payment status and Actions spending limits, resolve the issue, and
   confirm that a new Actions job actually starts. Escalate to GitHub Support if
   the account remains locked.
3. After unlocking, manually dispatch the CodeQL workflow on the affected
   branch or commit using `gh workflow run codeql.yml --ref <ref>`. Rerun or
   dispatch each needed revision according to the incident recovery scope.
   A successful dispatch alone does not establish that analyses were uploaded.
## Rollback/Recovery

If a dispatched run fails, keep merges paused and investigate its job logs
and annotations before retrying. Escalate unresolved billing locks to GitHub.

## Verification

Check completion of the runs and query
`gh api --paginate 'repos/{owner}/{repo}/code-scanning/analyses?per_page=100'`.
Compare analysis commit SHAs, refs, tool and timestamps against the missed
revisions, and investigate any missing uploads. The API and workflow require
suitable code-scanning permissions.

## Post-incident

Record evidence and resume merges only after the incident owner accepts recovery.

For retrospective inspection run
`python scripts/engineering/ops/check_actions_health.py --since 2026-10-03 --until 2026-10-05`.
Dates are UTC; the end is exclusive. Authenticate `gh` with repository Actions
read access. The check reports all failed zero-step jobs, not just billing locks.

## Compliance

Use the normal GitHub access controls; do not put tokens in reports or logs.
