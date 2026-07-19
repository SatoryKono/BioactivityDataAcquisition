# Refactoring log: issues #6351 and #6352

Date: 2026-07-18

## Scope

- #6351: make the evidence DAG reproducible, keep the debt rollup fail-closed
  without crashing on a missing flaky-test review artifact, and refresh every
  rollup input from a clean checkout.
- #6352: make compatibility registry, importer census, generated snapshot, and
  contributor-facing metadata agree semantically.

## Findings and changes

1. The rollup's missing/invalid/unreadable flaky-review preflight and its CI
   producer ordering were already present in current `main`; their focused unit
   coverage was retained and revalidated.
2. The clean `origin/main` module-coverage inventory contained unresolved merge
   markers. They were removed before any artifact regeneration.
3. All #6351 producer artifacts were regenerated in dependency order:
   module coverage, hotspot family baseline, dead-code inventory,
   compatibility census, Domain I/O taint inventory, test governance, flaky
   review, architecture scorecard, config backlog, remote-main baseline, and
   the final debt rollup.
4. `docs/reports/evidence/project-package-topology/SUMMARY.md` was restored as a
   current topology node with `source_module_count=2237` and
   `source_tree_sha256=a37a4d7adf0c835baf182a48843a03e4e95499eb50d64f46332d7ff3a29746bd`.
5. A later merge had copied the complete live Grafana audit suite into
   `test_grafana_dashboard_tooling.py` while retaining the canonical standalone
   `test_grafana_live_audit_tooling.py`. Removing that exact duplicated tail
   reduced duplicate test names from 41 to 0 and duplicate occurrences from 82
   to 0; the dashboard tooling file now matches its pre-merge owner blob.
6. The closeout test for #6022-#6028 referenced an ignored JSON evidence node
   that had never been committed. The missing node was reconstructed from the
   live dependency, hotspot, duplication, and test-governance measurements with
   only flat-or-decreasing ratchets.
7. The AI drift checker treated ignored `.cursor/**` deploy state as mandatory
   in a clean checkout. It now skips a missing local deploy copy while still
   scanning it when present and always validating the canonical tracked Cursor
   rule source.
8. Compatibility metadata now reports 12 retained seams, 7 burden-bearing
   seams, 23 removed seams, 0 twin modules, 4 export facades, and 0 semantic
   conflicts. In particular, `health_api` is classified as a stable public API
   with zero first-party `src` importers, `entrypoints` has a reviewed zero/zero
   classification, and `run.py` records its one live first-party importer.

## Debt budget outcome

- No bounded-growth budget or exception budget was increased.
- `application_core.total_loc` moved from 22597 to 22218.
- `composition_runtime_builders.total_loc` moved from 6846 to 6840.
- The final rollup reports 45 passing gates, 0 failing gates, release status
  `passing`, and integral score 8.66.

## Mirror and generated-surface status

- Canonical compatibility registry semantics were already correct in current
  `main`; the generated census JSON/Markdown and compatibility snapshot were
  refreshed and checked against it.
- The topology evidence summary was refreshed from the current source tree.
- No runtime behavior mirror changed, and no `.env` surface was edited by this
  change.
