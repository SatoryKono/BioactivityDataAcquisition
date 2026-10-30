# #12474 — real-backend schema parity in canonical CI

Acceptance is pending the exact-head remote controls, required CI and independent
review recorded below. A local passing test is not CI integration acceptance.

## Ownership and accepted input

The repository owner authorized this implementation on 2026-10-30 and confirmed
that existing Jules session `2798176471200290413` is dead. No new Jules session
was started and its claimed unpublished branch was not modified. Implementation
uses `codex/issue-12474-qualification-20261030`, initially based on main
`90128184d58cce8b7245027569882eaa01ce1297`, tree
`3608b992de22287e92a897ecf3e963acb43083ec`. Existing worktree changes, commits,
patches, the complete v5256 operation journal and raw qualification responses
remain preserved outside the repository; they are not new acceptance evidence.

Prerequisite #12475 is closed/completed. PR #12609 merged as
`54b212a94878d2785c2c139e631950b750081014`; historical head
`e5e02ed4e42356533a01a4120653a33db8cf95d4` passed required run
`40787371607`. That result does not qualify this new revision. The original
backend findings and measurement history in
`reports/quality/issue-12475-physical-parity-evidence.md` are retained unchanged.

### Gold nullability owner disposition

On 2026-10-30 the user, explicitly answering as backend/contract owner, accepted
physical `nullable=true` as a documented limitation of the current Gold-to-Delta
write path for #12474, with CI
checking that physical contract and separately prohibiting logical nulls.
The authenticated repository-owner account is `SatoryKono` (read-only identity
check); no GitHub APPROVE review is submitted on the user's behalf.

This is an acceptance of the limitation, not a claim that the #12475 mismatch
was fixed. Logically required columns remain `nullable=False` in their contracts.
Physical readback checks retain the finding for both configured Gold modes;
strict Gold writes must reject required `entity_id=None` with
`gold_contract_required_failure` / `gold.contract.required_fields`, before any
Delta commit. The negative tests inspect this exact error, not arbitrary I/O or
configuration failures. Bronze JSONL has no persisted schema; physical
nullability is inapplicable there.

## Acceptance matrix

| Case | Backend and logical contract | Required observation / outcome | Owning test |
|---|---|---|---|
| Config census | 27 resolved configs; Bronze JSONL; Silver Delta merge/evolve; Gold 25 SCD2, 2 overwrite | Exact census, real writes/readback for every config; Silver schema equals filtered logical Arrow schema, Gold types and documented nullability | `test_issue_12475_physical_parity.py` |
| Bronze | Compressed JSONL/Zstandard | Values/types/null preserved; no persisted-schema claim | Same file, Bronze round-trip |
| Silver types/nullability | Temporary Delta, prepared Arrow schema | Exact physical readback; permitted int-to-float coercion does not report drift | Same file, evolve/coercion cases |
| Silver evolution | Nullable field addition vs forbidden type change | Addition accepted; type change raises `SchemaEvolutionError`, exact `changed_fields`, persisted string type unchanged | Same file, type-change negative control |
| Silver missing/extras | Prepared schema and raw records | Raw extras remain visible; prepared-schema removal cannot be masked by raw value; raw key omission retains existing strict error contract; present nullable `None` is distinct | `test_issue_12474_parity_control.py`, Silver unit files and schema-drift E2E |
| Gold SCD2 | Temporary Delta, strict publication schema | Types, explicit physical nullable finding; repeated versions/history/current row/idempotency and mixed batches | `test_gold_writer_versioning.py` |
| Gold overwrite | Temporary Delta, strict schema | Types/nullability and repeated-write equality | Same file, overwrite test |
| Gold logical required | Both SCD2 and overwrite | Exact required-field rejection before persisted commit | `test_issue_12474_parity_control.py` |
| Positive physical control | Real temporary Delta int64/nonnullable | Logical/physical schema equality | Same file, real Delta control |
| Negative physical control | Same fixture; dispatch changes expected logical type to string | Assertion explicitly reports schema mismatch; pytest, canonical job and aggregate fail | Same fixture through canonical workflow dispatch |
| Fail-closed execution | Missing backend/module/JUnit, empty selection/results, error/skip/xfail or child nonzero | Nonzero result; none can qualify as PASS | `test_physical_schema_parity.py` |
| CI routing/aggregation | Existing generated-artifacts gate, class-lane schema-parity step | Storage/config/backend/test changes select gate; same step outcome feeds required assertion and aggregate | CI runner, classifier/lane and architecture owning tests |

All fixtures are synthetic and temporary. No production datasets/endpoints are
required. Actual backend/tool versions, command receipts, exit codes, source
identity and output hashes are recorded with the validation artifacts.

## CI owner and controls

`.github/workflows/pr-required.yml` retains the single `schema-parity` step,
first running the existing logical checker and then
`python -m scripts.engineering.ci pr-lane-results physical-parity --junit <new-path>`.
The runner selects all six prerequisite owning files plus the new controlled
physical fixture. Missing backend/module, absent/stale/empty JUnit, skipped/error/
failed tests or a nonzero child exit cannot become success. Strict pytest config,
markers and import mode remain enforced; ambient `PYTEST_ADDOPTS` is removed.

Manual `workflow_dispatch` input `physical-parity-negative-control=true` changes
only the synthetic control's expected type. It is false on ordinary PR runs.
The command returns the actual pytest failure: no expected-failure job, soft-fail
or successful aggregate hides it. Dispatch uses the explicit merge-base diff,
including after evidence-only follow-up commits. JUnit is uploaded even on failure.

## Validation and publication ledger

Local prechecks and earlier failures remain preserved; they are not relabelled.
The initial stale governance/CI-family checks failed as expected after changed
inputs. Only canonical generators may update their artifacts. Telemetry requires
a new qualified producer on these test inputs; previous measurements are not
rebound to this tree. Pending final exact-head receipts, CI links, independent
review, merge and issue readback will be appended before closure.

### Scoped CI corrections and static source maintenance

The first remote runs exposed missing explicit artifact retention, a missing VCR
inventory row for the new fixture, and Silver helper complexity 16 over the
existing limit 15. Retention is now one day; the VCR inventory uses its canonical
sync command; the pure helper uses equivalent set operations. The independent
reviewer checked 78,897 combinations against the previous implementation with
identical results. No complexity limit or test was relaxed.

The frozen #12552 whole-source census also invalidates after this production
helper changes. Its canonical checker now supports an explicit source maintenance
update for reviewed resource-free files only: `--update --source-commit <full SHA>
--reviewed-source <path>=<reviewed SHA256>`. It rejects changed resource-bearing
files, new/removed files, incomplete reviewed sets, incorrect digests and any
unreconciled acquisition. It retains the old source commit in maintenance history,
preserves the 202 resource definitions and 377 historical dispositions, and keeps
every runtime scenario `NOT_RUN_12553`. Actual Git blobs/tree and partition hashes
are generated and checked, not hand-edited. The changed Silver file has no resource
references and its modified pure function calls only `set()`.

An independent security-producer failure was reproduced on clean main
`0953a8f2b32c934eb9927389adfbc469c53b23c4`: the PII scanner reports `email` in
`_api_request_sanitize.py`, despite the existing request-metadata redaction path.
The unchanged test and product file are outside this parity implementation;
their FAIL is retained and cannot qualify the new telemetry producer as PASS.

On 2026-10-30 the user separately authorized only an addressed security-test
correction: the exact request-sanitizer path qualifies only if its real function
replaces email/Email/EMAIL with `[REDACTED]`. A negative control replaces the
sanitizer with an identity function and requires the PII gate to reject it.
Other paths and PII patterns retain their policy; no product code, credentials,
security settings or global ignore changes are included.

Two further producer failures also reproduce on clean main, without this PR:
`test_governed_publication_identifier_arrays_publish_canonical_json_patterns`
expects a one-character final ORCID group instead of the configured four-character
group, and `test_private_host_delivery_binds_source_and_survives_data_volume`
finds two plugin package-lock digests inconsistent with the accepted host manifest.
They remain outside the authorized parity/security correction. A failed producer
and its coverage artifact are not a qualified telemetry capture.

### Canonical entrypoint and explicit-control review correction

The scripts lifecycle cap remains 334. The new standalone runner/helper modules
were consolidated into the existing `pr-lane-results physical-parity` command and
the existing resource-inventory checker; only the two files introduced by this PR
were removed. The canonical inventory/catalog report 698 scripts / 334 active.
Independent AST comparison confirmed identical execution, JUnit and rebind guards.

An explicit dispatch negative-control input now forces `generated-artifacts` to
required with reason `explicit_physical_parity_control`, including docs-only
diffs. The ordinary PR default does not pass this flag to trusted-base gate code.
Owning tests check the real catalog, workflow forwarding and skipped-step refusal.

The class lane now checks out the classified candidate SHA explicitly. Its
existing schema-artifacts/parity steps run immediately after dependency setup;
a controlled mismatch fails before unrelated long-running scans. A positive
run still executes every selected lint/type/security/test/duplication gate.

The historical producer also failed module-coverage regression guards. The
changed Silver module's missing defensive type-diff guard is now covered by
two owning cases (no existing schema / empty batch). A focused current-source
measurement including the existing detect/warn regressions passed 141 tests:
71/71 statements covered (100% lines), 27/28 branches (96.43%), combined 98.99%.
The remaining partial branch is the Protocol declaration exit. This targeted
measurement does not replace the required complete telemetry producer and does
not overwrite its global measured inventory.

Checkpoint required run `41058632237` passed on PR head
`59e8c26b15c71329301106f93ece564433e00e4d`. Its default GitHub merge execution
`332fc4b7f0181f044dbe70be853be31124471601` was independently fetched and has
exactly the candidate tree `b325472db0be42bda1ea178d4f614b761eca908f`.
The corresponding negative dispatch `41058676623` was cancelled as superseded
while still scanning history; its schema control was NOT_RUN and is not proof
of mismatch propagation. New exact-head positive/negative runs remain required.
