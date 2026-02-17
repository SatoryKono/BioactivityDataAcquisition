# Contract Snapshot Diff Blocking Policy

## Purpose

This policy defines the merge gate for Silver schema contract snapshots.

The CI workflow `.github/workflows/contract-snapshot-diff.yml` regenerates schema JSON contracts from current Pandera models and compares the generated output with repository-tracked snapshots in `tests/contract/silver_schemas/snapshots/`.

## Blocking Rule

A pull request is **blocked from merge** when the job **Contract Snapshot Diff Status** is not green.

The check fails when regenerated contract JSON differs from tracked files, including changes in:

- `name` (field addition/removal)
- `type`
- `nullable`
- `description`

## Required Status Check Configuration

Branch protection for `main`/`master`/`develop` MUST include:

- **Required status check**: `Contract Snapshot Diff Status`

This status check is emitted by the summary job in `.github/workflows/contract-snapshot-diff.yml` and is the canonical check to require at merge time.

## Developer Workflow

When CI reports a contract diff:

1. Regenerate snapshots locally:

   ```bash
   python scripts/verify_silver_contract_snapshots.py --write
   ```

1. Review the diff and validate downstream impact.

1. Commit updated snapshot JSON files.

1. Ensure `Contract Snapshot Diff Status` passes.

## CI Diff Summary Output

On mismatch, CI emits a human-readable summary grouped by:

- `name`
- `type`
- `nullable`
- `description`

This summary is produced by `scripts/verify_silver_contract_snapshots.py`.
