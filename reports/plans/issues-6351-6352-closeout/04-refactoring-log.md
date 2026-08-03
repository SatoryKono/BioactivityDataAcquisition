# Refactoring log: issues #6351 and #6352

Date: 2026-07-19

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
2. The rebased `origin/main` module-coverage inventory was valid JSON, but its
   top-level source-tree hash was stale and its `summary` still carried a second,
   conflicting source-tree hash. The producer now removes that deprecated nested
   field and has unit plus architecture regression coverage.
3. All #6351 producer artifacts were regenerated in dependency order:
   module coverage, hotspot family baseline, dead-code inventory,
   compatibility census, Domain I/O taint inventory, test governance, flaky
   review, architecture scorecard, config backlog, remote-main baseline, and
   the final debt rollup.
4. `docs/reports/evidence/project-package-topology/SUMMARY.md` was restored as a
   current topology node with `source_module_count=2239` and
   `source_tree_sha256=dd3995ccbc3518a23e1c66d9c08f7f2eb6c78ca574fb653b35a9fa76f5cabcd9`.
5. The Grafana live-audit duplication was already removed on current `main`.
   The rebased test-governance collector confirms duplicate test names and
   duplicate occurrences remain `0/0` across `2014` test files and `22514`
   test functions.
6. The closeout test for #6022-#6028 referenced an ignored JSON evidence node
   that had never been committed. The missing node was reconstructed from the
   live dependency, hotspot, duplication, and test-governance measurements with
   only flat-or-decreasing ratchets.
7. The AI drift checker treated ignored `.cursor/**` deploy state as mandatory
   in a clean checkout. It now skips a missing local deploy copy while still
   scanning it when present and always validating the canonical tracked Cursor
   rule source.
8. Compatibility metadata now reports 12 retained seams, a
   `retained_public_entrypoint_burden` of `0`, 23 removed seams, 0 twin modules,
   4 export facades, and 0 semantic conflicts. The proposed maintenance-command
   removal wave is no longer mislabeled as unused: its two exact first-party
   importers are recorded and removal is deferred until they return to zero.

## Debt budget outcome

- No bounded-growth budget or exception budget was increased.
- `application_core.total_loc` is `22218` and remains within its ratchet.
- `composition_runtime_builders.total_loc` is `6842` and remains within its
  ratchet.
- The refreshed hotspot-family evidence reports 14 governed duplication
  clusters across the tracked families; all remain within existing limits and
  no limit was raised.
- The final rollup reports 45 passing gates, 0 failing gates, release status
  `passing`, and integral score 8.66.

## Mirror and generated-surface status

- The canonical compatibility registry was corrected first; the generated
  census JSON/Markdown and compatibility snapshot were then refreshed and
  checked against it.
- The topology evidence summary was refreshed from the current source tree.
- No runtime behavior mirror changed, and no `.env` surface was edited by this
  change.
