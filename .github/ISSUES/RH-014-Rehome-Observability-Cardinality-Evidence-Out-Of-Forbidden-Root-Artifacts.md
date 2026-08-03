# Rehome Observability Cardinality Evidence Out Of Forbidden Root `artifacts/`

**Status**: completed_in_repo
**GitHub Issue**: [#4347](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4347)
**Issue State**: closed
**Synced**: 2026-05-29
**Priority**: P1
**Labels**: `governance`, `observability`, `infrastructure`, `documentation`, `priority:high`
**Last audited**: 2026-05-19

## Problem

Root-hygiene policy currently forbids tracked generated/runtime root trees such
as ad-hoc artifact directories, but observability governance still points its
canonical runtime cardinality evidence to:

- `artifacts/observability/runtime_cardinality_inventory.json`

That creates a live policy contradiction:

- `scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked`
  currently fails because `artifacts/` is a tracked unexpected root directory
- observability governance and tests still treat that path as canonical

This is not a generic cleanup request. It is a governance and routing defect:
the repository currently blesses a root output path that the root policy says
must not exist.

## Evidence

- `artifacts/observability/runtime_cardinality_inventory.json`
- `configs/quality/observability_metric_governance.yaml`
- `configs/quality/test_governance_audit.yaml`
- `tests/architecture/test_observability_metric_governance.py`
- `scripts/engineering/repo/audit_root_cleanliness.py`
- `docs/00-project/governance/03-file-policy.md`
- `docs/03-guides/cleanup-policy.md`

## Proposed Solution

Move the runtime cardinality evidence to an approved artifact surface under
`reports/`, then update every governance/test/documentation reference to the
new canonical path.

Preferred target class:

- `reports/observability/` if the file is generated working evidence
- `reports/quality/` if the file is primarily a governance verification output

The issue is complete only when the old root `artifacts/` dependency is
removed from both tracked tree and policy/test references.

## Scope

- choose the canonical non-root destination for runtime cardinality evidence
- update `configs/quality/observability_metric_governance.yaml`
- update `configs/quality/test_governance_audit.yaml`
- update `tests/architecture/test_observability_metric_governance.py`
- update any producer command that writes `--write-evidence ...`
- update docs/readmes that mention the old path
- remove the tracked root `artifacts/` dependency from the repository tree

## Non-Goals

- do not weaken root-hygiene policy to allow a generic `artifacts/` root
- do not convert this file into a curated docs artifact under `docs/**`
- do not broad-clean other retention-sensitive outputs

## Acceptance Criteria

- no tracked `artifacts/` root directory remains
- observability cardinality evidence has one canonical path under an approved
  non-root artifact surface
- governance config, tests, and commands reference only the new path
- `./.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked`
  no longer fails because of `artifacts/`
- targeted observability governance tests pass against the new path

## Validation

```bash
./.venv/bin/python scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked
./.venv/bin/python -m pytest -q tests/architecture/test_observability_metric_governance.py
```

## Risks

- moving the evidence path without updating tests/governance config will create
  false drift
- routing the file to a curated docs surface would blur generated-vs-normative
  boundaries

## Related

- blocks `RH-015` because `artifacts/` is one of the current tracked root
  policy violations
