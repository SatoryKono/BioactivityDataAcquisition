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

## Surface Matrix

| Surface | Cleanup status | Required procedure |
| ------- | -------------- | ------------------ |
| `data/output/control/**` | Protected | Use [Control-Plane Lifecycle](../control-plane-lifecycle.md); preserve retained manifests, ledgers, effective configs, lineage, and protected references. |
| `data/output/checkpoints/**` | Protected | Use [Control-Plane Lifecycle](../control-plane-lifecycle.md) or a checkpoint-specific runbook; preserve resume/replay anchors. |
| cached Bronze snapshots | Protected | Use [Control-Plane Lifecycle](../control-plane-lifecycle.md); retain snapshots referenced by retained manifests. |
| `data/**` outside control-plane | Separate retention | Require owner approval, backup/restore path, and path-specific retention note. |
| `tests/fixtures/**` | Fixture-governed | Require fixture owner review and targeted test verification. |
| `tests/fixtures/vcr/**` | VCR-governed | Use the VCR recording/validation workflow; never blanket-delete cassettes. |
| `docs/reports/**` | Curated repo-only evidence | Keep by default; consolidate or archive only with provenance. |
| `reports/**` | Bounded working outputs | Clean only generated, non-curated, non-referenced outputs after dry-run. |
| `docs/99-archive/**` | Historical traceability | Keep by default; remove only duplicate/corrupt artifacts with explicit proof. |

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

## Rollback

- For tracked files, restore from git before rerunning tests.
- For local runtime data, restore from the documented filesystem or object-store
  backup. Do not synthesize immutable control-plane artifacts by hand.
- For VCR fixtures, re-record through the maintained VCR workflow and rerun the
  affected contract/e2e tests.

## Post-Cleanup Evidence

Every retention-sensitive cleanup PR or issue MUST include:

- candidate inventory;
- classification table;
- dry-run evidence;
- reviewed apply/delete list;
- verification command output;
- rollback or restore note.
