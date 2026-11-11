______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-11-11'

______________________________________________________________________

# Full-tree guard deployment and evidence

## Trigger

Use before installing Git hooks, changing checkout/index strategy, or merging
changes to the full-tree checker and its workflow.

## Impact

A partial snapshot can enter history even when the final tip looks healthy.
Local sparse state and committed content require separate checks.

## Preconditions

Use a complete checkout, Python 3.10 or later, Git with sparse-index inspection,
and a locally available trusted base. Missing Git, missing objects, a shallow
boundary inside the candidate range, ambiguous ancestry, errors and timeouts
do not qualify as PASS. History older than the trusted base need not be
downloaded again when the complete selected range is already available.
Do not create another project checkout to diagnose a failure outside the
approved workspace. Preserve existing history and environment files.

## Procedure

Run the existing history command from the complete working tree:

```text
python -B scripts/engineering/repo/check_no_partial_tree.py --base origin/main --tip HEAD
```

Add `--check-index` for the proposed commit. This reads the index without
write-tree, refresh, staging, or rewriting objects. Sparse checkout settings,
sparse-directory index entries and skip-worktree entries are inspected
independently. An index replacement during inspection is a refusal, including
when another agent performs it. No lock is retained across Git's eventual
commit; malicious races after validation require a stronger host boundary.

Every commit in base..tip is inspected, including intermediate commits and
merge ancestry. The directory-anchor comparison uses the verified common
ancestor; a missing or ambiguous ancestor is an error. Mandatory anchors are
src, tests, scripts, configs, docs, .github and the three canonical runtime
trees when present in the trusted base. Adding a dummy root does not excuse
omitting their contents. Git rename evidence can account for relocation;
one destination cannot cover several omitted files with identical contents.
Optional root-file/directory removal remains governed by the owning project
contracts rather than being treated automatically as a partial checkout.
Extensive edits may make rename evidence ambiguous. Treat that as requiring
migration review; do not infer completeness or add an automatic bypass.

This is a content/provenance guard, not a proof of arbitrary individual file
completeness or intent. A missing file inside a retained directory still needs
root hygiene, required-artifact checks, architecture tests and independent CI.
A local Git hook remains bypassable. No static comparison can distinguish all
intentional deletions from an identical tree produced by a partial index.

## CI event and trust boundary

The workflow uses pull_request_target with read-only repository access and a
job-scoped status-write permission. It checks out the protected main checker,
fetches candidate objects without checking them out, and executes no candidate
Python, actions, dependencies or hooks. The checkout ref is the literal
refs/heads/main, so a PR field cannot choose executable code. Git metadata queries disable fsmonitor
and external diff/textconv execution. No agent or service is started.
PR events are restricted to the protected main target. Push and manual runs
load their checker from main, including when manual dispatch is requested from
another ref; they never import the dispatcher ref's candidate Python module.

PR base/head come from the PR event, never the synthetic merge SHA. Push uses
before/after. A zero or missing base is an error; a new branch requires an
explicit trusted base through manual dispatch. Manual dispatch requires base
and tip inputs and never borrows fields from another event type. The CLI
supports the same selection through --event-name and --event-json with a
bounded event read. Unknown event shapes fail closed without dumping payloads.
CLI event files must resolve inside the invocation directory, including after
symlink resolution. The workflow reads GitHub's host-provided event path separately
and passes bounded bytes to the same parser; it does not widen the CLI boundary.

Because pull_request_target jobs attach to the base SHA, the workflow publishes
bioetl/no-partial-tree on the validated candidate SHA. Only a successful guard
job publishes success; errors publish failure when the candidate identity is
known. A missing status is not success. Fetch has a 90-second deadline; Git
queries have ten-second deadlines; the workflow has a ten-minute deadline.
Missing Python/gh, cancellation or publication failure cannot produce a new
successful status. Superseded PR runs are cancelled by stable PR identity.

## Verification

Run the isolated fixture tests for check_no_partial_tree, including a partial
snapshot with more than three roots, restoration after an intermediate bad
commit, merge ancestry, relocation, sparse state and index replacement. Keep
fixtures inside the permitted workspace on local machines.

Deployment has two distinct steps. First merge the checker/workflow through
the existing required coordinator. The trusted-base PR workflow cannot use its
new implementation before it exists in main; validate the push run after merge.
Then inspect the active main ruleset and add bioetl/no-partial-tree as a required
candidate status from the verified GitHub Actions integration, preserving every
existing required context, strictness and thread rule. Re-read settings and
observe a subsequent PR run on its exact head SHA. YAML alone does not establish
required status enforcement. A required context does not isolate other Actions
workflows able to publish the same status: workflow changes and write permissions
remain part of the trusted governance boundary. Until those observations exist, describe the gate
as deployed or pending, never as enforced. No settings change is performed by
the checker itself.

## Rollback

Restore the previous checker/workflow and required-status configuration only
through the approved rollback. Preserve the existing pr-gate-complete context,
worktree guard, environment guardrails and full-tree rule. A disabled/manual
workflow does not provide automatic PR enforcement. Never rewrite history to
hide an offending snapshot.

## Compliance

No environment mutation, automatic repair, threshold increase or native
runtime hook activation belongs to this check. Codex, Junie and Devin retain
equal runtime ownership. OpenCode write paths remain disabled.

## Post-incident

Record the trusted base, candidate SHA, failing layer and missing evidence.
Repair the actual tree/index or obtain the complete history; rerun the same
check and retain the current-head CI result separately from local validation.
