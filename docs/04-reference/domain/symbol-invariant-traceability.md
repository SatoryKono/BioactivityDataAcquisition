______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-23'

______________________________________________________________________

# Domain Symbol-to-Invariant Traceability

## Scope and evidence

This page classifies every symbol exported by the public aggregate,
value-object, and control-plane facades. The export lists in
`src/bioetl/domain/{aggregates,value_objects,control_plane}/__init__.py` are the
mechanically checked inventory. Detailed invariant text remains owned by
[aggregates.md](aggregates.md), [invariants.md](invariants.md),
[aggregate-state-machines.md](aggregate-state-machines.md), and
[control-plane.md](control-plane.md).

The authoritative aggregate invariant and test anchors are also published in
`reports/quality/domain-aggregate-invariant-registry.json`.

## Aggregate facade

| Symbol | Classification | Invariant / lifecycle owner | Event and test evidence |
| --- | --- | --- | --- |
| `Batch` | aggregate root | immutable `batch_id`; controlled add/process/complete/fail transitions | `BatchCompleted`; `tests/unit/domain/aggregates/test_batch.py` |
| `BatchRecord` | aggregate child | belongs to one batch and follows record status transitions | emitted through `Batch`; `tests/unit/domain/aggregates/test_batch.py` |
| `BatchStatus` | state enum | legal batch lifecycle vocabulary | `tests/unit/domain/aggregates/test_batch.py` |
| `PipelineRun` | aggregate root | legal run/stage transitions and terminal-state consistency | `PipelineRunStarted`, `PipelineRunCompleted`, `PipelineRunFailed`; `tests/unit/domain/aggregates/test_pipeline_run.py` |
| `PipelineRunState` | state enum | legal run lifecycle vocabulary | `tests/unit/domain/aggregates/test_pipeline_run.py` |
| `StageResult` | aggregate child/value | immutable stage outcome attached to its run | emitted through `PipelineRun`; `tests/unit/domain/aggregates/test_pipeline_run.py` |
| `StageStatus` | state enum | legal stage lifecycle vocabulary | `tests/unit/domain/aggregates/test_pipeline_run.py` |
| `QuarantineEntry` | aggregate root | immutable payload identity; legal review/resolve/ignore transitions | `RecordQuarantined`, `QuarantineResolved`; `tests/unit/domain/aggregates/test_quarantine_entry.py` |
| `QuarantineStatus` | state enum | legal quarantine lifecycle vocabulary | `tests/unit/domain/aggregates/test_quarantine_entry.py` |

## Value-object facade

All entries below are immutable value objects, constrained enums, domain
errors, or pure validators. Their constructor/validation rules are owned by
the named source modules and tested under
`tests/unit/domain/value_objects/`.

| Source family | Public symbols |
| --- | --- |
| Base | `ValueObject` |
| Academic identifiers | `ISSN`, `ORCID`, `OpenAlexId`, `SemanticScholarId` |
| Publication identifiers | `DOI`, `PubMedId` |
| Provider identifiers | `AssayId`, `ChemblId`, `CompoundId`, `CompoundSource`, `PubChemCid`, `UniProtId` |
| Chemical identifiers | `InChI`, `InChIKey`, `SMILES` |
| Activity semantics | `ActivityType`, `ActivityValue`, `Concentration`, `ConcentrationUnit`, `ConfidenceScore`, `PChemblValue`, `RelationOperator` |
| Chemical descriptors | `HeavyAtomCount`, `HydrogenBondCount`, `LogP`, `MolecularWeight`, `PolarSurfaceArea`, `PublicationYear`, `RotatableBondCount` |
| DQ semantics | `DQAnomaly`, `DQAnomalySeverity`, `DQAnomalyType`, `DQEvaluationStatus` |
| Protein classification | `ProteinClassHierarchy`, `ProteinClassLevel`, `ProteinClassificationResolutionError` |
| Taxonomy | `TaxonomyId`, `validate_taxonomy_id` |

## Control-plane facade

The models below are immutable provenance/state values unless explicitly
classified as a policy or pure resolver. Their cross-cutting invariants are:
manifest identity is stable, ledger entries are append-only, effective
configuration is snapshot-backed, and replay readiness is derived only from
persisted evidence.

| Classification | Public symbols | Code and test anchors |
| --- | --- | --- |
| Run provenance and ledger state | `ReplayCapability`, `RunArtifactRef`, `RunCodeProvenance`, `RunInputSnapshotRef`, `RunLedgerEntry`, `RunManifest`, `RunSourceRef` | `src/bioetl/domain/control_plane/run_manifest.py`; `src/bioetl/domain/control_plane/run_ledger.py`; `tests/unit/domain/control_plane/` |
| Workflow state | `WorkflowExecutionState`, `WorkflowLedgerEntry`, `WorkflowManifest`, `WorkflowManifestStep`, `WorkflowStepState` | `src/bioetl/domain/control_plane/workflow_*.py`; `tests/unit/domain/control_plane/` |
| Effective-config state | `ConfigResolutionPolicy`, `ConfigSourceRef`, `DQPolicySnapshot`, `EffectiveConfigArtifact`, `EffectiveConfigHashes`, `EffectiveExecutionConfig`, `ExecutionEnvironmentSnapshot`, `ResolvedConfigSnapshot`, `RuntimeOverrideSnapshot`, `SourceClassProvenance` | `src/bioetl/domain/control_plane/effective_config_artifact.py`; `tests/unit/domain/control_plane/` |
| Artifact lifecycle state/policy | `ControlPlaneArtifactLifecycleApplyResult`, `ControlPlaneArtifactLifecycleDecision`, `ControlPlaneArtifactLifecyclePlan`, `ControlPlaneArtifactLifecyclePolicy`, `ControlPlaneArtifactRef`, `ControlPlaneArtifactReplayImpact`, `ControlPlaneArtifactSurface`, `ControlPlaneArtifactResolutionIssue`, `ControlPlaneArtifactResolutionIssueCode` | `src/bioetl/domain/control_plane/artifact_lifecycle.py`; `tests/unit/domain/control_plane/` |
| Reproducibility state | `ReplayReadinessVerdict`, `ReproducibilityFamilyProfile`, `ReproducibilityPolicyAssessment`, `SnapshotEnvelopeStatus` | `src/bioetl/domain/control_plane/reproducibility_*.py`; `tests/unit/domain/control_plane/` |
| Pure policy/resolver functions | `assess_reproducibility_policy`, `build_lineage_closure_boundary`, `build_replay_family_contract`, `build_snapshot_envelope_status`, `normalize_required_persistence_profile`, `published_production_reproducibility_families`, `published_supported_reproducibility_families`, `registered_reproducibility_families`, `registered_reproducibility_family_inventory`, `resolve_replay_capability`, `resolve_replay_readiness_verdict`, `resolve_reproducibility_family`, `resolve_reproducibility_family_profile` | `src/bioetl/domain/control_plane/reproducibility_policy.py`; `src/bioetl/domain/control_plane/reproducibility_profiles.py`; `tests/unit/domain/control_plane/` |

## Mechanical drift guard

`tests/architecture/test_documentation_issues_6497_6498_closeout.py` fails when
a public facade export is missing from this page or when aggregate registry
source/test anchors stop resolving. New exports therefore require an explicit
classification in the same change.
