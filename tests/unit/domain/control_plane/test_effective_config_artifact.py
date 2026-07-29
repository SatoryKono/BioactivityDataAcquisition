# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for EffectiveConfigArtifact with DQ integration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

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


class TestConfigSourceRef:
    """Tests for ConfigSourceRef."""

    def test_config_source_ref_creation(self) -> None:
        """Test ConfigSourceRef creation and immutability."""
        source_ref = ConfigSourceRef(
            source_type="file",
            source_path="/config/pipeline.yaml",
            source_hash="abc123",
            raw_source_hash="rawabc123",
            source_hash_strategy="canonical_yaml",
            priority=1,
        )

        assert source_ref.source_type == "file"
        assert source_ref.source_path == "/config/pipeline.yaml"
        assert source_ref.source_hash == "abc123"
        assert source_ref.raw_source_hash == "rawabc123"
        assert source_ref.source_hash_strategy == "canonical_yaml"
        assert source_ref.priority == 1

        # Test immutability
        with pytest.raises(Exception):  # frozen dataclass should prevent modification
            source_ref.source_type = "env"  # type: ignore

    def test_config_source_ref_minimal(self) -> None:
        """Test ConfigSourceRef with minimal fields."""
        source_ref = ConfigSourceRef(
            source_type="default", source_path="internal://defaults"
        )

        assert source_ref.source_type == "default"
        assert source_ref.source_path == "internal://defaults"
        assert source_ref.source_hash is None
        assert source_ref.raw_source_hash is None
        assert source_ref.source_hash_strategy is None
        assert source_ref.priority == 0


class TestConfigResolutionPolicy:
    """Tests for ConfigResolutionPolicy."""

    def test_config_resolution_policy_defaults(self) -> None:
        """Test ConfigResolutionPolicy with default values."""
        policy = ConfigResolutionPolicy()

        assert policy.merge_strategy == "hierarchical"
        assert policy.default_materialization is True
        assert policy.strict_validation is True
        assert policy.allow_runtime_overrides is True

    def test_config_resolution_policy_custom(self) -> None:
        """Test ConfigResolutionPolicy with custom values."""
        policy = ConfigResolutionPolicy(
            merge_strategy="override",
            default_materialization=False,
            strict_validation=False,
            allow_runtime_overrides=False,
        )

        assert policy.merge_strategy == "override"
        assert policy.default_materialization is False
        assert policy.strict_validation is False
        assert policy.allow_runtime_overrides is False


class TestResolvedConfigSnapshot:
    """Tests for ResolvedConfigSnapshot."""

    def test_resolved_config_snapshot_creation(self) -> None:
        """Test ResolvedConfigSnapshot creation."""
        config_data: dict[str, Any] = {
            "pipeline": {"name": "test", "version": "1.0"},
            "settings": {"batch_size": 1000},
        }

        snapshot = ResolvedConfigSnapshot(
            config_type="standard",
            config_data=config_data,
            config_hash="config_hash_123",
        )

        assert snapshot.config_type == "standard"
        assert snapshot.config_data == config_data
        assert snapshot.config_hash == "config_hash_123"
        assert isinstance(snapshot.timestamp, datetime)
        assert snapshot.timestamp.tzinfo == UTC

    def test_resolved_config_snapshot_normalizes_naive_timestamp_to_utc(self) -> None:
        snapshot = ResolvedConfigSnapshot(
            config_type="standard",
            config_data={},
            config_hash="config_hash_123",
            timestamp=datetime(2026, 4, 13, 12, 0, 0),
        )

        assert snapshot.timestamp.tzinfo == UTC


class TestRuntimeOverrideSnapshot:
    """Tests for RuntimeOverrideSnapshot."""

    def test_runtime_override_snapshot_empty(self) -> None:
        """Test RuntimeOverrideSnapshot with empty overrides."""
        snapshot = RuntimeOverrideSnapshot()

        assert snapshot.cli_overrides == {}
        assert snapshot.env_overrides == {}
        assert snapshot.runtime_adjustments == {}
        assert snapshot.override_hash == ""

    def test_runtime_override_snapshot_with_data(self) -> None:
        """Test RuntimeOverrideSnapshot with override data."""
        snapshot = RuntimeOverrideSnapshot(
            cli_overrides={"batch_size": 2000},
            env_overrides={"log_level": "DEBUG"},
            runtime_adjustments={"auto_adjust": True},
            override_hash="override_hash_456",
        )

        assert snapshot.cli_overrides == {"batch_size": 2000}
        assert snapshot.env_overrides == {"log_level": "DEBUG"}
        assert snapshot.runtime_adjustments == {"auto_adjust": True}
        assert snapshot.override_hash == "override_hash_456"


class TestEffectiveExecutionConfig:
    """Tests for EffectiveExecutionConfig."""

    def test_effective_execution_config_creation(self) -> None:
        """Test EffectiveExecutionConfig creation."""
        config_data: dict[str, Any] = {
            "pipeline": {"name": "test", "version": "1.0"},
            "settings": {"batch_size": 2000},  # Overridden value
            "runtime": {"auto_adjust": True},
        }

        config = EffectiveExecutionConfig(
            config_data=config_data, effective_hash="effective_hash_789"
        )

        assert config.config_data == config_data
        assert config.effective_hash == "effective_hash_789"
        assert isinstance(config.timestamp, datetime)
        assert config.timestamp.tzinfo == UTC


class TestDQPolicySnapshot:
    """Tests for DQPolicySnapshot."""

    def test_d_q_policy_snapshot__snapshot_creation__b98d7984(self) -> None:
        """Test DQPolicySnapshot creation."""
        snapshot = DQPolicySnapshot(
            contract_ref="chembl_molecule",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            policy_hash="dq_policy_hash_abc",
            default_disposition=DQDisposition.WARN,
            disposition_overrides={
                "schema.molecule_id": DQDisposition.FAIL,
                "schema.assay_id": DQDisposition.QUARANTINE,
            },
            strictness_mode="strict",
        )

        assert snapshot.contract_ref == "chembl_molecule"
        assert snapshot.contract_version == "1.0.0"
        assert snapshot.rule_bundle_version == "1.0.0"
        assert snapshot.policy_hash == "dq_policy_hash_abc"
        assert snapshot.default_disposition == DQDisposition.WARN
        assert len(snapshot.disposition_overrides) == 2
        assert snapshot.strictness_mode == "strict"

    def test_dq_policy_snapshot_minimal(self) -> None:
        """Test DQPolicySnapshot with minimal fields."""
        snapshot = DQPolicySnapshot(
            contract_ref="test",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            policy_hash="test_hash",
            default_disposition=DQDisposition.PASS,
        )

        assert snapshot.contract_ref == "test"
        assert snapshot.disposition_overrides == {}
        assert snapshot.strictness_mode == "standard"


class TestEffectiveConfigArtifact:
    """Tests for EffectiveConfigArtifact."""

    def test_effective_config_artifact_creation(self) -> None:
        """Test EffectiveConfigArtifact creation with all fields."""
        # Create source refs
        source_refs: list[ConfigSourceRef] = [
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

        # Create resolution policy
        resolution_policy = ConfigResolutionPolicy(
            merge_strategy="hierarchical", default_materialization=True
        )

        # Create resolved config snapshot
        resolved_config = ResolvedConfigSnapshot(
            config_type="standard",
            config_data={"pipeline": {"name": "chembl_molecule"}},
            config_hash="resolved_hash_123",
        )

        # Create runtime overrides
        runtime_overrides = RuntimeOverrideSnapshot(
            cli_overrides={"batch_size": 5000}, override_hash="override_hash_456"
        )

        # Create effective execution config
        effective_config = EffectiveExecutionConfig(
            config_data={"pipeline": {"name": "chembl_molecule", "batch_size": 5000}},
            effective_hash="effective_hash_789",
        )

        # Create DQ policy snapshot
        dq_snapshot = DQPolicySnapshot(
            contract_ref="chembl_molecule",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            policy_hash="dq_hash_abc",
            default_disposition=DQDisposition.WARN,
        )

        # Create DQ policy refs
        dq_policy_refs: list[DQPolicyRef] = [
            DQPolicyRef(
                contract_ref="chembl_molecule",
                contract_version="1.0.0",
                rule_bundle_version="1.0.0",
                policy_hash="dq_hash_abc",
            )
        ]

        # Create the artifact
        artifact = EffectiveConfigArtifact(
            artifact_id="config_artifact_001",
            pipeline_name="chembl_molecule",
            pipeline_kind="standard",
            source_refs=source_refs,
            resolution_policy=resolution_policy,
            resolved_config=resolved_config,
            runtime_overrides=runtime_overrides,
            effective_execution_config=effective_config,
            resolved_config_hash="resolved_hash_123",
            effective_config_hash="effective_hash_789",
            source_fingerprint="source_fingerprint_xyz",
            contract_refs=["chembl_molecule"],
            dq_policy_refs=dq_policy_refs,
            dq_rule_bundle_versions={"chembl_molecule": "1.0.0"},
            dq_policy_snapshots=[dq_snapshot],
        )

        # Verify all fields
        assert artifact.artifact_id == "config_artifact_001"
        assert artifact.pipeline_name == "chembl_molecule"
        assert artifact.pipeline_kind == "standard"
        assert len(artifact.source_refs) == 2
        assert artifact.resolution_policy.merge_strategy == "hierarchical"
        assert artifact.resolved_config.config_hash == "resolved_hash_123"
        assert artifact.effective_config_hash == "effective_hash_789"
        assert artifact.source_fingerprint == "source_fingerprint_xyz"
        assert len(artifact.dq_policy_refs) == 1
        assert len(artifact.dq_policy_snapshots) == 1
        assert artifact.dq_contract_compatibility_hash == "dq_hash_abc"  # Auto-computed
        assert artifact.created_at.tzinfo == UTC

    def test_effective_config_artifact_minimal(self) -> None:
        """Test EffectiveConfigArtifact with minimal required fields."""
        minimal_artifact = EffectiveConfigArtifact(
            artifact_id="minimal_artifact",
            pipeline_name="test_pipeline",
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

        assert minimal_artifact.artifact_id == "minimal_artifact"
        assert minimal_artifact.dq_policy_refs == []
        assert (
            minimal_artifact.dq_contract_compatibility_hash == "no_dq_policies"
        )  # Auto-computed

    def test_effective_config_artifact_validation(self) -> None:
        """Test EffectiveConfigArtifact field validation."""
        with pytest.raises(ValueError, match="artifact_id cannot be empty"):
            EffectiveConfigArtifact(
                artifact_id="",
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

    def test_effective_config_artifact_normalizes_naive_created_at_to_utc(self) -> None:
        artifact = EffectiveConfigArtifact(
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
            created_at=datetime(2026, 4, 13, 12, 0, 0),
        )

        assert artifact.created_at.tzinfo == UTC

        with pytest.raises(ValueError, match="pipeline_name cannot be empty"):
            EffectiveConfigArtifact(
                artifact_id="test",
                pipeline_name="",
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


class TestEffectiveConfigHashes:
    """Tests for EffectiveConfigHashes."""

    def test_effective_config_hashes_creation(self) -> None:
        """Test EffectiveConfigHashes creation."""
        hashes = EffectiveConfigHashes(
            resolved_config_hash="resolved_123",
            effective_config_hash="effective_456",
            source_fingerprint="source_789",
            dq_contract_compatibility_hash="dq_compat_abc",
        )

        assert hashes.resolved_config_hash == "resolved_123"
        assert hashes.effective_config_hash == "effective_456"
        assert hashes.source_fingerprint == "source_789"
        assert hashes.dq_contract_compatibility_hash == "dq_compat_abc"

    def test_effective_config_hashes_validation(self) -> None:
        """Test EffectiveConfigHashes field validation."""
        with pytest.raises(ValueError, match="resolved_config_hash cannot be empty"):
            EffectiveConfigHashes(
                resolved_config_hash="",
                effective_config_hash="hash",
                source_fingerprint="fingerprint",
                dq_contract_compatibility_hash="dq_hash",
            )

        with pytest.raises(ValueError, match="effective_config_hash cannot be empty"):
            EffectiveConfigHashes(
                resolved_config_hash="hash",
                effective_config_hash="",
                source_fingerprint="fingerprint",
                dq_contract_compatibility_hash="dq_hash",
            )


class TestDQIntegration:
    """Tests for DQ integration in EffectiveConfigArtifact."""

    def test_dq_contract_compatibility_hash_auto_computation(self) -> None:
        """Test automatic computation of DQ contract compatibility hash."""
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

        artifact = EffectiveConfigArtifact(
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
        )

        # Should auto-compute compatibility hash from sorted policy hashes
        assert artifact.dq_contract_compatibility_hash == "hash1:hash2"

    def test_dq_contract_compatibility_hash_no_policies(self) -> None:
        """Test DQ contract compatibility hash when no DQ policies exist."""
        artifact = EffectiveConfigArtifact(
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
            dq_policy_refs=[],  # No DQ policies
        )

        assert artifact.dq_contract_compatibility_hash == "no_dq_policies"

    def test_dq_contract_compatibility_hash_explicit(self) -> None:
        """Test DQ contract compatibility hash when explicitly provided."""
        artifact = EffectiveConfigArtifact(
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
            dq_policy_refs=[],
            dq_contract_compatibility_hash="explicit_hash",  # Explicitly provided
        )

        # Should use explicitly provided hash
        assert artifact.dq_contract_compatibility_hash == "explicit_hash"


class TestImmutability:
    """Tests for immutability of all artifact classes."""

    def test_config_source_ref_immutability(self) -> None:
        """Test ConfigSourceRef immutability."""
        source_ref = ConfigSourceRef(
            source_type="file", source_path="/config/test.yaml"
        )

        with pytest.raises(Exception):
            source_ref.source_type = "env"  # type: ignore

    def test_dq_policy_snapshot_immutability(self) -> None:
        """Test DQPolicySnapshot immutability."""
        snapshot = DQPolicySnapshot(
            contract_ref="test",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            policy_hash="hash",
            default_disposition=DQDisposition.WARN,
        )

        with pytest.raises(Exception):
            snapshot.contract_ref = "modified"  # type: ignore

    def test_effective_config_artifact_immutability(self) -> None:
        """Test EffectiveConfigArtifact immutability."""
        artifact = EffectiveConfigArtifact(
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

        with pytest.raises(Exception):
            artifact.artifact_id = "modified"  # type: ignore
