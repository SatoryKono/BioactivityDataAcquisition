# Resolve Noncanonical Root `concepts/` Documentation Surface

**Status**: active
**Priority**: P2
**Labels**: `governance`, `documentation`, `cleanup`, `priority:medium`
**Last audited**: 2026-05-21

## Problem

Repo-native structure checks currently fail because the repository root contains
the tracked directory:

- `concepts/`

This directory is not part of the approved tracked root set in
`docs/00-project/governance/03-file-policy.md`, is not registered as an
approved root in `.github/root-allowlist.txt` or
`configs/quality/repo_structure_catalog.yaml`, and is therefore a live
root-governance violation.

The problem is not that the files are empty or obviously broken. The problem is
that a standalone documentation subtree exists outside the canonical active docs
surfaces (`docs/00-05/**`) and outside the approved archive/evidence lanes.

## Evidence

- `python3 scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked`
  reports:
  - unexpected tracked root directory: `concepts`
- `python3 scripts/engineering/diagnostics/audit_structure.py --path .`
  reports:
  - `[ROOT_DIR] concepts → Неразрешённая папка в корне`
- `docs/00-project/governance/03-file-policy.md`
- `.github/root-allowlist.txt`
- `configs/quality/repo_structure_catalog.yaml`
- current tracked files:
  - `concepts/data-quality.mdx`
  - `concepts/medallion-architecture.mdx`
  - `concepts/ru/data-quality.mdx`
  - `concepts/ru/medallion-architecture.mdx`

## Why This Matters

- Root policy says tracked root directories must stay within approved runtime,
  project, and curated tooling surfaces.
- The repository already has canonical documentation placement rules under
  `docs/**`.
- Leaving `concepts/` in root creates a second documentation topology outside
  the governed docs tree and keeps root-hygiene checks red.

## Proposed Solution

Classify the `concepts/` subtree explicitly and remove the root policy
violation by choosing one of the governed outcomes:

1. migrate the content into canonical `docs/**` pages if it is still active;
2. archive it under `docs/99-archive/**` if it is historical or superseded;
3. delete it if it is duplicate/non-canonical and no longer needed.

Do not solve this by weakening the root policy to allow an extra generic docs
root.

## Scope

- inventory all four tracked `.mdx` files under `concepts/`
- determine whether each file is active documentation, historical context, or
  duplicate content
- move retained content into canonical docs or archive surfaces
- remove the tracked root `concepts/` directory from the live repo layout
- update any navigation/build references only if a canonical destination is kept

## Non-Goals

- do not add `concepts/` to approved tracked root directories
- do not treat this as a broad docs reorganization wave
- do not delete canonical docs in `docs/**`

## Acceptance Criteria

- no tracked root `concepts/` directory remains
- any retained content has a justified canonical destination under `docs/**` or
  `docs/99-archive/**`
- `python3 scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked`
  no longer fails because of `concepts/`
- `python3 scripts/engineering/diagnostics/audit_structure.py --path .`
  no longer reports `concepts` as an unapproved root directory

## Validation

```bash
python3 scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
python3 scripts/engineering/diagnostics/audit_structure.py --path .
rg -n "concepts/" .github docs scripts tests configs README.md mkdocs.yml
```

## Risks

- deleting the subtree without first classifying the content may lose
  documentation that still has user value
- migrating content without mapping canonical successors can create a silent docs
  drift instead of removing it

## Related

- complements the existing root-hygiene issue pack
- should be resolved before any claim that the tracked root layout is policy-clean
