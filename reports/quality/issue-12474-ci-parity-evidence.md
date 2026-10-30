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
`python -m scripts.engineering.ci.physical_schema_parity --junit <new-path>`.
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
