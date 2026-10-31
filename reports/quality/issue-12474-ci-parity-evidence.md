# #12474 — real-backend schema parity in canonical CI

Acceptance is pending the exact-head remote controls, required CI and independent
review recorded below. A local passing test is not CI integration acceptance.

Source-evidence preservation after squash uses the archival Git tag
`evidence/issue-12474-checkpoint-63216d95433f1e111579303186c4baa12c87c9cb`,
published by ordinary non-force push and independently read back at the same
full commit. It retains both the pinned source `7db9b25e...` and catalog
checkpoint `c83f5b8d...`; it is not a release or acceptance tag. Architecture
consumers explicitly fetch only this task's archival tag prefix after their
existing current-ref unshallow step. Validators retain their source/tree/blob
checks and do not gain an implicit network fallback. Real-Git owning fixtures
delete the source branch, clone shallow main without tags or alternates, prove
the objects absent before explicit preparation and available afterwards, and
reject replacement of an already pinned tag. This closes the source-object
availability finding within this checkout route; it does not provide human
K8/K10 approval or the pending final qualified producer.

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
| Silver missing/extras | Prepared schema and raw records | Raw extras remain visible; prepared-schema removal cannot be masked by raw value; declared nullable fields remain valid with omitted/null raw values; without a prepared schema raw omission is reported | `test_issue_12474_parity_control.py`, Silver unit files and schema-drift E2E |
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

### Exact-head checkout fixture correction

Run `41065194099` on `ae405b63999349197cfe74d2b5f1a356692e837a`
proved the real negative chain: 1 schema mismatch / 112 passing cases, no
errors/skips, failed class job and failed aggregate. Its ordinary counterpart
passed all 113 physical cases, then exposed an inherited ambient event-SHA
assumption in the benchmark reducer's local-environment fixture. The failure was
reproduced locally with `GITHUB_SHA` set to a different commit. That fixture now
uses its existing explicit checkout/run identity builder before removing
`GITHUB_ACTIONS`; it still requires exactly `unproven_environment`. The test
deliberately seeds a mismatching ambient SHA to prevent regression. Product
evidence validation and wrong-checkout rejection are unchanged. This earlier
ordinary run is a FAIL, not final candidate acceptance.

### Authorized producer blocker remediation

The repository owner explicitly authorized addressed ORCID, Grafana provenance
and coverage blocker remediation without weakening checks. The stale identifier
expectations now require the full four-digit final ORCID group, retain the
approved author-alignment null slots for OpenAlex/Semantic Scholar, and retain
the supported numeric or 40-hex Semantic Scholar identifier contract. Positive
and negative fixtures reject truncated ORCIDs, invalid symbols, noncanonical
arrays and unsupported nulls. All 37 owning integration cases pass.

Seven existing owning unit files now cover the prior producer's exact missing
error/boundary/cleanup paths: DQ structural projection, ontology/boolean flags,
PubMed oversized stream closure without partial parsing, guarded HTTP redirect
handling, Gold SCD2 preconditions/no-op, and Silver subprocess deadline/cleanup.
The complete 202-case owning selection passes. The ontology defensive tuple-vs-
member prefix fallback uses an explicitly inconsistent str-subclass fault fixture;
it is not presented as an ordinary production-string scenario. Product code,
budgets and thresholds are unchanged. Focused coverage is diagnostic and does
not substitute for the required new complete 17-shard producer.

The unmodified Grafana candidate workflow on the earlier head failed with real
peer-dependency and stale packed-archive errors (`41077164501`); its host build
was skipped, not accepted. Equivalent delivery remediation already exists in
the separately owned PR #12616. Its branch and artifacts remain untouched; only
accepted, input-qualified upstream results may be reused after integration.

### Silver declared-schema contract correction

The disposable integration exposed an incorrect inference in the earlier #12474
helper change: a stale E2E expectation treated omitted nullable data as a schema
removal even when the declared/prepared schema retained that field. Original main
`0953a8f2` already permits this omission. The helper now preserves that behavior:
new fields are `(raw | prepared) - existing`; removed fields are
`existing - prepared` (prepared defaults to raw when no schema is supplied).
The intended extra guard remains: a raw value cannot mask removal from the
prepared schema. The earlier raw-key-omission interpretation is superseded.

The E2E case reused from PR #12616, head `2b46de77b265b979da60c2979126021a1074f7f6`,
checks actual Delta readback of the omitted nullable value and then still requires
`SchemaEvolutionError` with the exact removed field when the declared schema drops
it. This is an addressed correction to our helper, independent of the unmerged
Grafana dependency; no other source from that PR is adopted here.
Independent comparison over 78,897 combinations against original main confirmed
that the only intentional difference is detection of a prepared-field removal
masked by raw data. The 115-case real-backend suite passed in the disposable
preview without failures/errors/skips. The new Silver blob is resource-free;
its actual Git provenance must be regenerated before publication.

### Own CI telemetry capture qualification

PR #12624 was squash-merged as `2c31b0eed50a4100f5d3c871a4efd6673e4bc376`,
with the same tree as its published `6a71d28e` head. This publication is distinct
from telemetry acceptance. The fresh full drift check still returned exit 1:
two telemetry fingerprint assertions failed. Their original receipts remain
preserved; no old measurements were rebound to changed tests.

The provenance CLI now supports `--ci-run-id <actual-run-id> --pull-request <PR>`
for a newly measured Nightly capture. The existing local-manifest mode remains.
The CI mode verifies immutable original artifact ZIP identity, size and digest,
reconstructs coverage/duration metrics, requires unchanged producer inputs, and
writes only the telemetry squash receipt. Its source is the addressed CI capture
validator from PR #12616, head `0fead443960ac9b19cf2fbf5cae6bddc13ac9a89`;
QM-08 publication decisions and quality API changes are excluded.

Independent review found that a successful coverage combiner could receive
files uploaded after failed tests. Qualification now additionally requires all
17 actual coverage-producing jobs, plus coverage and duration aggregation, to
be unique and completed successfully on the exact run, source SHA and attempt.
The receipt retains those job identities. Missing, duplicate, skipped,
cancelled, timed-out and foreign-source/attempt producers fail closed.

The isolated owning suite passed 244 cases. Reviewer
`/root/telemetry_independent_review` accepted the two-file code diff SHA256
`10eee1de06d6548cd55b9dd2aa0d8e14664984116e5e9cb5983a4dae0637743e`.
The reviewer also tested the guard against actual run `41190149102`: coverage
and duration succeeded but integration failed, and qualification was correctly
refused for that integration producer. This is code acceptance, not a qualified
capture or ADMIT. PR #12616 remains unmerged; its human K8/K10 gate is independent.

### Authorized addressed producer fixes

The owner subsequently authorized the isolated Grafana input/delivery bundle
and the Docker Python patch-version fix. The Grafana transfer is exactly nine
build-input files plus seven coupled delivery manifests/pins and their owning
assertion, copied from immutable donor `0fead443960ac9b19cf2fbf5cae6bddc13ac9a89`.
All 123 declared inputs match the actual build source
`1b91146589ecff2829ae65bae3b8db83ae27e47d` and the working bytes (no newline-only
differences). The donor/build history is retained by the separately published
archival tag `evidence/issue-12474-grafana-source-0fead443960ac9b19cf2fbf5cae6bddc13ac9a89`;
this is source preservation, not a merge or acceptance of the quality migration.

Docker pins now select `3.13.18_git20261030-r0`, the fixed version named by the
original Trivy findings for CVE-2026-114583 and CVE-2026-115557. The exact-version
CI probe, provenance text, owning assertions and current documentation remain
synchronized. All runtime hardening assertions and the zero-CVE policy remain
unchanged. Local owning tests and pre-commit passed; two native Windows skips
require POSIX sh and remain distinct from PASS. Actual image build/scan and a
fresh qualified capture are still required on the resulting committed inputs.

The first addressed image build on `89fbcab7` produced Python 3.13.18, but its
caller still selected the old immutable Docker workflow `843eb3f1c9410df7eccfebf3c8a810cc897ed0e9`.
That old workflow required 3.13.16, so provenance failed before scanning. The
caller, pin registry, strict allowlist and exact owning test now consistently
select the reviewed published Docker workflow at
`89fbcab7461c6400f8b2df38ebd95375713e7d32`. No old pin is retained as an additional
allowlist exception. All 93 pin/runtime-policy owning cases passed.

The prior local 17-shard attempt on `89fbcab7` was stopped with its original
incomplete manifest and logs preserved when that required test-input change
became known. Its three completed shards are not a complete capture. The CI
coverage producers on that revision succeeded, but its separate currentness
and generated-governance results remain failures. New measurements must bind
the completed caller integration rather than inherit that earlier attempt.

An extra strict-mypy diagnostic of the repo-side pin checker returned
`no-any-return` in its unchanged YAML loader. Independent review confirmed the
same function bytes on main and this candidate. This diagnostic remains FAIL;
the configured required mypy targets (`src/bioetl`, `src/memory`, and
`scripts/engineering/quality`) are unchanged and still mandatory. The unrelated
YAML/security logic and mypy exclusions were not changed to silence it.
