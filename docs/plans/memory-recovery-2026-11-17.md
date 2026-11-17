# Memory recovery implementation

Publication branch: `codex/memory-recovery-pr-20261117`.
Preparation branch: `codex/memory-recovery-20261117` (preserved at
`c69f7964099daebe424bc81d1286999355463ddc`).
Publication base: `f1bed44e74b708f2c7fed17a18e7ee5d9c8ba654` from `origin/main`.
Initial source commit: `9e3361be1320f0d032668c66ae5c67393de98e23`.

## Outcome and boundaries

Restore useful local retrieval and prepare a branch-bound native Memory profile.
Preserve existing graphs, registrations, unrelated work and all env files.
Do not force a BioETL working directory in the global MCP configuration.
Local checks and native current-chat acceptance are separate evidence.

The implementation now uses the governed full worktree at
`D:/github/BioactivityDataAcquisition-worktrees/memory-recovery-20261117`.
The user explicitly approved creation of only its tracked `.env.example`; the
real `.env` was neither copied nor changed. A concurrent writer switched the
original checkout back to another branch, so its prepared recovery profile is
retained inactive and is not used as a fallback for this worktree.

The preparation branch inherited unrelated unmerged IUPHAR commits. Only the
memory changes are transferred onto the publication base; the original branch
and commits remain intact. Before switching branches, the owned idle Memory
profile was backed up and stopped through its normal drain procedure, without
forced process termination. The publication branch gets its own scoped identity.

## Execution checkpoints

| Step | State | Outcome and acceptance |
| --- | --- | --- |
| RF-001 | complete | Source identity captured; 20 protected backup members preserve both existing profiles, registry, configuration and seed. |
| RF-002 | complete | Partial retrieval, CLI status, cwd rendering, derived exclusions and reviewed navigation are implemented; focused tests and type checks pass. |
| RF-003 | complete | The preparation profile was stopped without force and preserved. Publication profile `7d49cd51ec16...` is independently registered, active and READY on port 55005. |
| RF-004 | partial | Native config/read verified a session-only workspace override without a forced MCP cwd. Current-chat Memory tools remain unavailable; normal-session native acceptance is NOT_TESTED. |
| RF-005 | source_checked | Full RAG/timeline and strict read-only acceptance passed at `cbbd4e9a03e...`: 8124 eligible/indexed sources, 66889 chunks, no stale/missing sources, and zero changes across 14784 observed files. Repeat after the final source commit. |
| RF-006 | complete_scoped | Publication-profile stdio acceptance passed: bounded read, reconnect persistence, probe cleanup, foreign-workspace refusal and positive control. This does not qualify native current-chat tools. |
| RF-007 | deferred | Existing main recovery requires an explicit reviewed reconciliation of reused process identity; no PID termination or record deletion. |
| RF-008 | finalizing | Focused Memory suite: 98 passed, one Windows symlink skip; selector suite: 309 passed. PR #13169 CI is green at `cbbd4e9a03e...`. Regenerate the scripts inventory, then bind final checks and closeout to the resulting head. Native acceptance remains NOT_TESTED. |

RF-002 precedes the final RF-005 build. MCP checks in RF-006 require RF-003;
local retrieval checks in RF-006 require RF-005.
RF-007 is independent and cannot block safe preparation of the new profile.

The historical checked-in seed remains unchanged. Source review found obsolete
version, orchestration and dashboard assertions. The new profile instead uses
`memory.tooling.navigation_seed.build_navigation_seed`: seven current source
pointers with titles and content digests, without inherited body assertions.
The generated seed is published once inside this checkout's ignored cache and
then pinned by the provider descriptor.

The post-task smoke found that current scope-bound `episodic/tasks` notes
were missing from the root Git exclusions. The task namespace is now kept
machine-local alongside legacy session/summary directories. A read-only Git
contract test verifies exclusion of session, summary and scope files while
retaining a shared catalog control. Existing notes are preserved in place.

## Validation and recovery

- Test all four RAG/timeline availability combinations, stale artifacts, strict
  no-refresh/no-note behavior, CLI JSON exit status, and TOML transport parity.
- Use process-scoped Git trust for the exact root; never change global Git trust.
- Generate with `--rag-build-scope full` into `src/memory/derived` and validate
  the catalog/chunk pair against the final source snapshot.
- Compare graph binding, engine pins, activation closure and provenance without
  treating source tests as proof of native tool availability.
- After successful persistence probes, compare remaining graph data and allow
  the expected provenance growth. Never roll a whole graph back over new writes.
- On partial registration or unknown request outcomes, retain evidence and stop
  the affected transition. Restore only owned configuration changes after a
  fresh drift check; never overwrite the shared registry from an old snapshot.
- Documentation link changes require the owner-generated cleanup inventory.
  Runtime mirror checks apply if runtime agent or skill sources change.

The preparation checkout reported an inherited 8-day freshness failure in
`docs/reports/evidence/project-test-health/SUMMARY.md`. The publication base
contains an upstream metadata refresh dated 2026-11-17 for the tracked-test-module
inventory scope. Re-run docs validation against that source; this metadata does
not prove a current full test-suite run. Native current-chat Memory acceptance
remains NOT_TESTED until actual tools are available.

## Evidence

Implementation receipts and command logs belong under
`reports/quality/memory-recovery-20261117/`; private registry, credentials and
raw graph backups remain in protected machine-local storage outside Git.
The user authorized main synchronization and draft PR publication on 2026-11-17.
Publish only the memory scope. Merge still requires separate authorization.
