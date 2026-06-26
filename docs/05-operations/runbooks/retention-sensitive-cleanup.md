______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-28'

______________________________________________________________________

# Retention-Sensitive Cleanup Runbook

## Trigger

Use this runbook before any cleanup that touches a retention-sensitive or
reproducibility-sensitive surface:

- `data/**`
- `data/debug_exports/**`
- `data/output/control/**`
- `data/output/checkpoints/**`
- cached Bronze snapshots under `data/output/bronze/**`
- `tests/fixtures/**`
- `tests/fixtures/vcr/**`
- `docs/reports/**`
- `reports/**`
- `docs/99-archive/**`

Do not use broad deletion commands against these paths. A cleanup is allowed
only when it is bounded by ownership, retention reason, dry-run evidence, and
post-cleanup verification.

GitHub cleanup requests for these surfaces MUST use
`.github/ISSUE_TEMPLATE/retention_sensitive_cleanup.yml` or provide the same
evidence fields in a PR description.

## Impact

- Priority: P1.
- Incorrect cleanup can destroy replay evidence, retained manifests, VCR
  fixtures, curated reports, or historical traceability needed for audit and
  reproducibility.

## Preconditions

- The exact candidate paths are known before any apply/delete command is run.
- The operator has a reviewed issue, PR, or local evidence note that records
  ownership, retention reason, verification command, and rollback source.
- The worktree state is known, and generated/local-only artifacts are separated
  from tracked evidence.

## Safety Model

Retention-sensitive cleanup is fail-closed:

1. Classify the target path before proposing deletion.
1. Prefer dry-run inventory over filesystem mutation.
1. Preserve replay, fixture determinism, historical traceability, and curated
   evidence by default.
1. Use the narrowest maintained tool for the surface.
1. Apply only after review of exact candidate paths.
1. Record the decision and verification evidence in the issue or PR.

The absence of an obvious runtime caller is not enough to delete artifacts in
the protected surfaces above.

The machine-readable replay-safe cleanup inventory is
`configs/quality/replay_safe_cleanup_inventory.yaml`. Treat it as the canonical
operator checklist for destructive or semi-destructive cleanup paths. Any new
cleanup path that can touch replay evidence must be added there before it is
used operationally.

Retention classes used by the inventory:

- `reproducibility_fixture`: tracked inputs or fixtures used to recreate or
  prove replay behavior; retain unless an owner-reviewed replacement exists.
- `tracked_debug_evidence`: debug export bundles with manifests, schema
  sidecars, DQ summaries, lineage, and Bronze/Silver/Gold CSV evidence; prune
  only after owner review and regenerate/archive proof.
- `checkpoint_control_plane_state`: manifests, ledgers, effective configs,
  lineage, and checkpoints; route through the control-plane lifecycle planner.
- `local_runtime_output`: medallion or quarantine outputs that may be
  regenerable but still need path-specific retention and replay-impact review.
- `disposable_local_output`: bounded generated diagnostics that can be pruned
  only after dry-run, TTL, and owner checks.

## Surface Matrix

| Surface | Cleanup status | Required procedure |
| ------- | -------------- | ------------------ |
| `data/input/**` | Reproducibility fixture/input | Retain tracked inputs by default; require owner approval and replacement/replay proof before deletion. |
| `data/output/control/**` | Protected | Use [Control-Plane Lifecycle](../control-plane-lifecycle.md); preserve retained manifests, ledgers, effective configs, lineage, and protected references. |
| `data/output/checkpoints/**` | Protected | Use [Control-Plane Lifecycle](../control-plane-lifecycle.md) or a checkpoint-specific runbook; preserve resume/replay anchors. |
| cached Bronze snapshots | Protected | Use [Control-Plane Lifecycle](../control-plane-lifecycle.md); retain snapshots referenced by retained manifests. |
| `data/output/silver/**`, `data/output/gold/**` | Local runtime output | Require dry-run, owner retention note, and rebuild/backfill proof before cleanup. |
| `data/output/quarantine/**` | Quality exception evidence | Inspect/replay before purge; preserve records needed for DQ investigation or replay proof. |
| `data/debug_exports/**` | Owner-reviewed replay-adjacent evidence | Require debug-export inventory review, retention reason, and restore/regenerate path before purge; do not broad-delete export bundles. |
| `data/**` outside control-plane | Separate retention | Require owner approval, backup/restore path, and path-specific retention note. |
| `tests/fixtures/**` | Fixture-governed | Require fixture owner review and targeted test verification. |
| `tests/fixtures/vcr/**` | VCR-governed | Use the VCR recording/validation workflow; never blanket-delete cassettes. |
| `docs/reports/**` | Curated repo-only evidence | Keep by default; consolidate or archive only with provenance. |
| `reports/**` | Bounded working outputs | Clean only generated, non-curated, non-referenced outputs after dry-run. |
| `docs/99-archive/**` | Historical traceability | Keep by default; remove only duplicate/corrupt artifacts with explicit proof. |

### `reports/quality` TTL subclasses

The machine-readable inventory also defines owner/TTL subclasses for working
diagnostics under `reports/quality/`:

| Path family | Owner | TTL | Notes |
| --- | --- | --- | --- |
| `reports/quality/_tmp_*` | `Engineering / Quality` | 7 days | Transitional local diagnostics inside a retained reports surface; prune only after TTL expiry |
| `reports/quality/pretest_guardrails_*.json` | `Engineering / Quality` | 30 days | Timestamped pretest guardrail snapshots kept for short-lived review/history; prune only after TTL expiry |

These TTL classes do not override the fail-closed review model. They narrow the
approved candidate families for bounded prune waves, and they only become
prune candidates after the artifact age exceeds the configured TTL.

## Procedure

### 1. Inventory

Capture the exact candidate set:

```bash
git status --short
git ls-files <target-path>
find <target-path> -maxdepth 3 -type f | sort
```

If the candidate path is not tracked but is in a protected local runtime
surface, keep the same classification discipline. Local-only does not mean
safe-to-delete.

### 2. Classify

For each candidate path, record:

- owning surface from the matrix above
- whether it is tracked or local-only
- runtime or test caller
- retention reason
- proposed action: keep, archive, regenerate, or delete
- verification command
- rollback or restore source

### 3. Dry-Run

Use maintained dry-run tools where available.

Control-plane lifecycle:

```bash
bioetl maintenance control-plane-lifecycle --retention-days 90
```

Repository cleanup outside protected surfaces:

```bash
python -m scripts.ops.support.repo.cleanup_repository --dry-run
```

Root hygiene:

```bash
python -m scripts.engineering.repo check-cleanliness
```

### 4. Review Gate

Before apply/delete, confirm:

- no candidate is a retained manifest, ledger entry, effective-config artifact,
  lineage fragment, checkpoint, or referenced snapshot;
- no candidate is a governed fixture or VCR cassette still used by tests;
- no candidate is curated evidence in `docs/reports/**`;
- no candidate is historical context in `docs/99-archive/**`;
- no candidate is needed for replay, inspection CLI, or forensic traceability;
- the restore path is known.

replay-impact checklist:

- if the candidate is under `data/output/control/**`,
  `data/output/checkpoints/**`, or cached Bronze, use
  `bioetl maintenance control-plane-lifecycle` and review `replay_impact`;
- if the candidate is under `data/debug_exports/**`, review the exact export
  bundle contents, confirm no active investigation or replay/debug workflow
  still depends on them, and record the regenerate or archive path before
  deletion;
- `strict_replay_evidence_protected` means deletion would violate a
  `replay_ready` or `forensic_grade` evidence floor unless a separate override
  review explicitly accepts that loss;
- `recovery_evidence_protected` means the artifact is still tied to retained
  resume/rebuild evidence and should not be deleted by ordinary cleanup;
- `unprotected_replay_evidence_delete_candidate` is allowed only when the
  retained manifest/checkpoint/snapshot references no longer protect it;
- surfaces outside the control-plane lifecycle planner must still record why
  the deletion does not affect exact replay, resume-only recovery, or forensic
  traceability.
- fixture/VCR/golden pruning must follow
  `configs/quality/fixture_governance_ledger.yaml`: metadata owner,
  reachability evidence, generator/catalog drift check, targeted replay or
  contract test, and rollback/rerecord path are required.

### 5. Apply

Apply only the reviewed candidate set. Do not use recursive wildcard deletion
against the protected surface root.

Allowed pattern:

```bash
# Example shape only: use the reviewed file list from the dry-run.
git rm <exact-reviewed-path>
```

Disallowed pattern:

```bash
rm -rf data/
rm -rf tests/fixtures/
rm -rf docs/reports/
rm -rf docs/99-archive/
rm -rf reports/
```

## Verification

### 6. Verify

Run the verification command recorded for the surface:

- root placement: `python scripts/engineering/repo/audit_root_cleanliness.py`
- control-plane: `bioetl maintenance control-plane-lifecycle --retention-days 90`
- VCR fixtures: targeted provider tests or VCR metadata checks
- reports/docs: link/nav checks appropriate to the edited docs

Record the command output summary in the PR or issue.

## Escalation

Escalate to a separate retention/security issue when:

- a candidate may contain secrets or local credentials;
- a candidate is tied to incident evidence;
- a manifest/ledger/checkpoint/snapshot relationship is ambiguous;
- a VCR cassette may include newly recorded provider data;
- the restore path is unknown.

## Rollback/Recovery

- For tracked files, restore from git before rerunning tests.
- For local runtime data, restore from the documented filesystem or object-store
  backup. Do not synthesize immutable control-plane artifacts by hand.
- For VCR fixtures, re-record through the maintained VCR workflow and rerun the
  affected contract/e2e tests.

## Post-incident

- Confirm the cleanup decision is linked from the issue or PR.
- Confirm all verification commands are recorded with pass/fail outcomes.
- File follow-up issues for any ambiguous retention surface that could not be
  classified during the cleanup.

## Post-Cleanup Evidence

Every retention-sensitive cleanup PR or issue MUST include:

- candidate inventory;
- classification table;
- dry-run evidence;
- reviewed apply/delete list;
- verification command output;
- rollback or restore note.

The canonical GitHub issue form for this evidence pack is
`.github/ISSUE_TEMPLATE/retention_sensitive_cleanup.yml`.

## Compliance

- ADR-010 local-only deployment remains the runtime baseline.
- Cleanup must preserve replay, inspection, and forensic evidence unless a
  separate reviewed exception explicitly accepts the loss.
