# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for EffectiveConfigSerializer with DQ support."""

from __future__ import annotations

import pytest

import json
from datetime import datetime
from typing import Any


from bioetl.composition.services.effective_config_serializer import (
    EffectiveConfigSerializer,
    create_effective_config_serializer,
)
from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigResolutionPolicy,
    ConfigSourceRef,
    DQPolicySnapshot,
    EffectiveConfigArtifact,
    EffectiveConfigHashes,
    EffectiveExecutionConfig,
    ResolvedConfigSnapshot,
    RuntimeOverrideSnapshot,
)
from bioetl.domain.types.dq_contracts import DQDisposition, DQPolicyRef


pytestmark = pytest.mark.unit


class TestEffectiveConfigSerializer:
    """Tests for EffectiveConfigSerializer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.serializer = create_effective_config_serializer()
        self.test_timestamp = datetime(2023, 1, 1, 12, 0, 0)

    def test_serializer_creation(self) -> None:
        """Test serializer factory function."""
        serializer = create_effective_config_serializer()
        assert isinstance(serializer, EffectiveConfigSerializer)

    def test_serialize_simple_artifact(self) -> None:
        """Test serialization of a simple artifact."""
        # Create minimal artifact
        artifact = EffectiveConfigArtifact(
            artifact_id="test_artifact",
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            source_refs=[],
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard", config_data={}, config_hash="resolved_hash"
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={}, effective_hash="effective_hash"
            ),
            resolved_config_hash="resolved_hash",
            effective_config_hash="effective_hash",
            source_fingerprint="source_fingerprint",
        )

        # Serialize
        json_str = self.serializer.serialize_artifact(artifact)

        # Verify it's valid JSON
        parsed = json.loads(json_str)
        assert parsed["artifact_id"] == "test_artifact"
        semantic = parsed["semantic_artifact"]
        assert semantic["pipeline_name"] == "test_pipeline"
        assert semantic["pipeline_kind"] == "standard"
        assert "occurrence_envelope" in parsed

    def test_serialize_artifact_with_sources(self) -> None:
        """Test serialization with source references."""
        source_refs = [
            ConfigSourceRef(
                source_type="file",
                source_path="configs/base/pipeline.yaml",
                source_hash="base_hash",
                priority=1,
            ),
            ConfigSourceRef(
                source_type="file",
                source_path="configs/providers/chembl.yaml",
                source_hash="provider_hash",
                priority=2,
            ),
        ]

        artifact = EffectiveConfigArtifact(
            artifact_id="test_artifact",
            pipeline_name="chembl_molecule",
            pipeline_kind="standard",
            source_refs=source_refs,
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard",
                config_data={"pipeline": {"name": "chembl_molecule"}},
                config_hash="resolved_hash",
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={
                    "pipeline": {"name": "chembl_molecule", "batch_size": 1000}
                },
                effective_hash="effective_hash",
            ),
            resolved_config_hash="resolved_hash",
            effective_config_hash="effective_hash",
            source_fingerprint="source_fingerprint",
        )

        # Serialize
        json_str = self.serializer.serialize_artifact(artifact)
        parsed = json.loads(json_str)

        # Verify source refs
        semantic = parsed["semantic_artifact"]
        assert len(semantic["source_refs"]) == 2
        assert semantic["source_refs"][0]["source_path"] == "configs/base/pipeline.yaml"
        assert (
            semantic["source_refs"][1]["source_path"] == "configs/providers/chembl.yaml"
        )

    def test_serialize_artifact_with_dq_policies(self) -> None:
        """Test serialization with DQ policy integration."""
        dq_policy_refs = [
            DQPolicyRef(
                contract_ref="chembl_molecule",
                contract_version="1.0.0",
                rule_bundle_version="1.0.0",
                policy_hash="dq_hash_abc",
            )
        ]

        dq_snapshots = [
            DQPolicySnapshot(
                contract_ref="chembl_molecule",
                contract_version="1.0.0",
                rule_bundle_version="1.0.0",
                policy_hash="dq_hash_abc",
                default_disposition=DQDisposition.WARN,
                disposition_overrides={
                    "schema.molecule_id": DQDisposition.FAIL,
                    "schema.assay_id": DQDisposition.QUARANTINE,
                },
                strictness_mode="strict",
            )
        ]

        artifact = EffectiveConfigArtifact(
            artifact_id="test_artifact",
            pipeline_name="chembl_molecule",
            pipeline_kind="standard",
            source_refs=[],
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard", config_data={}, config_hash="resolved_hash"
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={}, effective_hash="effective_hash"
            ),
            resolved_config_hash="resolved_hash",
            effective_config_hash="effective_hash",
            source_fingerprint="source_fingerprint",
            dq_policy_refs=dq_policy_refs,
            dq_policy_snapshots=dq_snapshots,
        )

        # Serialize
        json_str = self.serializer.serialize_artifact(artifact)
        parsed = json.loads(json_str)

        # Verify DQ policy refs
        semantic = parsed["semantic_artifact"]
        assert len(semantic["dq_policy_refs"]) == 1
        assert semantic["dq_policy_refs"][0]["contract_ref"] == "chembl_molecule"

        # Verify DQ policy snapshots
        assert len(semantic["dq_policy_snapshots"]) == 1
        snapshot = semantic["dq_policy_snapshots"][0]
        assert snapshot["contract_ref"] == "chembl_molecule"
        assert snapshot["default_disposition"] == "warn"
        assert len(snapshot["disposition_overrides"]) == 2
        assert snapshot["disposition_overrides"]["schema.molecule_id"] == "fail"

    def test_serialize_artifact_with_normalization_profile_identity(self) -> None:
        """Semantic payload should expose normalization profile identity."""
        artifact = EffectiveConfigArtifact(
            artifact_id="test_artifact",
            pipeline_name="pubchem_compound",
            pipeline_kind="standard",
            source_refs=[],
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard",
                config_data={},
                config_hash="resolved_hash",
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={},
                effective_hash="effective_hash",
            ),
            resolved_config_hash="resolved_hash",
            effective_config_hash="effective_hash",
            source_fingerprint="source_fingerprint",
            normalization_profile_ref="pubchem.compound",
            normalization_profile_version="1.0.0",
            normalization_profile_hash="a" * 64,
        )

        parsed = json.loads(self.serializer.serialize_artifact(artifact))
        semantic = parsed["semantic_artifact"]

        assert semantic["normalization_profile_ref"] == "pubchem.compound"
        assert semantic["normalization_profile_version"] == "1.0.0"
        assert semantic["normalization_profile_hash"] == "a" * 64

    def test_deterministic_serialization(self) -> None:
        """Test that serialization is deterministic (same input = same output)."""
        # Create two identical artifacts with fixed timestamps
        source_refs = [
            ConfigSourceRef(
                source_type="file",
                source_path="configs/base/pipeline.yaml",
                source_hash="base_hash",
                priority=1,
            )
        ]

        config_data: dict[str, Any] = {
            "pipeline": {"name": "test"},
            "settings": {"batch_size": 1000, "timeout": 30},
        }

        fixed_timestamp = datetime(2023, 1, 1, 12, 0, 0)

        artifact1 = EffectiveConfigArtifact(
            artifact_id="test_artifact",
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            source_refs=source_refs,
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard",
                config_data=config_data,
                config_hash="resolved_hash",
                timestamp=fixed_timestamp,
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data=config_data,
                effective_hash="effective_hash",
                timestamp=fixed_timestamp,
            ),
            resolved_config_hash="resolved_hash",
            effective_config_hash="effective_hash",
            source_fingerprint="source_fingerprint",
            created_at=fixed_timestamp,
        )

        artifact2 = EffectiveConfigArtifact(
            artifact_id="test_artifact",
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            source_refs=source_refs,
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard",
                config_data=config_data,
                config_hash="resolved_hash",
                timestamp=fixed_timestamp,
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data=config_data,
                effective_hash="effective_hash",
                timestamp=fixed_timestamp,
            ),
            resolved_config_hash="resolved_hash",
            effective_config_hash="effective_hash",
            source_fingerprint="source_fingerprint",
            created_at=fixed_timestamp,
        )

        # Serialize both
        json1 = self.serializer.serialize_artifact(artifact1)
        json2 = self.serializer.serialize_artifact(artifact2)

        # Should be identical
        assert json1 == json2

    def test_compute_artifact_hashes(self) -> None:
        """Test computation of artifact hashes."""
        source_refs = [
            ConfigSourceRef(
                source_type="file",
                source_path="configs/base/pipeline.yaml",
                source_hash="base_hash",
                priority=1,
            )
        ]

        artifact = EffectiveConfigArtifact(
            artifact_id="test_artifact",
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            source_refs=source_refs,
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard",
                config_data={"pipeline": {"name": "test"}},
                config_hash="resolved_hash",
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={"pipeline": {"name": "test", "batch_size": 1000}},
                effective_hash="effective_hash",
            ),
            resolved_config_hash="resolved_hash",
            effective_config_hash="effective_hash",
            source_fingerprint="source_fingerprint",
        )

        # Compute hashes
        hashes = self.serializer.compute_artifact_hashes(artifact)

        # Verify hash structure
        assert isinstance(hashes, EffectiveConfigHashes)
        assert hashes.resolved_config_hash
        assert hashes.effective_config_hash
        assert hashes.source_fingerprint
        assert hashes.dq_contract_compatibility_hash

        # Verify hash lengths (SHA256)
        assert len(hashes.resolved_config_hash) == 64
        assert len(hashes.effective_config_hash) == 64
        assert len(hashes.source_fingerprint) == 64

    def test_compute_dq_compatibility_hash(self) -> None:
        """Test DQ compatibility hash computation."""
        # Test with no DQ policies
        artifact_no_dq = EffectiveConfigArtifact(
            artifact_id="test",
            pipeline_name="test",
            pipeline_kind="standard",
            source_refs=[],
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard", config_data={}, config_hash="hash"
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={}, effective_hash="hash"
            ),
            resolved_config_hash="hash",
            effective_config_hash="hash",
            source_fingerprint="fingerprint",
        )

        dq_hash_no_policies = self.serializer._compute_dq_compatibility_hash(
            artifact_no_dq
        )
        assert dq_hash_no_policies == "no_dq_policies"

        # Test with DQ policies
        dq_policy_refs = [
            DQPolicyRef(
                contract_ref="contract1",
                contract_version="1.0.0",
                rule_bundle_version="1.0.0",
                policy_hash="hash1",
            ),
            DQPolicyRef(
                contract_ref="contract2",
                contract_version="2.0.0",
                rule_bundle_version="2.0.0",
                policy_hash="hash2",
            ),
        ]

        dq_snapshots = [
            DQPolicySnapshot(
                contract_ref="contract1",
                contract_version="1.0.0",
                rule_bundle_version="1.0.0",
                policy_hash="hash1",
                default_disposition=DQDisposition.WARN,
            )
        ]

        artifact_with_dq = EffectiveConfigArtifact(
            artifact_id="test",
            pipeline_name="test",
            pipeline_kind="standard",
            source_refs=[],
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard", config_data={}, config_hash="hash"
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={}, effective_hash="hash"
            ),
            resolved_config_hash="hash",
            effective_config_hash="hash",
            source_fingerprint="fingerprint",
            dq_policy_refs=dq_policy_refs,
            dq_policy_snapshots=dq_snapshots,
        )

        dq_hash_with_policies = self.serializer._compute_dq_compatibility_hash(
            artifact_with_dq
        )
        assert dq_hash_with_policies != "no_dq_policies"
        assert len(dq_hash_with_policies) == 64  # SHA256 hash

    def test_source_fingerprint_computation(self) -> None:
        """Test source fingerprint computation."""
        # Test with no sources
        fingerprint_no_sources = self.serializer._compute_source_fingerprint([])
        assert fingerprint_no_sources == "no_sources"

        # Test with sources
        source_refs = [
            ConfigSourceRef(
                source_type="file",
                source_path="configs/base/pipeline.yaml",
                source_hash="base_hash",
                priority=1,
            ),
            ConfigSourceRef(
                source_type="file",
                source_path="configs/providers/chembl.yaml",
                source_hash="provider_hash",
                priority=2,
            ),
        ]

        fingerprint_with_sources = self.serializer._compute_source_fingerprint(
            source_refs
        )
        assert fingerprint_with_sources != "no_sources"
        assert len(fingerprint_with_sources) == 64  # SHA256 hash

    def test_config_data_normalization(self) -> None:
        """Test configuration data normalization."""
        # Test with nested dicts and different key ordering
        config_data1 = {
            "settings": {"batch_size": 1000, "timeout": 30},
            "pipeline": {"name": "test", "version": "1.0"},
        }

        config_data2 = {
            "pipeline": {"version": "1.0", "name": "test"},
            "settings": {"timeout": 30, "batch_size": 1000},
        }

        normalized1 = self.serializer._normalize_config_data(config_data1)
        normalized2 = self.serializer._normalize_config_data(config_data2)

        # Should be identical after normalization
        assert normalized1 == normalized2

        # Should have sorted keys
        keys = list(normalized1.keys())
        assert keys == sorted(keys)

    def test_dq_disposition_normalization(self) -> None:
        """Test DQ disposition enum normalization."""
        config_data = {
            "dq_settings": {
                "default_disposition": DQDisposition.WARN,
                "overrides": {"schema.critical": DQDisposition.FAIL},
            }
        }

        normalized = self.serializer._normalize_config_data(config_data)

        # Enums should be converted to their string values
        assert normalized["dq_settings"]["default_disposition"] == "warn"
        assert normalized["dq_settings"]["overrides"]["schema.critical"] == "fail"

    def test_serialization_stability(self) -> None:
        """Test that serialization produces stable output across multiple runs."""
        # Create a complex artifact
        source_refs = [
            ConfigSourceRef(
                source_type="file",
                source_path="configs/base/pipeline.yaml",
                source_hash="base_hash",
                priority=1,
            )
        ]

        config_data: dict[str, Any] = {
            "pipeline": {"name": "test", "version": "1.0"},
            "settings": {
                "batch_size": 1000,
                "timeout": 30,
                "retry_policy": {"max_attempts": 3, "backoff": "exponential"},
            },
        }

        dq_snapshots = [
            DQPolicySnapshot(
                contract_ref="test_contract",
                contract_version="1.0.0",
                rule_bundle_version="1.0.0",
                policy_hash="test_hash",
                default_disposition=DQDisposition.WARN,
                disposition_overrides={
                    "schema.required_field": DQDisposition.FAIL,
                    "threshold.performance": DQDisposition.QUARANTINE,
                },
            )
        ]

        artifact = EffectiveConfigArtifact(
            artifact_id="test_artifact",
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            source_refs=source_refs,
            resolution_policy=ConfigResolutionPolicy(
                merge_strategy="hierarchical", default_materialization=True
            ),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard",
                config_data=config_data,
                config_hash="resolved_hash",
            ),
            runtime_overrides=RuntimeOverrideSnapshot(
                cli_overrides={"batch_size": 2000}, override_hash="override_hash"
            ),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={
                    **config_data,
                    "settings": {**config_data["settings"], "batch_size": 2000},
                },
                effective_hash="effective_hash",
            ),
            resolved_config_hash="resolved_hash",
            effective_config_hash="effective_hash",
            source_fingerprint="source_fingerprint",
            dq_policy_snapshots=dq_snapshots,
        )

        # Serialize multiple times
        json_results = [self.serializer.serialize_artifact(artifact) for _ in range(3)]

        # All should be identical
        assert len(set(json_results)) == 1

        # Should be valid JSON
        parsed = json.loads(json_results[0])
        assert parsed["artifact_id"] == "test_artifact"
        assert (
            parsed["semantic_artifact"]["dq_policy_snapshots"][0]["default_disposition"]
            == "warn"
        )

    def test_semantic_serialization_ignores_occurrence_timestamps(self) -> None:
        """Semantic serialization should stay stable across occurrence timestamps."""
        artifact1 = EffectiveConfigArtifact(
            artifact_id="test_artifact",
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            source_refs=[],
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard",
                config_data={"pipeline": {"name": "test"}},
                config_hash="resolved_hash",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={"pipeline": {"name": "test"}},
                effective_hash="effective_hash",
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
            ),
            resolved_config_hash="resolved_hash",
            effective_config_hash="effective_hash",
            source_fingerprint="source_fingerprint",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        artifact2 = EffectiveConfigArtifact(
            artifact_id="test_artifact",
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            source_refs=[],
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard",
                config_data={"pipeline": {"name": "test"}},
                config_hash="resolved_hash",
                timestamp=datetime(2025, 1, 1, 12, 0, 0),
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={"pipeline": {"name": "test"}},
                effective_hash="effective_hash",
                timestamp=datetime(2025, 1, 1, 12, 0, 0),
            ),
            resolved_config_hash="resolved_hash",
            effective_config_hash="effective_hash",
            source_fingerprint="source_fingerprint",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
        )

        assert self.serializer.serialize_semantic_artifact(
            artifact1
        ) == self.serializer.serialize_semantic_artifact(artifact2)

    def test_runtime_override_serialization_omits_empty_override_sections(self) -> None:
        """Empty runtime-override sections must not imply captured provenance."""
        artifact = EffectiveConfigArtifact(
            artifact_id="test_artifact",
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            source_refs=[],
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard",
                config_data={"pipeline": {"name": "test"}},
                config_hash="resolved_hash",
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={"pipeline": {"name": "test"}},
                effective_hash="effective_hash",
            ),
            resolved_config_hash="resolved_hash",
            effective_config_hash="effective_hash",
            source_fingerprint="source_fingerprint",
        )

        parsed = json.loads(self.serializer.serialize_artifact(artifact))

        assert parsed["semantic_artifact"]["runtime_overrides"] == {}


class TestHashDeterminism:
    """Tests for hash determinism and stability."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.serializer = create_effective_config_serializer()

    def test_hash_stability_across_runs(self) -> None:
        """Test that hashes are stable across multiple computations."""
        # Create identical artifacts
        artifact1 = self._create_test_artifact("test1")
        artifact2 = self._create_test_artifact("test1")

        # Compute hashes
        hashes1 = self.serializer.compute_artifact_hashes(artifact1)
        hashes2 = self.serializer.compute_artifact_hashes(artifact2)

        # Should be identical
        assert hashes1.resolved_config_hash == hashes2.resolved_config_hash
        assert hashes1.effective_config_hash == hashes2.effective_config_hash
        assert hashes1.source_fingerprint == hashes2.source_fingerprint

    def test_hash_differences_for_different_configs(self) -> None:
        """Test that different configs produce different hashes."""
        artifact1 = self._create_test_artifact("test1")
        artifact2 = self._create_test_artifact("test2")  # Different name

        hashes1 = self.serializer.compute_artifact_hashes(artifact1)
        hashes2 = self.serializer.compute_artifact_hashes(artifact2)

        # Should be different
        assert hashes1.effective_config_hash != hashes2.effective_config_hash

    def test_hash_insensitive_to_field_ordering(self) -> None:
        """Test that hashes are insensitive to field ordering in config data."""
        # Create artifacts with same data but different field ordering
        config_data1 = {"a": 1, "b": {"x": 10, "y": 20}}
        config_data2 = {"b": {"y": 20, "x": 10}, "a": 1}

        artifact1 = self._create_test_artifact_with_config("test", config_data1)
        artifact2 = self._create_test_artifact_with_config("test", config_data2)

        hashes1 = self.serializer.compute_artifact_hashes(artifact1)
        hashes2 = self.serializer.compute_artifact_hashes(artifact2)

        # Should produce same hashes despite different field ordering
        assert hashes1.resolved_config_hash == hashes2.resolved_config_hash

    def _create_test_artifact(self, artifact_id: str) -> EffectiveConfigArtifact:
        """Helper to create a test artifact."""
        fixed_timestamp = datetime(2023, 1, 1, 12, 0, 0)
        return EffectiveConfigArtifact(
            artifact_id=artifact_id,
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            source_refs=[],
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard",
                config_data={"pipeline": {"name": artifact_id}},
                config_hash=f"resolved_{artifact_id}",
                timestamp=fixed_timestamp,
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data={"pipeline": {"name": artifact_id, "id": artifact_id}},
                effective_hash=f"effective_{artifact_id}",
                timestamp=fixed_timestamp,
            ),
            resolved_config_hash=f"resolved_{artifact_id}",
            effective_config_hash=f"effective_{artifact_id}",
            source_fingerprint=f"source_{artifact_id}",
            created_at=fixed_timestamp,
        )

    def _create_test_artifact_with_config(
        self, artifact_id: str, config_data: dict[str, Any]
    ) -> EffectiveConfigArtifact:
        """Helper to create a test artifact with specific config data."""
        fixed_timestamp = datetime(2023, 1, 1, 12, 0, 0)
        return EffectiveConfigArtifact(
            artifact_id=artifact_id,
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            source_refs=[],
            resolution_policy=ConfigResolutionPolicy(),
            resolved_config=ResolvedConfigSnapshot(
                config_type="standard",
                config_data=config_data,
                config_hash=f"resolved_{artifact_id}",
                timestamp=fixed_timestamp,
            ),
            runtime_overrides=RuntimeOverrideSnapshot(),
            effective_execution_config=EffectiveExecutionConfig(
                config_data=config_data,
                effective_hash=f"effective_{artifact_id}",
                timestamp=fixed_timestamp,
            ),
            resolved_config_hash=f"resolved_{artifact_id}",
            effective_config_hash=f"effective_{artifact_id}",
            source_fingerprint=f"source_{artifact_id}",
            created_at=fixed_timestamp,
        )
