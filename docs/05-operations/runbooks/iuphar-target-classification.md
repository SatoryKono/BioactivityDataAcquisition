______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-11-28'

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

## UniProt identifier roles (RF-002)

Primary object accessions (`component_accessions` → kernel `uniprot`) are
strict exact-channel anchors. Auxiliary `target_xref_uniprot_ids` project to
`uniprot_xref` and only produce diagnostics (`unknown_auxiliary_uniprot` /
`auxiliary_uniprot_divergence`); they must not force false `ambiguous`.
Proven overlaps become `uniprot_equivalent` (evidence only).

- Roles: [`17-iuphar-uniprot-identifier-roles.md`](../../04-reference/pipelines/chembl/17-iuphar-uniprot-identifier-roles.md)
- Machine contract: `src/iuphar_target_class/identifier_roles.py`
- Policy pin: `data/iuphar_target_class/rf002/matching_policy.json`
- Matching policy version: `rf002-uniprot-roles-2026-11-23` (legacy merged
  anchors do not qualify this policy; RF-008 admits independently)

## Effective-class policy `hgnc-uniprot-channel-ec-v1`

For single proteins, the policy keeps the HGNC and primary UniProt priority
and resolves a supported ion-channel/enzyme class conflict as `Ion Channel`.
An ion-channel candidate blocks EC inference. Distinct valid first EC levels
give `Enzyme.Multitarget`. A single EC level fills a missing effective class
from the EC category, including for proteins outside IUPHAR species coverage.
Partial EC codes count when their first level is valid. The effective source
records `channel_priority` or `ec_rule`, and provider identity, annotation
status and evidence remain available for review.

Select the policy with `iuphar-snapshot-build --matching-policy-version
hgnc-uniprot-channel-ec-v1`. Its profile requires its own RF-008 acceptance
before use in `enrich`.

## Effective-class policy `hgnc-uniprot-name-ec-keyword-v1`

This version uses a same-species HGNC or primary UniProt match first, then a
unique exact provider full name with compatible identifiers. Without a
resolved provider class, a valid EC code supplies the effective class.
Preliminary EC entries such as `3.1.26.n2` use the confirmed numeric levels.
With a valid EC, synonyms are excluded from matching and cannot block the EC
result. Without a valid EC, a unique same-species synonym can match when
known identifiers are compatible and the gene symbol or Gene ID corroborates
the match. The multi-category EC and ion-channel
precedence rules still apply.

If the identity and EC routes yield no result, standalone functional words
in the target name can assign a local effective class with
`effective_source=keyword_rule`. Conflicting keyword classes remain
unassigned, except for ion channel versus enzyme. This fallback can also
classify single proteins outside the IUPHAR species coverage. Keyword
evidence records the word and the input name.

Select this version with `--matching-policy-version
hgnc-uniprot-name-ec-keyword-v1` at build time. The resulting profile
requires its own RF-008 acceptance for `enrich`.

## Effective-class policy `hgnc-uniprot-name-ec-keyword-tf-v1`

This version adds a project-specific label for a target name identifying a
transcription factor. It fills an empty effective class with
`Receptor.Nuclear receptor` after the ranked identity, EC and existing
keyword rules. It applies to single proteins across species. Names describing
related proteins, including factor-binding proteins, proteases and complex
subunits, do not trigger the transcription-factor rule. The result records
`keyword_rule` as its effective source. This profile requires its own RF-008
acceptance for `enrich`.

## Effective-class policy `hgnc-uniprot-reviewed-target-class-v1`

This V31 policy requires a known taxon for direct identity. A unique same-species
HGNC or primary UniProt candidate takes precedence over text. Two incompatible
confirmed anchors retain `identity_conflict`. A unique compatible full name is
eligible when direct anchors provide no result. A corroborated synonym is used
only when no valid EC exists. A single EC category fills an empty class or
refines an EC-only generic `Enzyme`; distinct EC categories yield
`Enzyme.Multitarget`, with supported ion channels retaining priority.
Functional keywords can fill an empty class even when a direct IUPHAR ID
exists. The transcription-factor rule again applies only to empty classes.
Single proteins outside the snapshot's species can receive a local class.

Provide the independently reviewed JSON to the snapshot builder using
`--matching-policy-version hgnc-uniprot-reviewed-target-class-v1`,
`--reviewed-inputs`, and `--reviewed-inputs-sha256`. The document has artifact
`bioetl_iuphar_reviewed_inputs` and `schema_version: 1`:

- `supplemental_source_sha256` maps the names of the reviewed CSV sources to
  their digests. When supplying supplemental rows, supply both original CSVs
  in `--supplemental-csv-dir`. The builder copies the bytes into the snapshot
  and the loader rechecks them against the review. `targets.json` and the
  official projection audit remain reproducible from official acquisition.
- `supplemental_targets` contains independently reviewed provider target/species
  payloads. Each requires a `reviewReference` and a primary UniProt or human
  HGNC anchor. Official variants and existing official anchors take priority.
- `local_classes` contains approved rows with `target_chembl_id`, `taxon`,
  `primary_uniprot`, `effective_class`, `origin` (`manual_review` or
  `ortholog`), and `review_reference`. The exact three-field identity must
  match. This last stage fills an empty class without creating a direct
  IUPHAR identity. Rows with conflicting strong identifiers stay in review.
  Keep orthology evidence tied to both proteins and species in the cited record.

The classifier emits the evidence for each applied assignment. This policy
requires its own executed RF-008 acceptance and the pinned reviewed inputs for
`enrich`.

## Trigger

Use this runbook to validate an offline IUPHAR classification dependency,
run shadow acceptance, or migrate the shared `chembl.target` tables to the
additive 3.1.0 contract. The feature is configured on `chembl_target`; it has
no dedicated workflow or pipeline CLI flag.

## Impact

Ordinary target runs load the checked-in RF-008 profile in `enrich` mode with
physical table contract `3.1.0`. Direct runs, workflows and the composite
post-join stage verify the pinned dependency before writing Silver or Gold.
Exact replay restores the mode and inputs recorded for the parent run.
The historical dictionary
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
| `"off"` | Historical replay of V30, contract 3.0.0 | Parent configuration |
| `shadow` | Unchanged V30, contract 3.0.0; separate classification evidence | Pinned profile envelope and snapshot |
| `enrich` | V31, contract 3.1.0, unless `table_contract` explicitly selects `3.2.0`; nine additional nullable business columns enter the explicit hash scope. `3.2.0` also persists source type, completeness, family ids, subclasses, structured paths, local status and rule ids, effective subclasses, conflict codes and evidence refs | Admitted, publishable scoped snapshot and executed V2 reference acceptance; compatible physical tables |

The registry's current identity remains 3.0.0. Publishing the
[V31 contract](../../04-reference/contracts/gold/chembl_target_v3.1.json) does
not promote production or enable generic dual writing. Physical contract
`3.2.0` is selected only by an explicit `table_contract`. It keeps the nine
V31 columns and adds canonical JSON detail. Computational
`classification_schema_version` stays on the loaded profile and may remain
`3.1.0`. Existing V30 and V31 tables are not migrated by selecting `3.2.0`.
`off` and `shadow` reject `3.1.0` and `3.2.0`. `enrich` rejects `3.0.0`.

## Delivery boundaries

These boundaries match the wired code. A green local test, a shadow
configuration, and an enrich configuration are different outcomes. An enrich
configuration plus an isolated run does not migrate the canonical V30 tables.
Promotion is only the migration procedure below.

### Base `chembl_target` and a composite target

Classification runs inside the `chembl_target` transformer, on the business
projection that transformer builds from the ChEMBL target record: `target_id`,
`target_type`, `taxonomy_id`, `organism`, `pref_name`, component accessions,
UniProt cross-references, EC numbers, and protein/gene synonyms. `shadow`
returns that business row unchanged. `enrich` merges the nine projection
fields into it. `"off"` does not bind a classifier.

With an enabled profile, `composite_target` also classifies after its dependency
joins, using the pinned workflow configuration when present. Historical replay
without a saved target classification configuration leaves the post-join
classifier disabled. A composite target
record can hold fields the standalone projection never sees. The kernel reads
`gene_symbol` and `gene_id` only when they are already on the business row.
The `chembl_target` extractor leaves these fields and `keywords`, `predicted_l1`,
and `predicted_l2` unset.

The kernel primary UniProt channel uses `component_accessions` and joined
`uniprot_accession`. Auxiliary `target_xref_uniprot_ids` remain diagnostic;
overlaps with primary accessions are recorded as equivalent evidence.

`chembl_target_protein_classification` is a different pipeline. It is not this
IUPHAR classifier. Workflows that write the same Silver/Gold target tables
still share the one `chembl_target` configuration.

### Stage signs and statuses

Eligibility failures stop the affected row before classification. The reasons are
`unsupported_target_type` (any type other than `SINGLE PROTEIN`),
`invalid_taxonomy_id`, `unsupported_taxon`,
`missing_taxonomy_for_known_organism`, and `taxonomy_name_conflict`. Those
rows are `not_applicable` and do not receive a direct class.

`unsupported_taxon` is an eligibility failure for the legacy and anchor-only
policies. The channel-EC policy can admit an out-of-coverage single protein
with a valid EC; ranked policies can also admit an unambiguous name keyword.
For these admitted rows, provider matching remains `source_unavailable` with
an `unsupported_taxon` diagnostic, while `effective_class` may be assigned by
`ec_rule` or `keyword_rule`. Other eligibility failures still stop the row.

Match status is `matched`, `ambiguous`, `not_found`, `source_unavailable`,
`insufficient_input`, `identity_conflict`, or `contract_error`.

For matching policy `hgnc-primary-uniprot-priority-v1`, an unambiguous
same-species HGNC or primary UniProt hit confirms identity. Name and synonym
hits remain in candidate evidence and cannot veto that result. Disjoint HGNC
and primary UniProt hits produce `identity_conflict`. HGNC is a direct
identifier only for human targets. This policy is opt-in through
`iuphar-snapshot-build --matching-policy-version` and requires its own
acceptance receipt before use in `enrich`.

Annotation status is `available`, `partial`, `unmapped_type`, `conflicting`,
or `not_available`. A `partial` annotation can still carry a coarse direct
class. Local inference does not fill `iuphar_class`.

The wired local policy publishes EC, L1/L2, and free-text rules. Class support
from EC is attached only for rules whose family is `ec_class` and whose input
condition is `ec_category=<n>`. The standard EC rules use family `ec`, so they
do not supply `local_class`. Keyword support requires family `annotation` and
an exact `keyword_id=` condition; the standard policy has no such rule. Free
text, including the substrings kinase, channel, and zinc finger, stays a
manual-review candidate. L1/L2 values on a kernel row are passed with unknown
provenance, so they stay candidates and do not assign `local_class`.

Local status from the wired assembler is `supported`, `not_supported`, or
`conflicting`. The decision table also accepts `candidate_only`.

Decision status is `resolved` or `requires_review`. `contract_error` is a
conflict code, not a third decision status.

Batch status is `empty`, `rejected`, or `processed`.

An acceptance receipt status is `PASS`, `FAIL`, or `BLOCKED_INPUT`. A check
that did not run stays `NOT_RUN`. `PASS` qualifies only the supplied scope.
`biological_accuracy_accepted` stays false. A V2 receipt records
`scientific_status: bounded_reference_cases_only`.

Stage-5 comparison with M is measured only when the stage-0 reference contains
M rows. An empty M set returns `measured: false` and does not invent counts.
That comparison is not biological acceptance. Policy gold cases remain
unconfirmed.

### Snapshot, export, and API key

New snapshots use `gtopdb_target_species_payload_v2` and
`annotation_capability: family_only`. The builder does not invent a direct
target type. `admission_complete: true` with `complete: false` is a bounded
snapshot: targets outside the reviewed scope stay `source_unavailable`, not
negative matches.

Hierarchy paths and subclass fields stay on the kernel result and in evidence
`classification.json`. The nine V31 business columns do not carry them.
Standard table export, including XLSX, writes the persisted table columns. It
does not reconstruct kernel paths that were not stored on the row. An enrich
table is required before those nine columns exist to export.

Shadow, enrich, acceptance, and migration read a pinned local snapshot.
Cohort export reads a frozen normalized ChEMBL target Silver file and does
not require that snapshot. None of these steps call the Guide to Pharmacology
API or require `GTP-API-Key`. The optional HTTP adapter omits that header when no key is
configured. The stage-1 policy records `api_key_required` as a documentary
note; it does not block stages 0–3. Do not add a key to the repository or to
an `.env` file for this procedure.

### Separated verification files

`iuphar-target-acceptance` writes `acceptance.json` and three siblings. Each
file is created only when that name is absent. A later run uses a new output
directory. None of the three copies another file's status:

| File | Contents |
| --- | --- |
| `classification-verification.json` | Stage-0 admission, reference cases, evidence integrity, and semantic determinism, with the run, profile, and snapshot bindings |
| `m-parity-report.json` | Stage-5 comparison with M. This command supplies no M rows, so `measured` stays false |
| `proof-verification.json` | Pipeline-integration status and proof/report digests. `ci.status` stays `NOT_RUN` unless a separate CI receipt names the head SHA. A local exit code is not that receipt |

Exit 0 still means the acceptance receipt status is `PASS`. It does not mean
CI ran, and it does not mean biological accuracy was accepted.

## Preconditions

- Work from the repository root using the native Windows interpreter
  `.\.venv-win\Scripts\python.exe`, or the prepared local interpreter on other
  platforms. The commands below use PowerShell.
- Preserve existing data, configuration, reports, and evidence. Leave `.env`
  files unchanged throughout this procedure. No API key is required.
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
    mode: enrich
    table_contract: "3.1.0"
    snapshot_manifest: configs/reference/iuphar/2026.3.1/profile.json
    snapshot_manifest_sha256: "b02152d8cce606caa43915f9039c2275b99a098861e52acf47643a128640dd15"
```

The profile directory includes the acceptance receipt, snapshot and pinned input
files used by the runtime. Git preserves their exact bytes across checkouts.

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
  "rules_version": "local-rules-2026.11.23",
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
[`data/iuphar_target_class/rf005/coverage_matrix.json`](../../../data/iuphar_target_class/rf005/coverage_matrix.json)
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
Subclass lists and hierarchy paths are not part of those nine columns.

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

#### Independent reference for the reviewed V31 policy

The 2026-11-27 independent review froze GtoPdb 2026.3.1 at 3,390 source
records for 3,304 distinct IDs. The admitted scope contains 3,154 IDs and
9,057 species variants. The review records 150 exclusions and leaves
`allows_not_found` false. Official annotations retain precedence.

The only supplemental direct anchor is human UniProt `P35613` for existing
official target `3127` (`CHEMBL3580492`, family `852`,
`Other Protein Target`). The reviewer confirmed this mapping against both
legacy CSVs and the official release. For bovine `CHEMBL4471` (`P00735`),
the class `Enzyme.Hydrolase` has separate orthology and bovine EC evidence.
The human ortholog `P00734` supports the recorded relationship. The bovine
direct IUPHAR ID stays null.

The admitted register has 1,730 explicitly approved manual rows, including
21 approved cluster rows. The 728 diagnostic cluster proposals are excluded.
The preliminary `ZNF664` entry for `CHEMBL4105757` remains excluded. The
review verified the decisions and exact keys in the frozen Gold data.

The 1,000-row shadow cohort was selected from retained Bronze and includes
all 64 historical IUPHAR ID cases, the orthology case, and the supplemental
anchor. Source precedence, label definitions, and reviewed/unreviewed row
membership belong to the frozen independent reference. A separate byte-pinned
comparison verified the 107 shadow rows that used the manual fallback
against the approved identity keys, classes, and evidence references. All
107 had a null direct IUPHAR ID.

| Input or proof | SHA-256 |
| --- | --- |
| Raw official CSV | `9e91ae4eed1e147f0c5b01dd2e0645c2d57edb39442114d3128c70232b0d39fb` |
| `_IUPHAR_target.csv` | `4756ff664c195aa5b54031d4403fe8eed8a144abfe9a6c3882978d1ec445b440` |
| `_IUPHAR_family.csv` | `3d56abada7f06068af153eca88e3b0d9fc04755ba319fd2d9acc00033875ecc3` |
| Reviewed scope | `b5b06e9679bf776dc3ae222ffa57df8661d11f31ab8baaf4c51e671f0a95fc6e` |
| Admitted reviewed inputs | `18ebd722d13b7bee3db3397d356d9f414276e917ec87a8ef8a2cfe37a3b5f6a1` |
| Independent evidence | `0e40ee4c6368b6555ebe8c35b3ed0e00ae1f3f3017c9daf9dc9a5ac5ce6fc516` |
| Stage0 V2 manifest | `2d877df31e6cd0ecd65efa323cd7d7ef2455fd3abc1d195dfaf9879172dd34f1` |
| Frozen expected labels | `9cb232b8d11084b2533ecf2215648a00e1cc5306f9cb615d3759c1a848720798` |
| Shadow profile | `abf6442c15d3311ae7570f97a7c915001f5ed77a6c9d082b22930ef43053d5b8` |
| Shadow proof | `61493626a053e0ad6c12e98a4f69d9b4636fe887c82a20c42a37a0b148c9089a` |
| Manual provenance comparison | `e153ab0c08db6fadda5886c4764edcc76ea6da323ead8fc7dad994cc25bce333` |
| Snapshot manifest | `2dcfde4b7790845383781b79e540b52ede0abf01def04a53cf952fd2c7bc0f1e` |
| RF-008 V2 receipt | `d4ce8e3ee3a4803d09902ce1658e2f0213100fcf546e57e5ef3bac953ba2b1da` |
| Enrich profile with the required receipt | `b02152d8cce606caa43915f9039c2275b99a098861e52acf47643a128640dd15` |

Shadow run `666e51a7-229f-5dca-9270-d835243301cb` completed on
`9c0aef926ad25a0c84fe48011829e413b4d24c2a`. RF-008 run
`429c4aed-51ff-42d6-af51-321a44f1fdd3` returned `PASS` on
`c9debf63adff9e0d62cb149189b1a1915822df00`. The producer verified
all 66 independent cases, including 64/64 historical IDs and their classes,
as well as evidence integrity, pipeline integration and deterministic output.
The final profile loaded with `require_acceptance=True`. The receipt records
`scientific_status: bounded_reference_cases_only` and
`biological_accuracy_accepted: false`. The separate
`proof-verification.json` records `ci.status: NOT_RUN` for this local execution.

The receipt and final profile are stored under
`reports/local/iuphar-13408-admission-20261127/rf008-429c4aed-51ff-42d6-af51-321a44f1fdd3/`
on the rehearsal host. Retain the referenced Stage0, labels, and shadow
artifacts at their pinned locations in the parent occurrence. This receipt
qualifies the profile for the complete V31 copy rehearsal.

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
  "source_profile": "V30",
  "destination_profile": "V31",
  "legacy_include_fields": ["REPLACE_WITH_THE_COMPLETE_FROZEN_V30_INCLUDE_LIST"]
}
```

Copy the full explicit V30 `hash_policy.hash_policy.include_fields` list from the canonical
target entity configuration into `legacy_include_fields`. Keep it frozen
through preparation, promotion, and recovery. `source_profile` and
`destination_profile` are required. The executable pair is `V30` → `V31`
(contracts `3.0.0` → `3.1.0`). `V30`/`V31` → `V32` (contract `3.2.0`) is
declared and rejected until that field contract is installed; enrich mode does
not select it. Canonical `promote` also requires `"cutover_authority": "RF-013"`.
Copy rehearsal does not use that authority and does not switch the active tables.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ops target-classification-migration freeze-inputs `
  --plan 'PATH_TO_APPROVED_PLAN_JSON' `
  --output 'NEW_FROZEN_INPUT_MANIFEST_JSON' `
  --restoration-manifest 'PATH_TO_VALIDATED_FK_RESTORATION_MANIFEST'
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
When assay references targets absent from current Gold, pass the validated
`--restoration-manifest`. The same flag is required again on `prepare`.
`build-candidates` and `promote` reuse the frozen input and the prepare journal.
`build-candidates` requires those exact inputs still to exist. It classifies
every old Silver row with the admitted profile, computes V31 business hashes,
and uses the matching Silver projection for each old Gold target. Historical
Gold versions keep that current Silver projection when their saved business
fields would classify differently; validation compares those Gold rows with the
Silver projection. A relative `snapshot_manifest` is resolved from the approved
workspace, the same root used by the runtime loader and dependency collector.
It validates the full candidates and publishes a completed build manifest and
per-row classification evidence. Preserve the input manifest and build evidence.

#### RF-013 candidate validation on 2026-11-25

The isolated V30 → V31 candidate build processed every row in the frozen
shared target snapshot and added 37 verified targets referenced by assay Gold.
Silver grew from 1,000 to 1,037 rows and Gold from 922 to 959. The unchanged
assay Gold contained 983 rows and had zero unresolved target references
against the candidate. Readback confirmed the nine classification fields
and the admitted profile on every candidate row. The shared tables and
canonical configuration passed the before-and-after identity checks.

| Local evidence | SHA-256 |
| --- | --- |
| Frozen V30 inputs | `2f9ec88a5cf07279a2ad6c40e5b73063e4b496065273b3d75a66e0212436e22e` |
| Validated FK restoration | `c638ee9856c60ea1953ed66f4af3d4abc27f4d6b8a750850e99bf9c75f1fa1e7` |
| V31 candidate build | `c8e84e96ae265a63f0f37f407c8f8834fcfdf3b06647febfbf71cf22d078308d` |
| Classification evidence | `974a5682bd6563aed16ed5da434aefb3850d24ca4acccfac42e87f662ca5929e` |
| Admitted profile | `2d96b292124aa14aa47fa60c7bbdf2f5d04003a1998a8d004383e50a0c059aa3` |

Candidate run `845a0367-d099-46aa-a5a0-62df4e8cdfcc` supplies the inputs for the copy rehearsal.
Rehearsal and production deployment each need their own evidence.

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

To refresh the policy on existing V31 tables, specify `source_profile: V31`
and `destination_profile: V31` in the plan. Freeze and validate both current
cohorts and their existing V31 hashes. Build each candidate from a complete copy
of its source table, appending one Delta commit that recalculates the
classification fields and content hashes for Silver and current Gold rows.
Closed Gold SCD versions retain their original values, and earlier Delta
versions remain readable. The refresh preserves the schema, target identities,
and foreign-key closure under physical contract
`existing_physical_target_v31_to_v31_v1`. Use a V31 `enrich` candidate config
bound to the new profile and its accepted RF-008 receipt. Gate the refresh with
`contour-report --require-ready` while the canonical tables stay `enrich`:
`READY` requires the live `enrich` mode and a candidate config separate from
the canonical one.

Before preparing a V31 refresh, verify the current writer configuration and
the stored profile independently:

1. Resolve the shared target configuration for standalone, workflow, and
   post-join composite writers. Record the config path, config SHA-256, mode,
   table contract, profile SHA-256, and destination paths. Record historically
   pinned workflow dependencies separately.
2. Read both target Delta tables and assay Gold. Record the Delta versions,
   distinct current target IDs, closed Gold rows, rows with no effective
   class, and orphan assay references. Compare the profile digest on every
   current target row with the final enrich profile envelope. Verify the RF-008
   receipt using the envelope's `acceptance` path and SHA-256 and the snapshot
   shared with the accepted shadow profile.
3. If the canonical configuration resolves to `off` while both tables are
   V31, pause target writers. On isolated copies, validate a separate
   `enrich` configuration pinned to the accepted profile already stored in
   the tables. Verify profile loading, non-destructive writer preflight,
   and the V31 guard for destructive workflow defaults using the copy
   verification procedure below. Obtain change
   authorization before restoring that binding on the shared contour.
4. Recheck the effective binding and current table digests after restoration.
   A standard `backfill` remains rejected for existing V31 tables. Keep the
   new profile in its own candidate configuration until the refresh reaches
   `READY`.

#### Verify the restored baseline binding on copies

Use the isolated config and Delta copies described below. Set the copied
`entities/chembl/target.yaml` to `enrich`, table contract `3.1.0`, and the
path and SHA-256 of the previously accepted profile. In `incremental-workflows/`
under the occurrence, copy the five workflow files from the copied `configs/`
tree and set their `workflow.defaults.run_options.run_type` to `incremental`. Use the
project Python from the checkout root. Save this snippet within the occurrence
and set its occurrence path before running it. It changes only the config
loader's root for the preflight calls and writes `restore-preflight.json`.

```python
from functools import partial
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch

from bioetl.composition.bootstrap.assembly import storage
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config_from_root
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.config.workflow_config_api import load_workflow_config

occurrence = Path("reports/local/<occurrence>").resolve()
configs = occurrence / "configs"
settings = Settings(_env_file=None, test_mode=True, data_dir=occurrence / "data")
load_pipeline = partial(load_pipeline_config_from_root, configs_root=configs)
target = storage.hydrate_target_runtime_config(load_pipeline("chembl_target"))
profile = storage.load_target_runtime_profile(target, require_new_admission=True)
assert profile is not None and profile.acceptance_sha256 is not None
report = {
    "config_sha256": sha256((configs / "entities/chembl/target.yaml").read_bytes()).hexdigest(),
    "profile_sha256": profile.profile_sha256,
    "receipt_sha256": profile.acceptance_sha256,
    "workflows": {},
}
names = (
    "chembl_baseline", "chembl_core", "chembl_reference_pack", "chembl_target",
    "chembl_target_protein_classification",
)
with patch.object(storage, "load_pipeline_config", load_pipeline):
    for name in names:
        workflow = load_workflow_config(name, configs_root=configs)
        try:
            storage.preflight_workflow_target_dependencies(workflow, {}, settings=settings)
        except ValueError as exc:
            if "V31 target requires staged complete-cohort migration" not in str(exc):
                raise
        else:
            raise RuntimeError(f"{name} admitted a destructive run")
        incremental = load_workflow_config(name, config_dir=occurrence / "incremental-workflows")
        binding = storage.preflight_workflow_target_dependencies(incremental, {}, settings=settings)
        assert binding
        assert storage.preflight_workflow_target_dependencies(
            incremental, binding, settings=settings
        ) == binding
        report["workflows"][name] = {"incremental": "PASS", "backfill_guard": "PASS"}
with (occurrence / "restore-preflight.json").open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2)
print(json.dumps(report, indent=2))
```

On 2026-11-27 all five incremental preflights and their pinned replays passed.
All five backfill defaults were blocked by the V31 guard. The report is stored
at `reports/local/iuphar-13406-baseline-20261127/restore-preflight.json`.

| Verified byte identity | SHA-256 |
| --- | --- |
| Copied `enrich` target config | `8726685545fa80840b9b1db8a75447d658f028c5bf75b01fda4c054700a41a5b` |
| Final baseline profile | `2d96b292124aa14aa47fa60c7bbdf2f5d04003a1998a8d004383e50a0c059aa3` |
| Baseline RF-008 receipt | `64a3d6c22fb80630e188bb0bab240d0906b129f4f466a2ac31670374589df7c3` |
| Preflight report | `d906570024a9a1d1e0804ee8f5dfa1bbfb387330c96e7f4b927a71781786c625` |

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

#### RF-013 promotion and rollback rehearsal on 2026-11-25

The rehearsal promoted full copies of the frozen V30 inputs and the validated
V31 candidate from the preceding build. Physical readback measured 1,037
Silver rows, 959 Gold rows, and zero unresolved target references from the
983 assay Gold rows. Every target row carried the admitted profile.

The native rollback resumed after a Windows file-sharing error while replacing
the journal and reached `rolled_back`. The restored target Silver, target Gold,
and configuration matched the original bytes. Assay Gold stayed in place and
its file digests matched before and after. Original backups and displaced V31
copies were retained. The shared configuration and tables matched their
pre-rehearsal bytes throughout.

| Local evidence | SHA-256 |
| --- | --- |
| Rehearsal summary | `7fd62157baf13fdde0b67fcb53966ad1972e789eebf6831b86fb30079a2ae298` |
| Final rollback journal | `7b61b4e8f6bc0999a7084da13d6593abc18d4de7e0750e0f80fa17d02aed95bf` |
| `contour-report --require-ready` result | `fe8377e164e612fa509d9ed496f7171b71a90591e53404bfa85b852f99baa9b8` |

The contour returned `READY` with the canonical mode still `off`. It admitted
the bounded RF-008 receipt and recorded live readback as `NOT_RUN`.
The rehearsal report used the passing PR Gate for the candidate build at
`b682ec32bc86c4c960c30a9731ef6b77ac6a174f` (PR #13389). Refresh the CI
attestation with the accepted rehearsal PR head before cutover.

Before the real `prepare`, stop and quiesce every canonical writer and hold the maintenance
window through backup, promotion, verification, or rollback. A stable freeze
does not itself prevent a later writer. Do not start preparation while a
pipeline or reconciliation transform can still mutate these resources.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ops target-classification-migration prepare `
  --plan 'PATH_TO_APPROVED_PLAN_JSON' `
  --restoration-manifest 'PATH_TO_VALIDATED_FK_RESTORATION_MANIFEST'
.\.venv-win\Scripts\python.exe -m scripts.ops target-classification-migration promote --plan 'PATH_TO_APPROVED_PLAN_JSON'
```

For a V31 policy refresh (`source_profile: V31`, `destination_profile: V31`),
run `prepare` without `--restoration-manifest`. `validate_target_candidate`
requires contract 3.1.0 and unchanged cohorts for a refresh plan and rejects
any restoration manifest.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ops target-classification-migration prepare `
  --plan 'PATH_TO_APPROVED_V31_REFRESH_PLAN_JSON'
.\.venv-win\Scripts\python.exe -m scripts.ops target-classification-migration promote --plan 'PATH_TO_APPROVED_V31_REFRESH_PLAN_JSON'
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
must agree with that result. For a V31 refresh, this projection check covers
current Gold rows. The validator compares closed Gold rows with their originals.
Preparation copies and hashes the entire physical old tables and configuration,
then writes `journal.json`.

`promote` rechecks canonical, candidate, and assay bytes and validation before
moving both candidates and the configuration into place. It journals each
move, retains originals, and restores already moved pairs on an activation
error. Keep the maintenance window open through verification.

#### RF-013 shared-table cutover on 2026-11-25

The local shared `chembl.target` Silver and Gold tables and their active
entity configuration were cut over at 11:47 UTC. The active mode is
`enrich`, with effective table contract 3.1.0 and profile
`2d96b292124aa14aa47fa60c7bbdf2f5d04003a1998a8d004383e50a0c059aa3`.
Both target tables were read back at Delta version 0. Silver had 1,037 rows,
Gold had 959 rows, and there were zero unresolved target references from the
983 unchanged assay Gold rows. The original V30 target tables and entity
configuration were verified in the backup. This occurrence uses a local
pinned dependency and deployment configuration.

| Local evidence | SHA-256 |
| --- | --- |
| Cutover summary | `69b51fa5cdfe1bcca6d3da42db2163d1c6a78fb0e2bd3166108a7628f1b3f279` |
| Promotion journal | `e912c12b637e443cc2d04f4f663d634adfcd519b85a827ed9aa869b3b4810b8b` |
| Ready evidence for PR #13390 at `bec891d8ce017ee8001e854320eccb3d245ff537` | `e7199b77e379f4a3fb520c3c9189c0ab7ad273e72cb6f489d05b982758d3c38e` |

For a post-cutover workflow on these tables, select `--run-type incremental`
explicitly. The checked-in workflow default selects backfill. Record the
post-cutover run and readback evidence before claiming `LIVE_ACCEPTED`.

### Record main-contour acceptance

Shadow, the isolated `--limit 1000` enrich, composite enrich, migration, and
live readback are separate statuses. A passing smoke does not prove the full
cohort. `biological_accuracy_accepted` stays false for a bounded RF-008
reference; a matched count must not be recorded as biological qualification.
For V30 → V31, keep the canonical entity document in `mode: "off"` until
`promotion_decision` is `READY`. For V31 → V31, verify that the canonical
configuration resolves to `enrich` with the accepted profile stored in the
current rows and use a separate candidate configuration. After `READY`,
`promote` runs in a window with no writers. `LIVE_ACCEPTED`
requires that promotion plus a readback of the next ordinary run. If a gate
fails after promotion, the command exits 1 with `rollback_required: true`;
restore with the rollback command above. Do not switch the mode to `"off"`
instead of restoring the tables.

Write the evidence JSON outside the committed tree. Point the command at the
actual discrepancy report, independent expectations, shadow business table,
shadow classification artifact, enrich table, repeat table, XLSX, isolated
Silver/Gold, main-contour Silver/Gold, and assay inputs. `--shadow-table` is
the unchanged V30 business cohort. `--shadow-classification` supplies the
status distributions; the business table does not. `--table`,
`--isolated-silver`, and `--isolated-gold` are the `--limit 1000` enrich
cohort. `--silver` and `--gold` are only the later main-contour readback. The
command recomputes hashes, status distributions, XLSX round-trip, historical
columns, current assay FK closure, and the canonical config digest. A file is
identified by its byte SHA-256. A Delta directory is identified by the SHA-256
of its current business-field projection, and a pinned hash is not accepted
when that identity was not measured. Every current enrich, Silver, and Gold
row must carry the claimed `target_class_profile_sha256`; a digest that is
only well formed does not confirm the classifier that wrote the rows. Current
rows of `--silver` and `--gold` are checked against
`migration.effective_profile_sha256`. Those live observations stay separate
from the isolated `--limit 1000` profile values. Current
rows are those with a missing or true `_is_current`. A CSV cell `False`,
`false`, or `0` is closed before that check. Closed versions do not close an
assay FK. Live readback compares each current Gold target with the current
Silver row of the same id. Two current rows of one id fail that readback.
Both rows must contain every classification field; a missing field is not a
null match. The comparison does not use the `--limit 1000` smoke table, and
the smoke hashes are not taken from the main-contour tables. A standard XLSX that carries
`_bioetl_export_manifest` is restored before the historical-column check, so
text split across cells is joined. The command does not promote, edit
configuration, or replace an existing report path.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ops target-classification-migration contour-report `
  --evidence 'PATH_TO_CONTOUR_EVIDENCE_JSON' `
  --discrepancy-report 'PATH_TO_DISCREPANCY_REPORT' `
  --expectations 'PATH_TO_INDEPENDENT_EXPECTATIONS' `
  --shadow-table 'PATH_TO_SHADOW_BUSINESS_TABLE' `
  --shadow-classification 'PATH_TO_SHADOW_CLASSIFICATION_TABLE' `
  --table 'PATH_TO_ENRICH_TABLE' `
  --repeat-table 'PATH_TO_REPEAT_ENRICH_TABLE' `
  --xlsx 'PATH_TO_STANDARD_XLSX' `
  --isolated-silver 'PATH_TO_ISOLATED_SILVER' `
  --isolated-gold 'PATH_TO_ISOLATED_GOLD' `
  --silver 'PATH_TO_MAIN_SILVER' `
  --gold 'PATH_TO_MAIN_GOLD' `
  --assay 'PATH_TO_ASSAY_TABLE' `
  --output 'NEW_CONTOUR_REPORT_JSON' `
  --require-ready
```

On Linux or WSL, use the prepared interpreter from the repository root. The
evidence document uses `schema_version`
`bioetl_iuphar_main_contour_evidence_v1`. Every key below is required; a
not-run phase still uses these objects. `local` and `ci` stay `NOT_RUN` until
their own evidence hash or 40-character commit SHA is supplied. Composite
acceptance stays `BLOCKED` while the composite Gold contract omits the nine
classification fields, even when both column groups already list them. Keep
the report with the occurrence; do not commit it.

```json
{
  "schema_version": "bioetl_iuphar_main_contour_evidence_v1",
  "shadow": {
    "executed": false,
    "run_id": null,
    "separate_directory": false,
    "contract_version": null,
    "business_rows_unchanged": false,
    "profile_sha256": null,
    "config_sha256": null,
    "cohort_sha256": null,
    "discrepancy_report_sha256": null,
    "independent_expectations_sha256": null,
    "row_count": 0,
    "status_counts": {
      "iuphar_match_status": {},
      "local_class": {},
      "effective_class": {},
      "decision_status": {}
    },
    "source_completeness": "not_recorded"
  },
  "isolated_enrich": {
    "executed": false,
    "separate_directory": false,
    "limit": null,
    "full_table_proof": false,
    "silver_contract": null,
    "gold_contract": null,
    "profile_sha256": null,
    "config_sha256": null,
    "evidence_manifest_sha256": null,
    "persisted_silver_sha256": null,
    "persisted_gold_sha256": null,
    "repeat": {
      "same_inputs": false,
      "same_versions": false,
      "classification_sha256": null,
      "repeat_classification_sha256": null
    },
    "xlsx": {
      "table_sha256": null,
      "xlsx_sha256": null,
      "historical_columns": []
    }
  },
  "composite_enrich": {
    "executed": false,
    "separate_directory": false,
    "agreed_cohort_sha256": null,
    "same_cohort_as_shadow": false,
    "classification_columns_present": false
  },
  "migration": {
    "rehearsal_rollback": "NOT_RUN",
    "fk_unresolved": null,
    "writers_quiesced": false,
    "promoted": false,
    "source_identity_matches": false,
    "effective_config_sha256": null,
    "effective_profile_sha256": null,
    "physical_contract": null,
    "backup_retained": false,
    "full_cohort": false
  },
  "live": {
    "readback": false,
    "next_run_executed": false,
    "next_run_id": null,
    "tables_match_promoted": false,
    "classification_reproduced": false,
    "observed_profile_sha256": null,
    "observed_config_sha256": null
  },
  "biological": {
    "biological_accuracy_accepted": false,
    "matched_count": null,
    "matched_count_used_as_qualification": false,
    "scientific_status": null,
    "rf008_receipt_status": "NOT_RUN",
    "rf008_receipt_sha256": null,
    "independent_reference_sha256": null,
    "reviewer_reference": null
  },
  "local": {"status": "NOT_RUN", "evidence_sha256": null},
  "ci": {"status": "NOT_RUN", "commit_sha": null}
}
```

## Verification

- Confirm the selected configuration, contract version, actual schema hash,
  normalization identity, and profile digest in the effective configuration
  and [run manifest](run-manifest-inspection.md).
- Read `classification-verification.json`, `m-parity-report.json`, and
  `proof-verification.json` separately. A `PASS` in one file does not change
  the status stored in the others. `ci.status: NOT_RUN` means CI was not
  recorded for that head. Do not relabel it as `PASS`.
- Keep `biological_accuracy_accepted: false` until a reviewed biological
  receipt says otherwise. Engineering checks, M comparison, and pipeline proof
  do not grant that receipt.
- For shadow, verify unchanged V30 rows/hash scope plus complete separate
  evidence. For enrich, verify V31 on both tables, coherent profile values,
  completed evidence, full cohort preservation, and baseline FK closure.
- Read `contour-report` phases and axes separately: `local`, `ci`,
  `migration`, and `biological`. `promotion_decision` is not a biological
  accuracy claim, and `matched_count` does not change
  `biological_accuracy_accepted`.
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

### RF-013 live acceptance on 2026-11-25

The shared `chembl_target` workflow completed at 12:34 UTC using fresh ChEMBL
input. It ran in `incremental` mode with `--no-cached-bronze` and the per-run
`--required-persistence-profile degraded_observable`. The first invocation
exited during configuration validation because the default `replay_ready`
requires an immutable Bronze snapshot. The final run retained its workflow,
pipeline, and classification manifests.

- Workflow run `d2fb7a28-e29e-5d4e-a2ff-c0cd2f904ad3`
- Pipeline run `4d8b54c7-763f-5598-abd5-bf48ddf7567c`
- 11,055 Bronze records, 365 Silver quarantines and 1,572 Gold exclusions
  under the active contract.
- 10,690 current Silver rows at Delta version 23 and 9,118 current Gold rows
  at Delta version 11. Each of the 10,690 stored Silver classifications
  matched its run evidence. All nine fields agreed between current Gold and
  Silver for every current Gold key.
- Zero unresolved target references from the 983 assay Gold rows. All
  promoted target identities are still present in their respective layers.

`contour-report --require-ready` returned `LIVE_ACCEPTED`. The active
local deployment is `enrich` on 3.1.0. This operational acceptance
uses the bounded RF-008 receipt and carries the accepted cutover PR
#13392 CI at `35befda97a6857fe479c5e1caff94a1d0ec848e0`.

The local deployment workspace retains the acceptance files under
`reports/local/iuphar-v31-rf013-live-20261125-v2/`. For a repeat report, use
`live-evidence.json`, `live-measurement-paths.json`, and
`--repo-root` pointing to `contour-source-bindings/` in that directory.
The pipeline report is under `reports/run-reports/pipeline/chembl_target/`
and the classification manifest under
`data/output/control/target_classification/`, each in the pipeline run ID
directory.

| Local evidence | SHA-256 |
| --- | --- |
| Live contour | `4df2caca933bc81eca0372df344f8cd0241e1553dc2f4d5fe79729b2bf94776c` |
| Live evidence | `4c20b88de2987d7304d0e682c7f4ead849913f8a3cda2e2e8772c7f9eee8dfc4` |
| Live measurements | `6eb75566770e8e9c17947fe3256509981998b33891e5118f907f2273733f664d` |
| Pipeline report | `f002e1fe9f3cbb6c5d213550b528336cc33511299f5d7359910ef287a51d305d` |
| Classification manifest | `e7a8c0c2e0b37ca1b20d05995840922e69faa4611c96da93c397967ab712e339` |

### RF-013 V31 refresh on 2026-11-27

The shared `chembl.target` tables were refreshed from V31 to V31 in the
authorised 17:00–18:30 window (UTC+03:00). The pre-promotion contour returned
`READY` with local and CI checks passing and a retained backup.
`LIVE_ACCEPTED` was recorded at 17:46:41 local time
(14:46:41 UTC).

- Code deployed at `627d517dc1d71ff92919ca57396b3df74dedc6da`.
- Rehearsal PR #13438 passed its gate at `dc37df9273b6dabd2b3dfae9fdba587578ddf06a`.
- Active mode `enrich`, contract `3.1.0`, and policy
  `hgnc-uniprot-reviewed-target-class-v1`.
- Enrich profile SHA-256 `b02152d8cce606caa43915f9039c2275b99a098861e52acf47643a128640dd15`.
- Effective local configuration SHA-256 `e4de770dd608a9ba45b213416dc931044e07d82349458a812248cc63bdeab469`.
- The controlled incremental `29f2fb28-eb43-579a-b367-5fbe531d43f7` used one
  hash-pinned Bronze record. The stored projection agreed between Silver and
  current Gold across all nine classification fields.

| Layer | Delta version after incremental | Current rows | No effective class |
| --- | ---: | ---: | ---: |
| Silver | 25 | 10,690 | 1,117 |
| Gold | 12 | 9,118 | 768 |

Both layers retained the original business cohort and previous Delta versions.
The 64 historical reference IDs and their classes, 37 closed Gold versions,
and 983 assay Gold rows were preserved. Unresolved assay target references
numbered zero. The two XLSX files contain the current rows at the accepted
Delta versions and passed round-trip verification. The journal and original
bundle are retained under `backup/`. The migration lock was released and the
active configuration admitted subsequent incremental writes.

The deployment host retains the evidence and exports in
`reports/local/iuphar-13410-rf013-20261127-1700/`.

| Path relative to the cutover directory | SHA-256 |
| --- | --- |
| `frozen.json` | `1d45834ce3cb0c79653628acaf0f06d0da8f1f70a275059c9787fcf3d18f9bce` |
| `build/build-manifest.json` | `f5d58b026c74909344d4e0188653474cfc197e19c64507421ba7e45b34a075ba` |
| `ready-contour.json` | `ac317e3cfc64b28c348cba84d7df1bd11a8bfe023f78f44034d5f10d6a934149` |
| `backup/journal.json` | `61ab44a8536acdd9de3a15d4189f8f67e05d7304503749488a524602b8466cf6` |
| `live-contour.json` | `383b0c931fb2eee6a7c74fb8539c2df7bfdca4ff414fbf0a2edfa7e8918317d1` |
| `incremental-readback.json` | `10c9edba3b4d93a349197a3c02751ab69c988ffd71143bc36a6a689313047c38` |
| `writer-release-verification.json` | `328ab6e96ba3fc07ac1e317bf19d9bf9be04d9397161ef1feae3635af53305e8` |
| `xlsx/verification.json` | `71e6b3803b943edd863e1321f60d50eb56740d0a0ae246dce6f34ec6ad565846` |
| `xlsx/chembl-target-silver-v31.xlsx` | `2b42f795c9aa33647824ebd75ae3a89ea14552eeb72045e2eb46def35b83a228` |
| `xlsx/chembl-target-gold-v31.xlsx` | `2491b28e91b77dd81dff09b906a026f0380c925aa4e5bb4eb3cb2402396e1111` |

## Compliance

Use the admitted profile for ordinary writers. A new profile requires reviewed
inputs and the promotion procedure. Use one contract for shared-table writers, preserve
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

## Audit remediation 2026-11-23

`iuphar_*`, `local_*` and `effective_*` keep separate roles. `target_type` remains the ChEMBL value. `source_unavailable` is not the same status as `not_found`. Standalone classification sees identifiers only. Full UniProt and protein features become available after composite dependency joins. The composite target runtime binds its post-join stage in classification modes other than off. An explicitly attached classifier remains available for callers that do not bind that stage.

Primary accessions come from `component_accessions`. `target_xref_uniprot_ids` are auxiliary and do not enter the required exact channel. Unknown auxiliary accessions stay diagnostic. A component accession does not prove a complex.

Connected local rules use catalog version `iuphar-local-rules-20261123`. EC 7 is Translocase under Enzyme. It is not Transporter. The pinned snapshot capability remains `family_only`. Paths are stored root to leaf. A `family_only` snapshot is not upgraded to full annotation.

Table contract `3.2.0` adds nullable detail columns to the nine V31 fields. Arrays are canonical JSON text. Null means the value was not computed. Default enrich stays on `3.1.0`. `off` and `shadow` cannot select `3.1.0` or `3.2.0`. The production entity configuration pins `enrich` and table contract `3.1.0`.

Standard XLSX export splits long text across the original data column and additional columns such as `<column>__bioetl_part_0002`. The `_bioetl_export_manifest` sheet records the part columns and source schema. Restore uses the manifest to reassemble the source columns.

Assay to target closure reports the missing target ids. A placeholder or a row without `source_sha256` is refused. `contract_mismatch` stays a blocker until `contract_decision` is `resolved`. The 37 missing Gold targets are not invented.

Offline candidate construction and validation support table contract `3.2.0`. The live target migration driver currently rejects `3.2.0` promotion. The audit evidence for promotion requires successful rehearsal rollback, FK closure, explicit biological acceptance and live-promotion authorization. Shadow is available. Enrich stays on an isolated catalog. A missing CI SHA is `NOT_RUN`. Class-match counts, including the diagnostic 633 and 374 figures, are not biological accuracy. No IUPHAR API key is required for the offline classifier.
