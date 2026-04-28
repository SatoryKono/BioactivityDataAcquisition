______________________________________________________________________

Title: Control-Plane Lifecycle Runbook
Status: Active
Class: operational
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: "2026-04-22"

______________________________________________________________________

# Control-Plane Lifecycle Runbook

Control-plane lifecycle cleanup covers immutable operational artifacts under
`data/output/control/`, active checkpoint files under `data/output/checkpoints/`,
and cached Bronze snapshot files under `data/output/bronze/`.

## Safety Model

Cleanup is planner-driven:

1. Build a dry-run plan.
1. Review candidates and protected-reference reasons.
1. Re-run the same command with `--apply` only after review.

Dry-run is the default. Apply mode deletes only files selected by the planner.

Protected references are fail-closed:

- retention-active manifests protect their run, replay parent, effective-config
  artifact, input snapshots, ledgers, and lineage fragments;
- stale manifests that declare `required_persistence_profile=replay_ready` or
  `required_persistence_profile=forensic_grade` protect the same evidence floor
  unless the operator explicitly passes `--allow-profile-floor-violation`;
- retention-active checkpoints protect their run, manifest, and effective-config
  artifact anchors;
- cached Bronze files are retained when their content-addressed
  `sha256:{content_hash}` snapshot ID is referenced by a retained manifest;
- explicitly protected run, manifest, effective-config, lineage, and snapshot
  identifiers are always retained.

## Commands

Preview cleanup candidates:

```bash
bioetl maintenance control-plane-lifecycle --retention-days 90
```

Apply the reviewed plan:

```bash
bioetl maintenance control-plane-lifecycle --retention-days 90 --apply
```

Write JSON for automation:

```bash
bioetl maintenance control-plane-lifecycle --format json > control-plane-lifecycle-plan.json
```

Protect specific references:

```bash
bioetl maintenance control-plane-lifecycle \
  --protected-run-id "$RUN_ID" \
  --protected-manifest-id "$MANIFEST_ID" \
  --protected-snapshot-id "sha256:$CONTENT_HASH"
```

Override a stale replay/forensic evidence floor only after separate review:

```bash
bioetl maintenance control-plane-lifecycle \
  --retention-days 90 \
  --allow-profile-floor-violation \
  --apply
```

Dry-run and JSON output expose evidence-floor retention as
`reason=reproducibility_evidence_floor` with `protected_by` values prefixed by
`evidence_floor:`. Treat those entries as replay/forensic contract violations,
not as ordinary retention-expired cleanup candidates.

## Recovery

If a dry-run plan looks unsafe, do not apply it. Increase `--retention-days` or
add explicit protected references, then generate a new plan.

If apply removes an artifact unexpectedly, restore it from filesystem backup or
object-store backup before running replay or checkpoint resume workflows that
depend on it. Do not recreate immutable control-plane payloads by hand; restored
payloads must match the original content-addressed or semantic identifiers.

## Observability

Apply mode emits structured log events:

- `control_plane_lifecycle_artifact_deleted`
- `control_plane_lifecycle_apply_summary`

It also emits bounded metrics:

- `bioetl_control_plane_lifecycle_deleted_total`
- `bioetl_control_plane_lifecycle_delete_candidates`
- `bioetl_control_plane_lifecycle_apply_total`
