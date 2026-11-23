______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-11-16'

______________________________________________________________________

# IUPHAR Target Classification

## Semantics baseline (RF-001)

Before changing rules or admitting enrich, use the RF-001 contract:

- Semantics: [`16-iuphar-target-classification-semantics.md`](../../04-reference/pipelines/chembl/16-iuphar-target-classification-semantics.md)
- Machine vocabulary: `src/iuphar_target_class/semantics.py`
- Baseline hashes: `data/iuphar_target_class/rf001/baseline_manifest.json`

`target_type` stays the ChEMBL object type; `iuphar_*`, `local_*`, and
`effective_*` remain separate layers. `source_unavailable` is not
`not_found`. `biological_accuracy_accepted` stays false unless proven.
Matched counts are not biological accuracy.

## Trigger

Use this runbook to validate an offline IUPHAR classification dependency,
run shadow acceptance, or migrate the shared `chembl.target` tables to the
additive 3.1.0 contract. The feature is configured on `chembl_target`; it has
no dedicated workflow or pipeline CLI flag.

## Impact

The production configuration remains `mode: "off"`. The historical dictionary
is an unqualified legacy source with unresolved classification disagreements.
Retrieving official export bytes and passing software tests does not approve a
snapshot's coverage or reference cases. Require the actual acquisition,
independent scope review, and executed acceptance artifacts below before
promotion. Historical reports and synthetic fixtures establish no biological
accuracy or reviewer approval.

The configuration applies to every writer of the same Silver/Gold target
tables: direct `chembl_target` runs and workflows `chembl_baseline`, `chembl_core`,
`chembl_reference_pack`, `chembl_target`, and
`chembl_target_protein_classification`. These writers must use one compatible
configuration and contract during a deployment.

| Mode | Business rows and hash policy | Required dependency |
| --- | --- | --- |
| `"off"` | Unchanged V30, contract 3.0.0 | None |
| `shadow` | Unchanged V30, contract 3.0.0; separate classification evidence | Pinned profile envelope and snapshot |
| `enrich` | V31, contract 3.1.0; nine additional nullable business columns enter the explicit hash scope | Admitted, publishable scoped snapshot and executed V2 reference acceptance; compatible physical tables |

The registry's current identity remains 3.0.0. Publishing the
[V31 contract](../../04-reference/contracts/gold/chembl_target_v3.1.json) does
not promote production or enable generic dual writing.

## Preconditions

- Work from the repository root using the native Windows interpreter
  `.\.venv-win\Scripts\python.exe`, or the prepared local interpreter on other
  platforms. The commands below use PowerShell.
- Preserve existing data, configuration, reports, and evidence. Leave `.env`
  files unchanged throughout this procedure.
- Keep the existing target eligibility filters. This integration does not
  expand the pipeline to protein complexes or change baseline cohort selection.
- For preparation, promotion, or rollback, stop and quiesce all writers listed above and
  hold the maintenance window until both tables and their configuration agree.
  The migration helper additionally refuses recognized managed writers; this
  does not replace the operator's check for other processes.

## Procedure

### Configure the pinned dependency

The canonical setting is under `pipeline` in
[`configs/entities/chembl/target.yaml`](../../../configs/entities/chembl/target.yaml):

```yaml
pipeline:
  target_classification:
    mode: "off"
```

Quote `"off"`: YAML 1.1 readers can interpret an unquoted `off` as a boolean,
which the strict configuration rejects.

For shadow validation, prepare a separately reviewed configuration with:

```yaml
pipeline:
  target_classification:
    mode: shadow
    snapshot_manifest: data/input/iuphar/APPROVED_BUNDLE/profile.json
    snapshot_manifest_sha256: "REPLACE_WITH_SHA256_OF_PROFILE_JSON_BYTES"
```

These are placeholders, not a runnable or approved configuration. Despite its
name, `snapshot_manifest` points to the **profile envelope**, not directly to
the snapshot manifest. A relative path is resolved from the repository/configs
root's parent. Its digest is the lowercase, 64-character SHA-256 of the exact
profile bytes. Calculate a file digest with:

```powershell
(Get-FileHash -Algorithm SHA256 'PATH_TO_PROFILE_JSON').Hash.ToLowerInvariant()
```

The profile has this structure; all references are relative to its directory,
must stay inside that directory, and bind exact bytes:

```json
{
  "artifact": "bioetl_iuphar_profile",
  "schema_version": 2,
  "snapshot": {"path": "snapshot.json", "sha256": "SNAPSHOT_SHA256"},
  "acceptance": null,
  "normalization_version": "bioetl-iuphar-input-v1",
  "rules_version": "plan-v1-r8",
  "classification_schema_version": "3.1.0"
}
```

New snapshots use artifact `bioetl_iuphar_snapshot`, schema version 2, and
format `gtopdb_target_species_payload_v2`. The official wide CSV can contain
multiple records for one public target ID and Human/Rat/Mouse annotation
columns. The builder retains the public ID and derives separately checked
species variants; it does not choose the first record or collapse taxa.
This export provides `annotation_capability: family_only`. The builder does
not manufacture a direct target type, and an available family can yield a
coarse direct class with annotation status `partial`. RF-005 keeps that
capability: subclasses and all intact `root_to_leaf` hierarchy paths are
persisted from the approved dictionary and merged multi-parent family graph
without claiming full direct-type coverage. See
[`data/iuphar_target_class/rf005/coverage_matrix.json`](../../data/iuphar_target_class/rf005/coverage_matrix.json)
and the path policy notes in
[16-iuphar-target-classification-semantics.md](../../04-reference/pipelines/chembl/16-iuphar-target-classification-semantics.md).

Supply a pinned `bioetl_iuphar_acquisition` receipt containing the release,
timezone-bearing retrieval time, source format, and every raw artifact's
relative path, HTTPS source URL, SHA-256, and byte count. Supply a separate
`bioetl_iuphar_coverage` receipt binding that acquisition, explicit included
IDs, species/family scope, exclusions with source-record rationales, and raw
row/public-target/species-variant counts. Its `bioetl_iuphar_scope_review`
artifact must independently bind the acquisition and exact scope digest.
The source-derived projection and audit are recomputed during loading;
manifest flags alone cannot establish admission.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.engineering.qa iuphar-snapshot-build `
  --acquisition 'PATH_TO_ACQUISITION_JSON' `
  --acquisition-sha256 'ACQUISITION_SHA256' `
  --coverage 'PATH_TO_REVIEWED_COVERAGE_JSON' `
  --coverage-sha256 'COVERAGE_SHA256' `
  --output-dir 'NEW_SHADOW_SNAPSHOT_BUNDLE_DIRECTORY'
```

The output includes the frozen sources/review, targets, projection audit,
snapshot, and a shadow profile with `acceptance: null`. Keep all files.
V1 snapshot/profile validation remains available for historical compatibility;
new enrich admission uses V2 source and acceptance contracts.

`admission_complete` means the declared, independently reviewed scope is
complete for admission. `complete` means global identity/absence coverage.
A family-only bounded snapshot can have `admission_complete: true` and
`complete: false`: unrepresented targets must retain `source_unavailable`,
not become negative matches. `enrich` requires admission completeness,
publication evidence, and the matching V2 acceptance receipt. Neither a
caller-supplied boolean nor an unverified provider version qualifies it.

Workflow dependency preflight pins and checks the target configuration and
profile before the first workflow step, including `chembl_baseline` assay
ingestion. It considers pending pipeline writers and declared target-mutating
transform steps at their actual destinations, including transform-only and
resumed execution. Already completed steps and dry runs do not count as
pending writes; dependency verification remains distinct from new-write
admission. Target preflight rechecks the pinned bytes and both actual writer
destinations before a backfill can clear target outputs. A V30 destination
blocks `enrich`; a V31 destination blocks `off`/`shadow`; partial or unrecognized
table schemas require recovery. Empty candidate destinations are allowed.
Destructive `backfill`/`rebuild` against an existing V31 table is rejected,
including limited campaigns. Rebuild into empty candidate destinations and
use the paired migration procedure to replace the canonical bundle.

### Interpret classification and evidence

| Column | Meaning |
| --- | --- |
| `iuphar_target_id` | Matched IUPHAR identity, separate from the ChEMBL target ID |
| `iuphar_class` | Direct class supported by the frozen IUPHAR payload |
| `iuphar_match_status` | Identity-resolution outcome |
| `iuphar_annotation_status` | Completeness of the provider's direct annotation |
| `local_class` | Separate local rule result |
| `effective_class`, `effective_source`, `decision_status` | Existing resolver decision and its source/status |
| `target_class_profile_sha256` | Exact profile identity used by this enriched row |

Local EC/L1/L2 inference does not fill `iuphar_class`. A direct annotation with
status `partial` can still support a coarse direct class; retain that class
and distinguish annotation completeness from identity resolution. Do not turn
an ambiguous, unavailable, or unsupported input into a fabricated direct class.

Evidence is stored under the configured data root:
`output/control/target_classification/<run_id>/`. Each batch/row directory
contains `classification.json`, `evidence.json`, `candidates.json`,
`components.json`, `diagnostics.json`, `metrics.json`, and a row manifest.
The completed run's `manifest.json` binds every artifact's SHA-256, the run,
profile, snapshot, mode, row identities, and row count. Conflicting retries are
rejected. The application publishes row evidence after successful row
finalization and completes the run manifest after data writes finish.

Check evidence IDs against their referenced records and frozen payload hashes.
Keep run/batch clocks and evidence paths outside business content hashing.
V31 hashes include the nine columns above; V30 hash scope remains unchanged.

### Freeze a canonical cohort and its evidence

Stage0 V2 assigns every copied material an explicit `cohort` or `evidence`
role. Executable source selection must equal the complete cohort set;
reference documents, raw inputs, and ledgers stay evidence. Every copy is
hash-checked, including evidence that is not an execution input. Provenance
claims may bind either role. The historical V1 publisher and reader retain
their original contract.

Export only a frozen normalized ChEMBL target Silver CSV or Arrow IPC stream
with schema tag `chembl.target.normalized_silver.v1`. Required fields are
`target_id`, `target_type`, `taxonomy_id`, `pref_name`, `organism`, and
`component_accessions`. Each row needs a unique `CHEMBL` target identity,
`SINGLE PROTEIN` type, and a confirmed canonical positive ASCII TaxID in
`taxonomy_id`. The exporter rejects missing TaxIDs, species names in that
field, guessed eligibility, importer-reserved fields, and pre-existing
classification output fields.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ops iuphar-target-cohort export `
  --source 'PATH_TO_FROZEN_NORMALIZED_TARGET_CSV' `
  --source-sha256 'RAW_SOURCE_SHA256' `
  --source-format chembl_target_silver_csv_v1 `
  --source-schema-version chembl.target.normalized_silver.v1 `
  --mapping-approval-reference 'ACTUAL_TECHNICAL_MAPPING_REFERENCE' `
  --environment 'ACTUAL_ENVIRONMENT' `
  --output-dir 'NEW_CONVERSION_DIRECTORY'
```

Use `chembl_target_silver_arrow_ipc_v1` for a frozen Arrow IPC stream. A
separately confirmed provider-ID column can be declared with
`--direct-iuphar-id-column`; a ChEMBL target ID must never be passed as that
column. The shared adapter projection produces `bioetl_target_kernel_csv_v1`
with stable row IDs `chembl.target:<target_id>` and canonical TaxID in the
kernel's `organism` field. The output preserves `raw-source.bin`, `cohort.csv`,
and `conversion-ledger.json` with separate raw/canonical hashes, byte counts,
row identities, and per-row hashes. Duplicate target IDs stop conversion and
leave a rejected diagnostic ledger; the exporter does not select one duplicate.
The technical mapping reference grants no biological or eligibility approval.

Create a Stage0 request JSON with `cohort_id`, `approval_reference`,
`environment`, and `materials`. Each material declares a workspace-relative
`source_path`, `source_sha256`, `role`, and `format_version`. Each cohort
material additionally needs `target_kind: "protein"` and
`conversion_ledger_source` naming a separately copied evidence material.
Copy the ledger and its exact raw source as evidence; additional review
documents may also be evidence. Both roles may appear in `provenance_claims`
using the existing claim contract.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ops iuphar-target-cohort stage0 `
  --request 'PATH_TO_REVIEWED_STAGE0_V2_REQUEST_JSON' `
  --repo-root 'D:/github/BioactivityDataAcquisition' `
  --output-dir 'NEW_STAGE0_OCCURRENCE_DIRECTORY'
```

Retain `manifest.json`, `cohort_manifest.json`, `conversion_ledgers.json`,
content checks, provenance map, stage report, and every copy. Stage0 verifies
ledger/raw/canonical byte bindings and row hashes. Its report explicitly
records no biological acceptance. Publish a separate occurrence when any
input changes; do not replace an earlier occurrence.

### Execute independent reference acceptance

1. Obtain a publishable snapshot with admitted reviewed scope and an admitted,
   frozen Stage0 V2 cohort. Freeze a schema-version-2
   `bioetl_iuphar_reference_cases` document with
   reviewer/approval references, environment, full source selection, expected
   row count, snapshot digest, and independently reviewed per-case outcomes.
   Each case needs source references with verified byte hashes. Do not derive
   expected labels from the classifier output under test.
   Pin the cohort manifest, conversion-ledger index, normalization/rules/schema
   versions, and the complete selected cohort sources. Every selected source
   declares `bioetl_target_kernel_csv_v1` and `target_kind: protein`.
2. Declare every mandatory reference category before execution:
   `direct_type`, `direct_family`, `partial_direct`, `ambiguous`, `unmatched`,
   `identity_conflict`, `taxonomy_boundary`, `local_vs_direct`, and
   `non_applicable`. Each category has disposition `real_reference`,
   `engineering_only`, or `out_of_scope`, case IDs, a rationale, and independent
   hash-pinned source references. Out-of-scope categories have no case IDs.
   A family-only snapshot cannot qualify direct-type cases by inventing a
   target type; explicitly record that limitation.
3. Supply `scope_declaration` with `kind: bounded_reviewed_reference`, a scope
   ID, actual approval reference, limitations, reviewed and unreviewed row IDs.
   These disjoint sets must account for the full cohort. Real cases require
   expected `match_status`, `matched_target_id`, `iuphar_class`,
   `iuphar_annotation_status`, and `decision_status`, including explicit nulls
   where appropriate. `local_vs_direct` additionally requires `local_class`,
   `effective_class`, and `effective_source`; `non_applicable` additionally
   requires `input_validation_status`. The producer verifies that declared
   scenarios actually occur. Engineering-only cases do not inflate real
   reviewed coverage. Keep expected labels and proof bytes frozen before the
   run; do not generate them from its results.
4. Run the actual `chembl_target` pipeline in isolated `shadow` destinations
   using that same snapshot.
   Preserve its completed evidence manifest and successful run report. A
   standalone kernel invocation does not prove pipeline integration.
5. Run the following command after replacing every uppercase placeholder with
   an approved value. Choose a new output directory; acceptance does not
   overwrite an earlier occurrence.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.engineering.qa iuphar-target-acceptance `
  --profile 'PATH_TO_SHADOW_PROFILE_JSON' `
  --profile-sha256 'PROFILE_SHA256' `
  --stage0-manifest 'PATH_TO_STAGE0_MANIFEST' `
  --expected-labels 'PATH_TO_REVIEWED_REFERENCE_CASES_JSON' `
  --expected-labels-sha256 'REFERENCE_CASES_SHA256' `
  --pipeline-proof 'PATH_TO_COMPLETED_PIPELINE_EVIDENCE_MANIFEST' `
  --pipeline-report 'PATH_TO_SUCCESSFUL_PIPELINE_RUN_REPORT' `
  --run-id 'NEW_ACCEPTANCE_RUN_ID' `
  --run-started-at 'FROZEN_ISO8601_TIMESTAMP' `
  --output-dir 'NEW_ACCEPTANCE_OUTPUT_DIRECTORY'
```

The command checks the full admitted cohort, reviewed cases, evidence
integrity, frozen-provenance permutation determinism, execution bounds, and the
matching successful pipeline occurrence. Exit 0 and receipt status `PASS`
qualify only that supplied scope. Receipt V2 records the category matrix,
reviewed/unreviewed IDs, pinned versions, and
`scientific_status: bounded_reference_cases_only`;
`biological_accuracy_accepted` remains false.
`BLOCKED_INPUT` or `FAIL` is not admission.

Receipt `artifact_references` binds actual local file URIs and exact hashes
for the Stage0 manifest, cohort manifest, ledger index and copied evidence,
expected labels, matching pipeline proof/report, and all six kernel outputs.
The pipeline evidence manifest also binds the completed row-store artifacts.
Keep the dependency closure, not just the receipt JSON. The current pipeline
report producer does not expose effective-config or run-manifest immutable
URI/hash references; preserve those artifacts separately using their recorded
run identities, rather than inferring a path from `manifest_id`.

For an enrich profile, replace `acceptance: null` with the relative path and
SHA-256 of the accepted receipt. This creates new profile bytes and a new
profile digest. The dependency is noncircular: the receipt binds the snapshot;
the final profile binds the snapshot and receipt. Re-pin the final profile's
digest before building enriched candidates.

### Prepare and promote complete physical tables

Build V31 Silver and Gold candidates at separate approved destinations from
the persisted complete old tables. The candidate builder does not refetch
provider records or run the ordinary limited pipeline. It preserves the
complete old target cohort independently in each layer, including Silver
targets removed from Gold by the final baseline reconciliation. A
`--limit 1000` smoke supplies no full-table migration proof.

Keep execution routing separate from deployment routing. An isolated shadow
execution uses its own configuration and empty destinations. The full
deployment entity YAML retains canonical sinks, filters, and business rules;
only its `pipeline.target_classification` section may change to the newly
pinned enrich profile. The migration loader resolves that YAML with the
actual configs root and settings and requires its destinations to equal the
canonical table paths. Candidate destinations come from the explicit plan.
Do not promote a YAML whose sinks point at temporary candidates.

Prepare a JSON migration plan outside the repository root. This example uses
placeholders deliberately; resolve the actual writer paths and replace them
before execution. Every path must be inside the existing approved workspace,
with no symlink/junction, nesting, overlap, or `.env` resource. The backup path
must not exist yet. Despite its name, `candidate_config` is the complete
**deployment** entity YAML to be promoted; `config` is the canonical entity
YAML. Neither file is the isolated shadow/build routing configuration.

```json
{
  "paths": {
    "workspace": "D:/github/BioactivityDataAcquisition",
    "silver": "ABSOLUTE_CANONICAL_TARGET_SILVER_PATH",
    "gold": "ABSOLUTE_CANONICAL_TARGET_GOLD_PATH",
    "assay": "ABSOLUTE_BASELINE_ASSAY_DELTA_PATH",
    "config": "D:/github/BioactivityDataAcquisition/configs/entities/chembl/target.yaml",
    "candidate_silver": "ABSOLUTE_CANDIDATE_TARGET_SILVER_PATH",
    "candidate_gold": "ABSOLUTE_CANDIDATE_TARGET_GOLD_PATH",
    "candidate_config": "ABSOLUTE_CANDIDATE_ENTITY_YAML_PATH",
    "backup": "ABSOLUTE_NEW_BACKUP_DIRECTORY"
  },
  "legacy_include_fields": ["REPLACE_WITH_THE_COMPLETE_FROZEN_V30_INCLUDE_LIST"]
}
```

Copy the full explicit V30 `hash_policy.hash_policy.include_fields` list from the canonical
target entity configuration into `legacy_include_fields`. Keep it frozen
through preparation, promotion, and recovery.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ops target-classification-migration freeze-inputs `
  --plan 'PATH_TO_APPROVED_PLAN_JSON' `
  --output 'NEW_FROZEN_INPUT_MANIFEST_JSON'
.\.venv-win\Scripts\python.exe -m scripts.ops target-classification-migration build-candidates `
  --plan 'PATH_TO_APPROVED_PLAN_JSON' `
  --input-manifest 'PATH_TO_FROZEN_INPUT_MANIFEST_JSON' `
  --input-manifest-sha256 'FROZEN_INPUT_MANIFEST_SHA256' `
  --output 'NEW_CANDIDATE_EVIDENCE_DIRECTORY' `
  --run-id 'NEW_CANDIDATE_BUILD_RUN_ID' `
  --run-started-at 'FROZEN_ISO8601_TIMESTAMP'
```

`freeze-inputs` records table IDs, versions, physical file hashes, complete
Silver and Gold target IDs, assay facts, and original configuration digest.
`build-candidates` requires those exact inputs still to exist. It classifies
every old Silver row with the admitted profile, computes V31 business hashes,
and uses the matching Silver projection for each old Gold target. Historical
Gold versions keep that current Silver projection when their saved business
fields would classify differently; validation compares those Gold rows with the
Silver projection. A relative `snapshot_manifest` is resolved from the approved
workspace, the same root used by the runtime loader and dependency collector.
It validates the full candidates and publishes a completed build manifest and
per-row classification evidence. Preserve the input manifest and build evidence.

Historical tables use the migration-only physical contract
`legacy_physical_target_v30_to_v31_v1`: candidates must contain exactly the old
physical columns plus the nine classification fields. Preserve every old value,
including technical metadata, except the recomputed `content_hash`. The validator
records known runtime metadata columns absent from the historical source rather
than inventing run provenance. For an absent nullable Gold `description`, only the
logical validation view supplies `None`; persisted columns remain unchanged.
Gold's existing four-column SCD envelope is validated separately, retaining its
datetime or ISO8601 text values. Present business and metadata fields and all nine
new fields remain validated. These bounded migration adaptations do not change
the schemas required for new runtime writes.

Rehearse promotion and recovery against separate complete copies. The production
CLI binds the active configuration and canonical destinations; use the composition
API `bind_target_rehearsal` for a copy rehearsal. Keep `paths.workspace` at the
approved repository. Put every mutable plan resource, a complete copied configs
tree (excluding `.env*` and `*.env`), candidate tables, evidence, and a new backup
directory inside one dedicated `reports/local/<occurrence>` directory. The old
copied target configuration must match the active configuration byte for byte.
Pass explicit `Settings(_env_file=None, test_mode=True, data_dir=...)` with its
data directory inside that occurrence, then resolve the binding:

```python
binding = bind_target_rehearsal(
    paths,
    rehearsal_root=occurrence,
    configs_root=occurrence / "configs",
    settings=settings,
)
```

Supply that binding as `deployment` to candidate construction, preparation, and
promotion. The real profile loader, receipt admission, physical destination
resolution, validation, backup, and recovery remain active. Pinned dependencies
may be read from the approved repository; migration resources may not overlap
active tables or configuration. Verify complete copied table/configuration byte
identity after rollback and unchanged canonical resources throughout the rehearsal.

Before the real `prepare`, stop and quiesce every canonical writer and hold the maintenance
window through backup, promotion, verification, or rollback. A stable freeze
does not itself prevent a later writer. Do not start preparation while a
pipeline or reconciliation transform can still mutate these resources.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ops target-classification-migration prepare --plan 'PATH_TO_APPROVED_PLAN_JSON'
.\.venv-win\Scripts\python.exe -m scripts.ops target-classification-migration promote --plan 'PATH_TO_APPROVED_PLAN_JSON'
```

`prepare` validates admission, strict V31 schemas, unique target IDs, unchanged
legacy business values and identities, V30/V31 hash recomputation, the complete original target
cohort separately in each layer, and inclusion of the non-null final baseline
assay target IDs in Gold. Gold may contain additional preserved target IDs;
Silver can retain targets removed from Gold
by the workflow's final reconciliation. Gold's
`description` alias is mapped back to Silver's `target_description` for the
legacy hash check. Every candidate Silver row is classified again against the
admitted snapshot; its nine new fields and the corresponding Gold projection
must agree with that result. It copies and hashes the entire physical old tables and
configuration, then writes `journal.json`.

`promote` rechecks canonical, candidate, and assay bytes and validation before
moving both candidates and the configuration into place. It journals each
move, retains originals, and restores already moved pairs on an activation
error. Keep the maintenance window open through verification.

## Verification

- Confirm the selected configuration, contract version, actual schema hash,
  normalization identity, and profile digest in the effective configuration
  and [run manifest](run-manifest-inspection.md).
- For shadow, verify unchanged V30 rows/hash scope plus complete separate
  evidence. For enrich, verify V31 on both tables, coherent profile values,
  completed evidence, full cohort preservation, and baseline FK closure.
- Inspect all executed receipt checks, category dispositions, bounded scope,
  source digests, output hashes,
  and matching successful integration report. Retain unresolved disagreements
  for owner review; a green software test is not reference-case approval.
- For replay, retain the exact profile, snapshot, payload, receipt, effective
  configuration, and run/workflow dependency artifacts. Replay pins their
  recorded identities and rejects changed bytes; it must not resolve a
  `latest` alias or substitute a newly available snapshot. Workflow resume
  retains the stored target configuration/dependency rather than taking the
  current default.

## Compliance

Keep production `"off"` until the admission and promotion procedure has actual
reviewed inputs. Use one contract for all shared-table writers, preserve
historical and recovery artifacts, and keep local inference separate from
direct IUPHAR evidence. Software contract fixtures cannot waive acceptance.

## Rollback

Keep all writers quiescent and use the same approved plan:

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ops target-classification-migration rollback --plan 'PATH_TO_APPROVED_PLAN_JSON'
```

Rollback restores both physical original tables and their original
configuration, preserving displaced candidates in the backup directory. It
verifies original bytes, journals each restored pair, and can retry a partial
restore only while those original bytes still match. Switching the mode to
`"off"` alone is insufficient. A Delta-version-only restore does not remove
the enriched physical schema. Do not clear the tables, delete backups, or
weaken the compatibility guard to bypass recovery.

## Post-incident

Record the original and final configuration digests, all writer identities,
profile/snapshot/receipt digests, run IDs, migration journal, full-cohort and FK
checks, and any recovery action. Preserve earlier reports and reference
decisions. Promote production only after actual inputs and all required
acceptance evidence are available and reviewed.

## Source owners

- [Profile and snapshot admission](../../../src/bioetl/infrastructure/adapters/iuphar/snapshot_loader.py)
- [Official snapshot builder](../../../src/bioetl/infrastructure/adapters/iuphar/snapshot_payload.py)
- [Canonical cohort exporter](../../../src/bioetl/infrastructure/adapters/iuphar/cohort_projection.py)
- [Stage0 V2 roles and immutable copies](../../../src/iuphar_target_class/stage0/v2.py)
- [Bounded reference coverage contract](../../../src/iuphar_target_class/reference_coverage.py)
- [Workflow/runtime dependency binding](../../../src/bioetl/composition/bootstrap/runtime/publication_vocab_init.py)
- [Schema and hash profile selection](../../../src/bioetl/infrastructure/config/target_classification_profile.py)
- [Evidence publication](../../../src/bioetl/infrastructure/adapters/iuphar/evidence_store.py)
- [Acceptance implementation](../../../src/iuphar_target_class/integration_acceptance.py)
- [Acceptance CLI](../../../scripts/engineering/qa/iuphar_target_acceptance.py)
- [Physical migration and journal](../../../src/bioetl/infrastructure/storage/target_classification_migration.py)
- [Full persisted-cohort candidate builder](../../../src/bioetl/infrastructure/storage/target_candidates.py)
- [Deployment configuration binding](../../../src/bioetl/composition/bootstrap/runtime/composite_runtime_management_bundle.py)
- [Physical migration CLI](../../../scripts/ops/target_classification_migration.py)
