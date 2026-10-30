______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-10-29'

______________________________________________________________________

# Quality tooling artifact refresh (QM-08)

## Trigger

Use this runbook when the quality-tooling candidate changes active source,
test, documentation or governance artifact inputs.

## Impact

Stale reports can attribute engineering code to the product denominator or
hide missing test paths. Priority: P2. This refresh does not accept the epic.

## Preconditions

`scripts.engineering.quality` is the shared engineering library. Existing QA/CI
commands remain the operator entrypoints. Product analysis still targets
`src/bioetl`; quality tooling is outside that product denominator. A changed
topology count does not establish a change in total code or CI cost.

Use the locked project development interpreter. On Windows use `.venv-win` when
present, otherwise the configured Windows project venv. Source tooling needs
the repository root and `src` importable. Do not apply this bootstrap to the
installed-wheel smoke environment. Generators that share outputs run serially
in one owned checkout. Preserve before-bytes and measurements outside the
working tree before updating them.

## Procedure

### Inputs and dependency order

Start from a source/consumer candidate with the accepted scripts taxonomy and
budgets. Reuse applicable test and generator side-effect evidence by source and
input identity. An issue's closed state or a local commit alone is not evidence.
This workflow neither accepts QM-07 nor requires its lifecycle ADMIT to refresh
an otherwise qualified input. Do not overwrite QM-07's checkout or receipts.

Run each affected peripheral owner as check → update → check before the
coupled rollup. For test/docs-only changes use the selected
`refresh-ci-drift-families` families; do not run the full coupled writer merely
to rebind fingerprints. Its `_ratchet_family_budgets` step may shrink
`configs/quality/debt_scorecard.yaml`. Use the full coupled writer only when
coverage, the dependency map or hotspot inputs changed, or the live assertless
category inventory decreased, and review any shrink.
Budgets must never increase. Exact entrypoints and output families are:

When a candidate changes the production source covered by COMP-004, qualify its
delta before the rollup. The repository-only source requalifier requires full Git
history and an explicit review for every changed source file. It reuses pinned
definitions, resolves references against actual Git blobs, and retains the
independent acquisition census and historical candidate dispositions:

```bash
python -m scripts.engineering.qa requalify-external-resource-inventory --review configs/quality/external_resource_inventory_qm08_review.json --check
python -m scripts.engineering.qa requalify-external-resource-inventory --review configs/quality/external_resource_inventory_qm08_review.json --update
python -m scripts.engineering.qa requalify-external-resource-inventory --review configs/quality/external_resource_inventory_qm08_review.json --check
python -m scripts.engineering.qa.external_resource_inventory --check
```

The writer derives source identities, partition hashes and counts. Do not edit
them by hand. Ambiguous reference moves, missing acquisitions, dirty production
sources and a runtime-PASS substitution stop generation before writing. This is
source qualification only: all lifecycle scenarios remain `NOT_RUN_12553`.
The requalifier is engineering repository tooling, not an installed runtime or
a Git-free sdist command. Its baseline narrative and heuristic input provenance
remain preserved separately from the derived current source counts.

If the config-discrepancy baseline is stale, run
`python -m scripts.schema generate-config-matrix --check` → `--update` →
`--check` **before** the full coupled owner. This produces
`reports/quality/config-discrepancy-baseline.json`,
`docs/04-reference/config_comparison_matrix.csv` and
`docs/reports/generated/config-discrepancies-report.md`. The coupled scorecard
sync takes its config counts from this baseline, tightens matching maxima and
rejects any increase above an existing maximum.

| Order | Owner and argv | Inputs | Outputs |
| --- | --- | --- | --- |
| 1 | `python -m scripts.engineering.qa report-test-basename-collisions --check` / `--update` | Existing Git-indexed `tests/**/*.py` named `test_*.py`; no lane exclusions | `reports/quality/test-basename-collision-inventory.json` |
| 2 | `python -m scripts.engineering.qa.build_pytest_nodeid_inventory --check` / `--update` | Actual pytest collection, test matrix and shard rules | `reports/quality/pytest-nodeid-inventory.json` |
| 3 | `python -m scripts.engineering.qa report-cast-any-typing-census --check` / without `--check` | Product Python sources and the existing statement-window classification | `reports/quality/cast-any-typing-census.{json,md}` |
| 4 | `python -m scripts.engineering.qa report-compatibility-importer-census --check` / without `--check` | Python imports and existing facade/twin registries | `reports/quality/compatibility-importer-census.{json,md}` |
| 5 | `python -m scripts.engineering.repo check-inventory --check` / `--update` | Indexed scripts, callers, docs, catalog and lifecycle decisions | `configs/quality/scripts_inventory_manifest.json` |
| 6 | `python -m scripts.engineering.qa.refresh_governance_artifacts --check` / without `--check` | The coupled sources below | The coupled output set below |
| 7 | `python -m scripts.engineering.qa refresh-ci-drift-families --check --test-gov --flaky-fingerprint --remote-main --dataflow` / replace `--check` with `--update` | Updated test/config/source fingerprints and fetched main | Test-governance, flaky, remote-main and dataflow families |
| 8 | `python -m scripts.docs generate-cleanup-inventory --check` / `--update` | Final documentation links, headers and references | `docs/reports/generated/documentation-cleanup-inventory.{json,md}` |
| 9 | `python -m scripts.engineering.qa report-debt-governance-gates --check` / `--update` | Final active scorecards and inventories | `reports/quality/debt-governance-gates.{json,md}` |
| 10 | `python -m scripts.engineering.qa refresh-ci-drift-families --check --evidence` / replace `--check` with `--update` | Final audit evidence paths, including `debt-governance-gates.json` | Current audit registry/report `evidence_surface_sha256` |

The full coupled owner runs, in source order:

1. Source-tree manifest → `reports/quality/source-tree-manifest.json`.
2. Module-coverage freshness → `reports/quality/module-coverage-inventory.json`.
3. Architecture map → `docs/02-architecture/generated/module-dependency-map.{json,md}`.
4. Test governance → `reports/quality/test-governance-current.json` and
   `test-fixture-asset-duplication.json`. The fresh scan also supplies the
   shrink-only `assertless_triage.categories.*.count` bindings in
   `configs/quality/test_governance_audit.yaml`; changed counts trigger a second
   test-governance write before downstream owners. New categories or count growth
   stop the writer for policy review. `--check` reports stale bindings without
   writing; update preserves the other policy values, comments and formatting.
   Do not edit the measured category counts or historical closeouts by hand.
5. Hotspot baseline and shrink-only scorecard synchronization →
   `reports/quality/hotspot-family-baseline.{json,md}` and existing scorecard metrics.
6. Dead-code inventory → `reports/quality/dead-code-inventory.{json,md}`.
7. Architecture scorecard → **both** `reports/quality/architecture-quality-scorecard.json`
   and `reports/quality/domain-aggregate-invariant-registry.json`.
8. Config backlog → `reports/quality/config-surface-backlog.json`.
9. Live residual snapshot → `reports/quality/live-residual-snapshot.json`.
10. Remote-main baseline → `reports/quality/architecture-debt-remote-main-baseline.{json,md}`.
11. Debt rollup, then the entrypoint's targeted coverage/application-core closeout
    refresh. Preserve the previous measurement XML/JSON in Git and before-bytes.

The conditional closeout owners cover `low-coverage-targeted-tests-6045.json`,
`low-coverage-6045-revalidation.xml` and
`issue-5272-application-core-coverage-closeout.json` under `reports/quality`,
plus their existing technical-debt audit references. They run only when their
source binding requires it; unchanged measurements are not replayed.

Use the coupled entrypoint, not a hand-assembled substitute. Confirm actual
outputs from its invocation log: some reporters own more than one artifact.
The dependency-map owner is
`python -m scripts.engineering.qa.generate_architecture_dependency_map --check`
or `--update`; coupled refresh already invokes it. Do not duplicate a run just
to collect another PASS for unchanged inputs. No historical telemetry rebind is
part of this recipe. The CI-family owner does not ratchet debt budgets.

## Business equality, measurements and invariant claims

Compare fixed fixtures with the same injected date/time and inputs before and
after refresh. Preserve business decisions, schema versions, severity and
formulas; list any agreed `generated_by` difference explicitly. Compare live
topology separately. A Git-indexed collision inventory records file locations,
not pytest nodeids or duplicate test-function names.

The coverage freshness mode preserves measured rows for existing modules and
drops deleted source paths. It does not measure new modules or justify changing
coverage facts. Only a complete accepted coverage-verify capture can update
measurements. Keep dated coverage-gap reports and source-pinned audit snapshots
as historical evidence, including their old namespace literals. Record those
references individually with content-bound reference decisions; never exclude
all docs or reports from the scan. The original QM-01 manifests remain historical
inputs and must not be rewritten into an invented fresh baseline.

For the two scorecard outputs, compare invariant text, aggregate identity,
selected executable test links and semantic-completeness claims independently
of grading/topology numbers. Batch, PipelineRun and QuarantineEntry claims must
not weaken. A generator run is not a scientific proof of semantic completeness.

Curated/episodic memory and pipeline data are outside this refresh. Rebuild only
materialized memory projections if required by their owning mechanism; do not
rebuild them solely because another report changed.

### Squash-safe publication provenance

When repository policy requires squash, preserve the published branch and its
full Git objects. Normal ancestor checks remain unchanged. A pinned source that
is no longer a main ancestor requires a reviewed publication receipt plus a
read-only GitHub lookup confirming the actual merge, identical published/merged
trees, source ancestry within the published head, and merge ancestry within the
current checkout. Missing objects, an unmerged PR, API failure or changed inputs
fail closed. This bridge does not replace source, semantic, acquisition or
physical artifact checks.

After promoting the real successful coverage/duration artifacts from the last
source candidate, materialize the bridge while that candidate is the published
PR head:

```bash
python -m scripts.engineering.ci.test_telemetry_provenance --ci-run-id <actual-Nightly-run-id> --pull-request <epic-PR-number>
```

The native writer checks producer identity, both producer job results and the
unchanged `TEST_INPUTS`. It writes two active outputs atomically per file:
`reports/test-telemetry/squash-provenance.json` for captured measurements and
`reports/quality/quality-move-qm08/publication-provenance.json` for the exact
catalog/build source refs. Preserve prior before-bytes. The publication receipt
remains independent of future telemetry refreshes. A pending receipt records no
future merge SHA and grants no acceptance; the actual merge is resolved only
after GitHub reports it. Do not narrow `TEST_INPUTS`, restamp captured run IDs or
treat the overall producer workflow's FAIL as PASS.

Make only metadata changes after this capture; source/input changes require a
new capture. Run the owning read-only checks and final CI on the resulting head.
After merge, repeat the affected ancestry/source checks on the actual main tree.
Full history must include the preserved publication branch/PR objects; a source
object's absence is missing evidence, not permission to accept a tree alias.

## Verification

After the last writer, record all tracked working-byte hashes and run the
applicable check modes plus owning tests. Compare before/after hashes: the check
pass must create no tracked diff. Capture actual argv/cwd, interpreter and tool
versions, source/input fingerprints, raw logs and exit codes. Keep failed and
skipped checks as such. Commit the complete coherent tree in the owned branch.
Check the evidence family again after the final debt rollup; a successful earlier
rebind does not prove the final audit-registry hash is current.

Fetch main again before finalization and integrate only into the owned branch;
recheck changed inputs if integration moved the candidate. Transfer exact
commit/tree and artifact hashes to QM-09. Lifecycle acceptance, remote CI and
publication are separate steps; a green workflow alone is not ADMIT. Follow
the [generated-artifact drift workflow](generated-artifact-drift-workflow.md)
and the [testing guide](../../03-guides/testing.md).

## Rollback/Recovery

Preserve the failed run and its receipts before correcting inputs. Recover only
owned active outputs from the recorded before-bytes or an identified Git revision,
then rerun their supported writers. Do not reset unrelated worktrees or replace
historical evidence with a regenerated result.

## Post-incident

Record the actual failed command, input identity, correction and subsequent
check result. Transfer current fingerprints and unresolved limitations to QM-09.

## Compliance

Follow [project rules](../../00-project/RULES.md) and the
[generated-artifact drift workflow](generated-artifact-drift-workflow.md).
Preserve debt budgets, historical measurement history and publication ownership.
