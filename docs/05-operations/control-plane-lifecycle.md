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

## Replay Evidence Retention Matrix

| Evidence surface | Retain when | Delete only when | Replay impact |
| ---------------- | ----------- | ---------------- | ------------- |
| `RUN_MANIFEST` | Manifest is retention-active, explicitly protected, replay parent/child-linked, or declares `required_persistence_profile=replay_ready` / `forensic_grade`. | Retention expired and not protected by run, parentage, checkpoint, lineage, or evidence-floor policy. | `strict_replay_evidence_protected` or `unprotected_replay_evidence_delete_candidate`. |
| `RUN_LEDGER` | Ledger is tied to a retained manifest or a replay/forensic evidence floor. | Owning manifest is delete-eligible and no checkpoint/resume reconstruction path references it. | Loss removes produced-artifact trace and resume/replay audit history. |
| `EFFECTIVE_CONFIG` | Artifact id is referenced by a retained manifest, checkpoint, or explicit protected reference. | No retained manifest/checkpoint/protected reference points at the artifact id. | Loss removes the semantic config identity proof for exact replay. |
| `CHECKPOINT` | Checkpoint is retention-active or anchors a retained run/manifest/effective-config artifact. | Checkpoint is expired and no protected run/manifest/effective-config relationship remains. | Loss may block resume or checkpoint-compatible exact replay. |
| `LINEAGE` | Fragment id is referenced by retained manifest/ledger sidecar links or explicit protected references. | No retained artifact, manifest, or ledger entry references the fragment id. | Loss breaks forensic closure for produced artifacts. |
| `cached_bronze_snapshot` | Snapshot id appears in retained manifest `source_refs` or explicit protected snapshot ids. | Snapshot is not referenced by any retained manifest/checkpoint/evidence floor. | Loss downgrades exact replay to rebuild/degraded modes. |

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

Dry-run text and JSON output include a `replay_impact` classification:

- `strict_replay_evidence_protected` means the artifact is protected by a
  `replay_ready` or `forensic_grade` evidence floor.
- `recovery_evidence_protected` means the artifact is protected by an active
  run/checkpoint/reference relationship.
- `unprotected_replay_evidence_delete_candidate` means the artifact is selected
  for deletion and may remove replay/resume/rebuild evidence that is no longer
  protected by retention policy.
- `no_replay_evidence` means the planner did not identify replay evidence for
  the selected artifact.

Evidence-floor retention is also exposed as
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

Deletion metrics include a bounded `replay_impact` label so alerting can
separate ordinary retention cleanup from replay-evidence deletion candidates.
