# RF-004 / RF-005 reference-based decisions

Reviewed source: `d50ecd5f35bd9d243702f2bcbfabbaaabdecaa1a` (2026-10-01).
Scope: #11849 and #11850, after RF-003 moved replay snapshot selection to
Application. This is a bounded candidate review, not a claim that all
forwarding in the repository has been eliminated.

## Composition and Core candidates

| Candidate | Callers / compatibility evidence | Owner | Decision | Measurable effect |
| --- | --- | --- | --- | --- |
| `composition/runtime_builders/run_manifest_support.py` | `run_manifest_builder.py`, `_run_manifest_creation_support_helpers.py`, `factories/pipeline/run_context_contract_identity.py`; `test_run_manifest_support.py`, `test_run_manifest_builder.py` | Composition manifest assembly; 14 public exports including provenance bundle | Retain. It creates a typed provenance bundle and preserves public import/patch surfaces. Removing the facade alone redistributes imports without removing assembly policy. | No module, LOC, fan-in or budget change for this candidate. |
| `composition/runtime_builders/_run_manifest_refs.py` | `run_manifest_support.py`; `test_run_manifest_refs_lazy_facade.py`, `test_reproducible_sink_modes.py` | Composition source refs and persistence-profile enforcement | Retain pending coordinated public-surface migration. Its source-ref construction is policy-bearing; root/artifact forwarding is compatibility-tested. Existing dynamic imports are a limitation of static fan-in evidence, not evidence of reduced runtime coupling. | No new deferred imports, wrappers or exemptions. RF-003 separately removed selection policy from Composition. |
| `composition/runtime_builders/_run_manifest_control_plane_refs.py` | `_run_manifest_refs.py` via `create_control_plane_refs`; control-plane and manifest builder tests | Composition persisted fingerprint/contract identity refs | Retain: it assembles multiple concrete stores and refs; not an empty forwarding hop. | No module/LOC growth or transferred helper complexity. |
| `application/core/quarantine_manager.py` | `batch_transformer.py`, `batch_transformer_quarantine.py`, `_batch_write_schema_quarantine.py`, `core/wiring/runtime.py`, `factories/services/pipeline_processing_components_builder.py`; `test_quarantine_manager.py` | Application runtime quarantine writes; operator inspection/purge remains in `application/services/quarantine_service.py` | Retain explicit-dependency constructor and value-object exports. It assembles fallback metrics behavior and is a stable injection/patch surface. | No new service or helper. Existing fan-in is not by itself an SRP defect. |

Decision: motivated **no-change** for these four candidates. No arbitrary
250-module or fan-in 2/4 target is imposed. A safe future collapse must migrate
all public imports and patch points together and prove a reduction in hops or
duplication; renaming or dynamic-import substitution does not qualify.

## Script candidates

Reference search covered `src`, `scripts`, `tests`, `.github`, docs, root build
files and `configs/quality/scripts_lifecycle_registry.json` / inventory manifest.
The committed input inventory contains 637 scripts: 339 active and 298 supporting; live regeneration finds 638 / 340 / 298 due to the inherited `_replay_layout.py`. These
are the inherited snapshot counts, not a newly accepted budget. This review
adds no script and changes no lifecycle status.

| Candidate | References | Replacement / owner | Decision and effect |
| --- | --- | --- | --- |
| `scripts/docs_parity_check.py` | `scripts/documentation_governance_check.py`, `tests/unit/scripts/docs/test_docs_parity_check.py` | Active config/spec gate: `python -m scripts.data_quality check-entity-config-parity`; legacy governance report has different output | Remove its recommendation from the published parity guide; preserve executable for compatibility. Zero scripts retired; no fake active-to-supporting transition. |
| `scripts/documentation_governance_check.py` | `tests/unit/scripts/test_documentation_governance_check.py`, legacy governance imports | Existing governance report API; external callers unknown | Retain non-CI entrypoint. Deletion is not justified by absence from workflow YAML. |
| `scripts/docker-setup.ps1` and `scripts/docker-setup.sh` | `startup.ps1`, `shutdown.ps1`, `startup.sh`, `shutdown.sh`, runtime docs and architecture wrapper tests | Platform wrappers delegate to existing operational implementation | Retain platform boundary, argument forwarding and exit-code semantics. No new universal wrapper. |
| `scripts/diagrams/fix_mermaid_operators.py` (former root duplicate) | Current router targets `scripts/diagrams/fix/fix_mermaid_operators.py` | `python -m scripts.diagrams fix-operators` | Already removed upstream before this review. Correct remaining README path; do not count upstream removal as a new retirement. |

Two private single-caller implementations were consolidated after the live cap failure: `_overall_verdict.py` into its only owner `_run_explorer_columns.py`, and `_stage_removal_columns.py` into `_provider_evidence_columns.py`, which already owns saved-report table projections. `render_nav_bus.py` now imports the latter directly. Bodies and callable names are preserved; there are no CLI entrypoints or test patch references to either retired module. This removes two files and two import dependencies, returning active count from 340 to 338 without changing statuses or caps. Unknown external public entrypoints above remain. There is
no evidence supporting a forced active-script target of 320. Canonical
inventory synchronization and catalog/lifecycle/zero-reference tests are
required before closing #11850; a failing inherited cap is a blocker, not a
reason to relabel scripts or increase the cap.

## Validation evidence

Commands and final exit codes are attached to the corresponding GitHub issues
with the final source SHA. This decision document does not pre-assert their
outcome. Relevant checks: hotspot fan-in/growth/duplication ratchets,
`test_di_compliance.py`, quarantine and manifest caller tests, scripts catalog,
inventory, zero-reference and lifecycle contracts, and existing router help.
