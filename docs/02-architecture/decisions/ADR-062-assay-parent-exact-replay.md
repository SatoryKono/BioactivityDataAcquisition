# ADR-062: Immutable composite parent merge replay

Status: Accepted
Date: 2026-10-03
Owner: BioETL maintainers

## Context

The composite rebuild-only boundary does not support exact parent replay.
Successful child processing and intact child reports cannot establish that the
same parent Silver and Gold data can be reproduced without ChEMBL. In particular,
a live parent has no immutable fingerprint for the Silver tables it actually
read. An advertised capability alone is not replay evidence.

## Decision

The extension applies to `composite_assay`, `composite_activity`,
`composite_molecule`, `composite_publication`, and `composite_target`.
Its replay boundary begins
at the raw, materialized child Silver tables consumed by the parent. Re-extracting
child Bronze is a separate child replay operation; parent acceptance continues to
require the complete child evidence chain, including Bronze and checkpoints.

Capture the exact Arrow tables returned by the reader before renaming,
deduplication, aggregation, joining, conflict resolution, lineage enrichment, or
Gold filtering. Own the captured buffers immediately and preserve schema, nulls,
timestamps, nested values, row order, and column order. Repeated reads in one
capture use the first captured version. Seal a digest-bound inventory only after
all contract-required inputs exist. Failed or cancelled reads must not certify
completeness. Files and sealed inventories are create-only.

The immutable parent envelope must bind the input inventory fingerprint, parent
identity, effective configuration, dependency lock, merge implementation and
policy fingerprints, stage outcomes (including intentional skips), original
lineage timestamp, child report identities and digests, and expected Silver/Gold
data fingerprints. Optional pipeline configuration does not make a successfully
consumed input optional for replay. An intentional skip is explicit evidence;
an absent snapshot of a consumed input is a failure.

An offline entry point reconstructs the same merge request and collaborators from
the envelope. Its reader has no live datasource or fallback. It executes the full
merge and writes to a new isolated output location. It verifies both materialized
Silver and Gold against the original logical table values, schema, and ordering.
Physical Delta transaction metadata and Parquet encoding are not the equality
contract. Delta scan order is normalized by `entity_id` and the assay identifier;
column order and Arrow schema remain part of equality. Other families use the
shared `entity_id` identity. Original report files and
original output locations are never updated.
Serialized stage-status maps use sorted JSON keys at the production write boundary;
insertion order of dependency or enricher results cannot change canonical rows.

`READY` requires a successful offline verification receipt bound to the parent
envelope plus current verification of every required object. Missing, modified,
or mismatched inputs, config, lock, policies, outputs, or child evidence block
acceptance. A historical successful receipt cannot override current object loss.
Provider `WARN` remains a strict acceptance failure even if replay succeeds.

## Rollout and validation

Launch manifests retain their original rebuild-only declaration. At completion,
the parent report binds the create-only replay envelope and child report digests.
The envelope binds resolved configuration, pipeline execution settings, dependency
lock bytes, installed implementation fingerprint, raw inputs, stage outcomes,
original lineage timestamp, and the tables read back from production storage.
The automatic offline replay uses the same production Silver and Gold writers in
an isolated directory. Its receipt binds all physical output files. HTTP promotes
only that verified post-capture evidence and retains every other strict gate.

The standalone command is:

```bash
python -m bioetl replay-composite --envelope /path/to/replay/parent.json --sha256 DIGEST_FROM_PARENT_REPORT --output /new/isolated/output
```

The destination must not exist. The implementation and dependency lock must match
the captured versions. No provider adapters are constructed. Receipt and object
digests are checked again on each HTTP assessment, including after a prior
successful replay. A missing proof keeps the rebuild-only boundary authoritative.

The v2 envelope freezes dependency selections and terminal outcomes as well as
enrichers. Every successfully consumed dependency must be captured. The actual
field-group registry (including provider order and the default group) is stored
as a required digest-bound object, so publication replay preserves Gold filtering
without loading mutable configuration. Output table names come from the captured
merge configuration. Target envelopes additionally require `target-mapping.json`,
containing the actual protein-class mapping version, entries, and non-counting
classes used by the merge. Standalone replay initializes this lookup from the
verified object; it cannot depend on prior live-process initialization or current
YAML. A missing or modified mapping blocks target replay readiness.
The legacy `replay-assay` command and v1 assay envelopes
remain supported within their original dependency-free boundary.

Required tests cover typed round trips; source-buffer mutation; concurrent reads;
cancellation; missing mandatory input; attempted overwrite; envelope and object
corruption; path escape; config/lock/policy mismatch; nullable cell/tissue foreign
keys with all seed rows retained; and offline Silver/Gold equality with networking
disabled. Production HTTP bootstrap must reject each damaged child independently
and must re-check lost objects after a successful replay.

Enforcement owners are the [physical replay tests](../../../tests/integration/composite/test_assay_snapshot_merge_replay.py)
and [bundle integrity tests](../../../tests/unit/infrastructure/storage/test_composite_replay_bundle.py).

## Consequences

Parent evidence consumes additional local storage proportional to the actual
merge inputs. The snapshot boundary avoids mutable Delta-table rereads and does
not require external orchestration. Families outside the explicit supported set
remain under the existing rebuild-only contract. Debt budgets and health-check thresholds are
unchanged.
