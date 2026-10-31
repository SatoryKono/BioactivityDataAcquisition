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

The strict impact shadow compare subsequently identified two task-owned paths
without routes: the monitoring compose file and Docker security runbook. Their
exact routes now select existing owning tests; unmapped paths still fail.
The Windows full producer also exposed a synthetic scanner fixture whose
reviewed digest used LF text while its writer created CRLF bytes. That fixture
now hashes the actual written bytes, matching the unchanged scanner contract;
the wrong-digest negative control remains. All 147 focused owning cases passed.
The complete actual diff plus 20 applicable future generated outputs was checked
before freezing again: 56 unique paths, no unmapped input, 86 selected targets.
The previous local attempt remains incomplete with its recorded failed shard;
none of its partial measurements are promoted as a complete capture.

The independent review of `9ffbc6f05305682ad6d11c74f55d267facdbbaac`
corrected an earlier check summary: `route-fixture-final-nontel-check` actually
returned exit 1 because the local main tracking ref was absent. That FAIL is
preserved. After a fresh fetch, `routing9ff-nontel-check-after-fetch` returned
exit 0 without changing the working tree. Actual Nightly `41201108375` completed
with all 17 coverage producers and both aggregation jobs successful, while
the old telemetry/currentness gates remained FAIL. Original artifact archives,
API identities and digests are preserved; this is not final admission.

The Windows local attempt on that source exposed another synthetic newline
fixture and remains incomplete/failed. The synthetic time producer now writes
the exact declared UTF-8 bytes; its strict digest comparison and all five
success/failure outcomes remain. A complete tooling diagnostic then exposed
`nul.csv`, a Windows device alias even with an extension. Only that temporary
filename changes to `malformed.csv`; its null-byte payload, malformed-error
contract and financial redaction assertions remain unchanged. The next full
tooling validation returned exit 0: 3583 cases, no failures/errors, 54 existing
platform/fixture skips. The targeted fixture/routing suite returned 149 PASS.

A parallel authorized repair published `a4a0869a47a8cbb1a726c278e72d4cb8da4dedf9`
before writer coordination. Both histories and the unique local patch were
preserved in a verified bundle. Its author then explicitly handed off the sole
writer role and stopped writing. The full six-file changeset was integrated
without rewriting history. Its shared ESLint helper preserves the existing
rules; the new exact helper route selects the existing plugin governance tests,
and the fail-closed shadow comparison covers the actual full diff.

That parallel changeset copied module coverage candidate artifact `13041464406`
from run `41199002040`, source `0d09e1cfecc58948464ae32caf703443a9b1d666`.
The author confirmed that no reporter was executed for that copy. It remains
provisional historical input, not a qualified new measurement or acceptance.
Our complete new capture and canonical reporter must replace it before closeout.
The lint topology change also invalidates the earlier claim that all 123
historical Grafana build inputs equal the current tree. Own Router run
`41202898231` failed its unchanged moderate npm audit gate before the build;
its actual findings and original logs are preserved. Neither a skipped host
build nor the prior donor success is presented as current Grafana acceptance.

The owner then authorized addressed `glob`/`minimatch` remediation with consumer
compatibility and security-negative controls. Both plugin graphs now select
`glob@14.0.3` and a private callable/named entry point that delegates to the
unmodified npm `minimatch@11.0.3` implementation. No legacy matching algorithm
is retained. Node 20 remains within the declared engine range; removed legacy
`makeRe` APIs are not represented as supported. Both normal clean installs and
both nine-case contracts passed. Real vulnerable-version controls fail for
the actual amplification/continued-filesystem-work assertions. The fixed
matcher honors its explicit upstream expansion cap; this is not a claim of
linear default globparts growth. Original development diagnostics are retained.

The private archive has 1237 bytes, SHA256
`7de54d9e68d54b6c2fd82dce7c4c584fbcd72b9e80c351c319fdee3628a6b736`;
both npm-generated lockfiles retain its real SRI and the fixed upstream SRI.
The existing Jest/NYC commands and worker limit remain; nine controls are appended
through `&&` in both existing `test:ci` entry points. Both unchanged moderate
audit gates pass with six LOW findings remaining through unfixed `deepmerge`;
no advisory exclusion or severity change is introduced.

The first combined Python owning run returned exit 1 only because the strict
existing override dictionary rejected the two newly authorized bindings:
532 PASS, one FAIL, four existing historical-render skips. The exact dictionary
now includes only the approved pins, with added fixed-upstream/consumer checks;
all router/uuid constraints remain. The affected recheck passed 63 cases with
the same four skips. Windows Jest remains a preserved environment FAIL before
test execution: the SWC native cache rejects local DACLs. No permissions or
security settings were changed. Actual Linux Jest and host build acceptance
remain mandatory and are not inferred from the local type/lint checks.

The subsequent parallel `fa8d903223efda3c26c19af08933d8a4000b2a7a` update was
preserved and integrated after a second explicit sole-writer handoff. It adds
the workflow-selector contract and hoists an unchanged route string. Because
it changes TEST_INPUTS, the complete successful 17+2 CI capture on
`b4e4332b1d9a5924f999eba941a32837a1bb0443` is historical evidence, not a capture
for the new head. Its original archives and source qualification are preserved.
The interrupted local attempts, including the WSL launcher failure and the
subsequent seven-successful-shard attempt stopped for that external input change,
remain incomplete; none are combined or promoted as the final measurement.

Fresh readback at 2026-10-31 14:15 UTC found external merge of PR #12626:
merge commit `32903f5187961922f19cf14417aa19afdf30c208`, actor `SatoryKono`,
merged at `2026-10-31T14:14:03Z`. Its tree is exactly the former published
`fa8d903` tree, `e9ca7401d8fd53a322fd6ca1f06658bcb7eaafaa`; the author of
this qualification did not perform that merge. Issue #12474 remains OPEN.
The preserved staged changes were carried onto a new owned branch directly
from that main commit without conflicts or source loss. The source-owning
437-case validation and pre-commit passed before that identical-tree move.
Remote-main pre-check then correctly failed for the advanced base; its actual
canonical remote-main update is retained. No telemetry result or ADMIT is
inferred from the external merge. A new full frozen-source capture and Linux
Grafana qualification are required before issue acceptance.

### Continued qualification after the external merge

The continuation is published in PR #12633. Main subsequently advanced to
`da58d2c13f4e2e2d4159effff83fff4c71a7f35f`, tree
`508a180dfae88d9368f7bd0af3efdddb9d08ce41`; both incoming commits were preserved
by a normal merge. The changed Router development metadata required a real
`npm pack`: the resulting bridge archive has SHA256
`93f02cd3c3420b1854a1c2228f70a99222a754286c2494dc9773145fef8614be`.
Both plugin locks were regenerated with native Linux npm. Their only changed
package field is the existing bridge alias integrity; no resolved dependency
version changed. Windows npm attempts that pruned WASM optional dependencies
were rejected and retained outside the repository.

Own Nightly `41209731607` on `0e37d00f8d5100c5ed0b99d19fce1bae2d022a13`
failed, including its integration producer. Successful aggregators therefore
do not qualify this capture. The Linux local17 attempt also remains incomplete:
six completed shards passed, one tooling shard rejected the installed system
Node 18, and the attempt was stopped for the confirmed integration input defect.
The actual outer exit was -15; all original measurement bytes were preserved.
The locked Node 24 runtime is available for the next complete attempt.

Router `41209731413` passed both plugin jobs but failed because BuildKit had
not loaded the immutable base into Docker's inspectable store. The addressed
pull-before-inspect correction preserves the original digest and all parity
checks; 12 owning controls passed. Router `41210863632` then reached the real
complete filesystem comparison and failed against the old delivery image.
Original ZIP identity checks show exactly two changed Scenes source maps;
JavaScript and all other plugin assets are unchanged. A local candidate built
from those exact CI outputs matches the actual CI rebuild's complete rootfs
`897a29cd108d9dc76655a2fd5b94c2915f4cbbbe53e0b5ddeafefb0632a17437`.
Its managed variant equals that parent minus Scenes, with all 15,478 paths
matching the previous managed runtime. These are local preparation receipts,
not registry publication, current delivery acceptance or ADMIT.

The source-only provenance generator rejects unsuccessful/foreign attempts,
substituted ZIPs, incomplete parity and source additions/deletions. Independent
review findings were fixed before adoption; its six isolated Python fixture
methods run through the existing image verifier's 13 Node controls. It cannot
relabel the changed image as an unchanged-image revalidation.

The owner separately authorized narrow Gitleaks exclusions for historical
metadata. Each of 57 findings was verified as a Git blob OID on its exact
finding commit, yielding 29 exact source-path/OID pairs; six other findings
are two exact public response metadata lines. Three AND-scoped generic-api-key
entries preserve every other rule and path. Native Gitleaks 8.24.3, verified
against the official release checksum, accepts all 29 pairs and both headers
(exit 0, zero findings) and detects four synthetic credentials in the same
three files (exit 1), including an arbitrary 40-hex value under an approved
source-path key. Thirty affected Python owning tests pass. Real current CI,
the complete frozen producer, registry/readback, independent final acceptance
and native ADMIT remain required before closing #12474.

The next main integration retained `ce48486bbf742c2a0d135d43dff56b78b9080f05`,
tree `10fb6595f65fc9cfddf3c7c7dfe504f4d51e79f4`, including its organism mapping
change and removal of the unused Router development dependency. A new native
pack now has SHA256 `86995f918b30efa16931f99407f28368cfe5d529b130c48c9c1d53c1e9c209b1`;
again, native Linux lock generation changed only the existing alias SRI.
Native positive controls also cover the historical 29th OID and first-line
CRLF metadata; the positive/negative exits remain 0/1 with zero/four findings.

The reviewed source-ac307 archival candidates were then published and pulled
back by immutable identity: host
`sha256:2ef07e20ee5b6451f2386fdaa13d3ce72e411bbfae4053332e8e8dfa3575044e`
and managed `sha256:09176a12590763ea1adeb844bd325074e79b4edd94cfc43f1012a1f03fba75c3`
in `satorykono/bioetl-grafana-router7-canvas`. Complete registry exports verify
15,534/15,478 paths and the exact prepared rootfs/config identities; raw records
are preserved for both. This is archival candidate publication, not promotion
of the current main source. The existing Router workflow now has an explicit
owned immutable candidate input; its empty default still verifies declared
delivery. Candidate qualification retains all complete image checks and labels
its receipt separately. Fifteen Node controls and 58 CI-policy tests pass.
