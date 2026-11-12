______________________________________________________________________

Version: 1.0.0
Class: operational
Owner: @bioetl-platform
Status: implementation qualification
Last verified: '2026-11-12'

______________________________________________________________________

# Scoped post-change checks

## Purpose

Select additive local checks from actual committed, staged, unstaged and untracked
changes. Keep existing pre-commit, pytest and CI owners authoritative. These are
explicit command-wrapper checks, not native Codex, Junie or Devin lifecycle hooks.
OpenCode remains subordinate and unqualified adapters remain disabled.

## Trigger

Run after relevant edits and before submitting a PR. Re-run after state changes.

## Impact

Missing dependencies, unknown surfaces, corrupt receipts and changing state return
ERROR. No automatic staging, generation, dependency installation or debt ratchet
occurs. A selected check can fail because a required artifact needs its owning
generator; perform that separately, review the diff, then validate again.

## Preconditions

Use the approved full checkout, a prepared project interpreter and resolvable
`origin/main`. Existing environment-file authorization and worktree rules apply.
Never create environment files to exercise this mechanism.

## Procedure

`python -m scripts.engineering.repo checks plan` reports PLANNED / NOT_RUN with
the selected check identifiers. It does not establish PASS.

`python -m scripts.engineering.repo checks validate` always runs the protected
tree and debt guards afresh, including working policy bytes and new policy files
against the pinned trusted base. Both indexes remain independently checked.
Planning is enclosed by matching state snapshots before any selected check starts.
Additional owners cover runtime parity/static
contracts, documentation inventory, module source inventory, workflow policy,
pre-commit configuration and changed Python lint. Unknown paths require an owner
and return ERROR. This command does not claim complete test coverage.

DASH-FIT-004 requires the first-window check for every code/test/docs change;
its broad gate remains intact. Other dashboard checks are selected only for
dashboard sources, declared helpers, quality owners and dependency manifests.
No Grafana service or browser renderer is started.

On success, the result includes an immutable observation receipt and, where
eligible, a separate static cache receipt. Pass the latter via `--reuse <path>`.
Reuse is limited to 60 seconds and the exact state, interpreter, package set,
environment digest and checker sources. Time-sensitive gates and protected guards
always execute again, as do documentation and coverage inventories whose inputs
may include ignored local artifacts. A cache hit retains its original observation
and never renews the 60-second lifetime. Ordinary observations cannot substitute for cache receipts.
`checks receipt --receipt <path>` validates the expected observation against current
state; it does not grant runtime admission or CI acceptance.

## State and failure handling

Identity includes HEAD, trusted base, both the default and supplied Git indexes,
worktree/Git identity, changed source bytes (including ignored policy candidates
under trusted policy prefixes) and root dotenv hashes. Hidden index
entries, symlink escapes and incomplete measurement fail closed. No source content,
environment value or child output is stored. Local hashes detect staleness; a user
who can forge local files is outside this trust boundary.

Each Git measurement has a 10-second timeout; inputs and receipts are bounded.
Validation allocates 120 seconds to child execution, with individual static checks
limited to 30 seconds and dashboard tests to 90. Measurement bookends add bounded
Git calls. The owned process runner cleans descendants; missing cleanup evidence
is ERROR. The same private runner supports Windows and qualified Linux/WSL.
The Windows pretest wrapper now returns an error when Bash is unavailable.

Parallel invocations write distinct UUID files under common Git metadata. They do
not overwrite one another. Worktree identity prevents cross-worktree reuse; a
concurrent edit detected by either bookend prevents a new qualifying receipt.
There is no filesystem lock against arbitrary edits after the final observation.

## Verification

Run focused receipt, scope-selection and real Git-dispatch regression tests on
Windows and WSL. Verify malformed/missing inputs, changed indexes and source,
fresh protected checks despite cache reuse, concurrent writes and callback-staged
budget increases. Record measured durations separately by platform and scenario.
Local mechanism tests do not prove native lifecycle loading or current-head CI.

Windows qualification (Python 3.13.7, pre-commit 4.7.0, pytest 9.2.0) passed
71 tests with one POSIX-only skip. WSL (Python 3.13.18, pre-commit 4.7.0,
pytest 9.2.0) passed 71 tests with one native-Windows-only skip in 172.87 seconds. A representative-path experiment executed
the actual selected check commands in this checkout, without editing those
representative inputs or invoking agents:

| Scenario | Selected owners | Measured seconds | Outcome |
| --- | --- | ---: | --- |
| docs | cleanup inventory, mandatory first-window | 6.999 | PASS |
| Python | module source inventory, first-window, Ruff | 31.372 | PASS |
| runtime | parity, static runtime doctor, docs inventory | 3.205 | PASS |
| dashboard | first-window, dashboard static gates | 10.966 | PASS |

Measurements are one local observation under concurrent machine load, excluding
scope measurement and the always-fresh protected core. They are not a comparison
against an old baseline, a production workload benchmark, or token/model metrics.
The Python source-inventory owner accounted for 26.141 seconds; no heavy suite
was added to every commit. Framework cache reuse across platforms is not inferred.

## Limits and additional controls

Git hooks can be bypassed and command wrappers must be explicitly invoked. Keep
the independent required `bioetl/no-partial-tree` status, existing pytest/CI,
generated-artifact checks, secret scanning and runtime parity gates. No local
receipt can create Proof-or-Stop ADMIT or replace a CI receipt. A skipped, failed
or unavailable check never becomes PASS.

## Rollback

Stop invoking the optional `checks` command and revert its implementation through
review. Requalify owned Git-hook bundles after reverting callback changes; use the
documented rollback/reinstall procedure. Preserve independent CI and all budgets.

## Compliance

No new runtime event or vendor configuration parameter is assumed. No environment
file mutation, budget increase, external service or native adapter is introduced.

## Post-incident

Preserve the controlled reason and source identity, repair the owning dependency
or artifact, and rerun fresh checks. Never repair evidence by editing a receipt.
