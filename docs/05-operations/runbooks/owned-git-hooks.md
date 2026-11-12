______________________________________________________________________

Version: 1.0.0
Class: operational
Owner: @bioetl-platform
Status: implementation qualification
Last verified: '2026-11-12'

______________________________________________________________________

# Owned Git hooks

## Purpose

Install verifiable local callbacks without changing existing debt budgets,
Git settings or the project's environment files. Git hooks remain bypassable;
independent full-tree CI and existing required checks protect shared history.
These callbacks are Git events, not AI runtime lifecycle events.

## Trigger

Use for explicit hook installation, inspection, framework/interpreter upgrade or
rollback. Requalify after changing the owned callback bundle.

## Impact

Missing or stale callbacks can leave local protections inactive. Invalid ownership,
dependency or timeout evidence blocks Git operations once this deployment is active.

## Preconditions

Use a full approved checkout and an absolute project interpreter with pre-commit
4.7.0. Preserve existing callbacks and do not change environment files. Native AI
runtime loading is outside this Git-hook qualification.

## Procedure

First merge the shared guards, full-tree checker and installer into the protected
main branch. Fetch that branch in an approved full checkout. Bootstrap dependencies
explicitly with the chosen project interpreter: `python -m pre_commit install-hooks`.
That command may download dependencies; it belongs outside commit/push.

Run `python -m scripts.engineering.repo hooks install --python <absolute-project-python>`.
The default source is `origin/main`, resolved once to a commit. Use the Windows
project interpreter on Windows and a separately provisioned Linux interpreter in
WSL. This command copies tracked helper blobs into an immutable, hashed bundle
under the common Git metadata directory; it creates no Git checkout or worktree.
It does not install dependencies or execute existing callbacks.

`python -m scripts.engineering.repo hooks doctor` checks effective hook discovery,
owned file hashes, bundle hashes and interpreter presence. PASS means installation
identity matches; it does not prove a vendor runtime loaded an adapter or that
every configured check passed. Qualify actual invocations separately using private
fixtures and the exact installed framework version. Never infer execution from a
file's presence. Missing or changed evidence is ERROR.

## Ownership and parallel operation

Installation honors the effective `core.hooksPath` read through Git. A path outside
the common metadata directory or a symlink requires host review and is refused;
the installer does not rewrite local/global Git settings. A shared exclusive lock
prevents simultaneous install/rollback. A stale lock is ERROR; inspect its owner
before manual recovery. Ordinary callbacks use unique private input files.

Foreign pre-commit, pre-push and commit-msg callbacks are backed up with hashes
and chained once after protected guards, retaining their existing interpreters.
Disabled POSIX callbacks remain disabled. A recognized pre-commit-generated entry
is backed up but replaced by one framework invocation; the framework's existing
legacy callback protocol remains intact. Other hooks, including reference-
transaction, remain untouched. Reinstallation of a valid deployment is idempotent;
an upgrade requires explicit rollback then installation from the new main SHA.

## Runtime behavior

Protected staged environment paths, full checkout/index and debt guards run before
foreign/framework callbacks on commit. Push validates each non-deletion local tip
against `origin/main`, then runs existing configured push checks. Missing base,
unsupported policy format, dependency failure or incomplete evidence blocks the
operation. Commit-msg retains the existing framework stage and protocol; it does
not repeat tree/budget checks. No automatic generator, staging or debt ratchet is
added. An authorized env-file change needs a separate reviewed host procedure;
there is no caller-supplied self-approval flag.

The offline framework adapter is qualified only for pre-commit 4.7.0 and the tested
private API signatures. Unknown versions fail before configured framework callbacks. Missing repository
cache or unhealthy/missing environments fail instead of cloning or installing.
Existing checks remain required. The dashboard QA suite now has an explicit
pre-push stage, aligned with the other dashboard suites; it no longer inherits
every framework stage, including commit-msg. Its independent CI gate remains.
Offline environment switches
reinforce this rule but do not sandbox network calls made by arbitrary hook code.
The qualified framework error handler is replaced with controlled failure output;
it does not persist raw exceptions or child output in pre-commit.log. Arbitrary
callbacks still require host controls for their own logging and filesystem access.

The outer watchdog covers protocol input, Git discovery and callbacks: 30 seconds
for commit, 10 for commit-msg, 180 for push. Timeout, malformed protocol, absent
interpreter or missing containment evidence blocks with ERROR. Child output is
suppressed; run the named scoped check explicitly for detailed diagnostics without
publishing secrets. Existing check failure blocks with FAIL. These initial limits
need measured platform qualification; changing a timeout cannot waive a check.

Windows descendants enter a kill-on-close job before their first instruction.
Linux uses a separate subreaper, process groups and pidfds, including adopted
detached descendants. Normal exit, timeout and interruption require cleanup.
Unsupported kernels/permissions fail closed. Forced host/supervisor termination and
hostile filesystem replacement require a host boundary; hooks are not an OS
sandbox. Windows and WSL installations require separate interpreter qualification;
one common hook deployment must not be claimed portable across incompatible
interpreters. A changed platform requires rollback/reinstall and fresh evidence.

## Verification

Local mechanism qualification on 2026-11-12 used private synthetic Git fixtures
and a deployment bundle, without installing callbacks in the project repository.
Windows: Python 3.13.7, pre-commit 4.7.0, pytest 9.2.0. WSL: Python 3.13.18,
pre-commit 4.7.0, pytest 9.2.0, virtualenv 21.15.6. The WSL isolated suite passed
49 tests in 60.73 seconds, including normal and linked checkout protocols,
custom metadata-local hooksPath, foreign callback preservation, detached-child
cleanup and stalled protocol input. This is not the full BioETL test suite or
proof of native AI lifecycle loading. Windows skips POSIX-only setsid and executable-bit cases;
Linux exercises them. The corresponding Windows suite passed 46 tests and skipped
the three POSIX-only cases. Platform evidence does not authorize cross-platform cache
reuse. Repeat qualification after any bundle/framework/interpreter change.
The fixture also invokes actual Git commit dispatch after installation, checking
that both Git events run exactly once and a preserved Python callback keeps its
interpreter. This qualifies discovery as well as direct callback invocation.

## Limits and additional controls

Local bypasses, arbitrary shell writes, same-user bundle replacement, later index
changes and `SKIP`/framework configuration changes require host controls or CI.
Commit-time env checks occur after a filesystem write and cannot prevent that
write. Tip comparison alone does not prove absence of historical secrets: retain
secret scanning. Tree anchors do not validate every individual deletion: retain
architecture, policy and required generated-artifact checks. A successful callback
is not a full runtime Proof-or-Stop acceptance receipt.

## Rollback

Run `python -m scripts.engineering.repo hooks rollback`. All owned and backup hashes
are checked before any hook changes. A later owner's edit blocks rollback rather
than being overwritten. Original callbacks and modes are restored; absent originals
are removed. Bundles/backups remain for inspection. Removing this deployment never
removes the independent CI guard or weakens existing required checks.

## Compliance

No debt-budget increase, environment-file mutation, runtime parity exception,
external-service activation or OpenCode write-path activation belongs to deployment.
All runtime peers use the same repository guardrails.

## Post-incident

Record source SHA, interpreter/framework versions, effective hook path and the
controlled failure reason. Preserve bundles and backups. Repair the failing layer,
then repeat fixture qualification and inspect doctor; do not infer PASS from a
missing callback, timeout, skipped check or stale receipt.
