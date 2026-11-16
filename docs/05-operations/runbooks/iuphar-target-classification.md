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

## Trigger

Use this runbook to validate an offline IUPHAR classification dependency,
run shadow acceptance, or migrate the shared `chembl.target` tables to the
additive 3.1.0 contract. The feature is configured on `chembl_target`; it has
no dedicated workflow or pipeline CLI flag.

## Impact

The production configuration remains `mode: "off"`. The historical dictionary
available during implementation is an unqualified legacy source with unresolved
classification disagreements. An approved snapshot and independently reviewed
reference cases have not been supplied. Historical reports and synthetic test
fixtures do not qualify those inputs or establish biological accuracy.

The configuration applies to every writer of the same Silver/Gold target
tables: direct `chembl_target` runs and workflows `chembl_baseline`, `chembl_core`,
`chembl_reference_pack`, `chembl_target`, and
`chembl_target_protein_classification`. These writers must use one compatible
configuration and contract during a deployment.

| Mode | Business rows and hash policy | Required dependency |
| --- | --- | --- |
| `"off"` | Unchanged V30, contract 3.0.0 | None |
| `shadow` | Unchanged V30, contract 3.0.0; separate classification evidence | Pinned profile envelope and snapshot |
| `enrich` | V31, contract 3.1.0; nine additional nullable business columns enter the explicit hash scope | Complete, publishable snapshot and executed reference acceptance; compatible physical tables |

The registry's current identity remains 3.0.0. Publishing the
[V31 contract](../../04-reference/contracts/gold/chembl_target_v3.1.json) does
not promote production or enable generic dual writing.

## Preconditions

- Work from the repository root using the native Windows interpreter
  `.\.venv-win\Scripts\python.exe`, or the prepared local interpreter on other
  platforms. The commands below use PowerShell.
- Preserve existing data, configuration, reports, and evidence. Do not modify
  `.env` files as part of this procedure.
- Keep the existing target eligibility filters. This integration does not
  expand the pipeline to protein complexes or change baseline cohort selection.
- For promotion or rollback, stop and quiesce all writers listed above and
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
  "schema_version": 1,
  "snapshot": {"path": "snapshot.json", "sha256": "SNAPSHOT_SHA256"},
  "acceptance": null,
  "normalization_version": "bioetl-iuphar-input-v1",
  "rules_version": "plan-v1-r8",
  "classification_schema_version": "3.1.0"
}
```

The snapshot manifest uses artifact `bioetl_iuphar_snapshot`, schema version 1,
and format `gtopdb_target_payload_v1`. It binds frozen target payload bytes and
records the release, retrieval time, approved species/type scope, expected
count, pagination completion, coverage approval, and provider-version evidence.
The loader checks those facts against the payload. A caller-supplied
`complete: true` is not admission evidence.

`shadow` can inspect an incomplete dependency. Its missing coverage must remain
`source_unavailable`, rather than becoming a claim that the target was not
found. `enrich` requires both `complete` and `publishable`; a complete snapshot
with unverified provider versions is insufficient for publication.

Workflow dependency preflight pins and checks the target configuration and
profile before the first workflow step, including `chembl_baseline` assay
ingestion. Target preflight rechecks the pinned bytes and both actual writer
destinations before a backfill can clear target outputs. A V30 destination
blocks `enrich`; a V31 destination blocks `off`/`shadow`; partial or unrecognized
table schemas require recovery. Empty candidate destinations are allowed.

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

### Execute independent reference acceptance

1. Obtain a complete, publishable snapshot and an admitted, frozen Stage-0
   cohort. Freeze a versioned `bioetl_iuphar_reference_cases` document with
   reviewer/approval references, environment, full source selection, expected
   row count, snapshot digest, and independently reviewed per-case outcomes.
   Each case needs source references with verified byte hashes. Do not derive
   expected labels from the classifier output under test.
2. Run the actual `chembl_target` pipeline in `shadow` using that same snapshot.
   Preserve its completed evidence manifest and successful run report. A
   standalone kernel invocation does not prove pipeline integration.
3. Run the following command after replacing every uppercase placeholder with
   an approved value. Choose a new output directory; acceptance does not
   overwrite an earlier occurrence.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.engineering.qa.iuphar_target_acceptance `
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
qualify only that supplied scope; `biological_accuracy_accepted` remains false.
`BLOCKED_INPUT` or `FAIL` is not admission.

For an enrich profile, replace `acceptance: null` with the relative path and
SHA-256 of the accepted receipt. This creates new profile bytes and a new
profile digest. The dependency is noncircular: the receipt binds the snapshot;
the final profile binds the snapshot and receipt. Re-pin the final profile's
digest before building enriched candidates.

### Prepare and promote complete physical tables

Build V31 Silver and Gold candidates at separate approved destinations. Use
the complete canonical target cohort and the admitted enrich profile. A
`--limit 1000` smoke is not a migration candidate unless it independently
covers the entire canonical cohort.

Prepare a JSON migration plan outside the repository root. This example uses
placeholders deliberately; resolve the actual writer paths and replace them
before execution. Every path must be inside the existing approved workspace,
with no symlink/junction, nesting, overlap, or `.env` resource. The backup path
must not exist yet. `candidate_config` is the complete candidate entity YAML;
`config` is the canonical entity YAML.

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
.\.venv-win\Scripts\python.exe -m scripts.ops.target_classification_migration prepare --plan 'PATH_TO_APPROVED_PLAN_JSON'
.\.venv-win\Scripts\python.exe -m scripts.ops.target_classification_migration promote --plan 'PATH_TO_APPROVED_PLAN_JSON'
```

`prepare` validates admission, strict V31 schemas, unique target IDs, unchanged
legacy business values, V30 hash equivalence, equal full Silver/Gold target
cohorts, and closure with the non-null baseline assay target cohort. Gold's
`description` alias is mapped back to Silver's `target_description` for the
legacy hash check. It copies and hashes the entire physical old tables and
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
- Inspect the receipt's five executed checks, source digests, output hashes,
  and matching successful integration report. Retain unresolved disagreements
  for owner review; a green software test is not reference-case approval.
- For replay, retain the exact profile, snapshot, payload, receipt, effective
  configuration, and run/workflow dependency artifacts. Replay pins their
  recorded identities and rejects changed bytes; it must not resolve a
  `latest` alias or substitute a newly available snapshot. Workflow resume
  retains the stored target configuration/dependency rather than taking the
  current default.

## Rollback

Keep all writers quiescent and use the same approved plan:

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ops.target_classification_migration rollback --plan 'PATH_TO_APPROVED_PLAN_JSON'
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
- [Workflow/runtime dependency binding](../../../src/bioetl/composition/target_classification.py)
- [Schema and hash profile selection](../../../src/bioetl/infrastructure/config/target_classification_profile.py)
- [Evidence publication](../../../src/bioetl/infrastructure/adapters/iuphar/evidence_store.py)
- [Acceptance implementation](../../../src/iuphar_target_class/integration_acceptance.py)
- [Physical migration and journal](../../../src/bioetl/infrastructure/storage/target_classification_migration.py)
