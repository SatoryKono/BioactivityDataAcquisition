"""Unit tests for EffectiveConfigService with DQ integration."""

from __future__ import annotations

import json
import hashlib
from typing import Any

import pytest

from bioetl.application.services.control_plane.effective_config_support import (
    stable_hash,
)
from bioetl.application.services.control_plane.effective_config.service import (
    EffectiveConfigService,
    create_effective_config_service,
)
from bioetl.domain.normalization import serialize_json_canonical
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigSourceRef,
    EffectiveConfigArtifact,
)
from bioetl.domain.types.dq_contracts import DQDisposition

pytestmark = pytest.mark.unit


def _create_service_with_degraded_default() -> EffectiveConfigService:
    """Keep generic service tests focused on artifact mechanics, not strict runtime policy."""
    service = create_effective_config_service()
    original_create = service.create_effective_config_artifact

    def _create_effective_config_artifact(*args, **kwargs):
        kwargs.setdefault("required_persistence_profile", "degraded_observable")
        return original_create(*args, **kwargs)

    service.create_effective_config_artifact = (  # type: ignore[assignment]
        _create_effective_config_artifact
    )
    return service


class TestEffectiveConfigService:
    """Tests for EffectiveConfigService."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.service = _create_service_with_degraded_default()

    def test_service_creation(self) -> None:
        """Test service factory function."""
        service = create_effective_config_service()
        assert isinstance(service, EffectiveConfigService)

    def test_create_simple_artifact(self) -> None:
        """Test creation of a simple artifact without DQ."""
        pipeline_config: dict[str, Any] = {
            "pipeline": {"name": "test_pipeline", "version": "1.0.0"},
            "settings": {"batch_size": 1000},
        }

        source_refs: list[ConfigSourceRef] = [
            ConfigSourceRef(
                source_type="file",
                source_path="configs/base/pipeline.yaml",
                source_hash="base_hash",
                priority=1,
            )
        ]

        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            resolved_config=pipeline_config,
            runtime_overrides={},
            source_refs=source_refs,
        )

        # Verify artifact structure
        assert isinstance(artifact, EffectiveConfigArtifact)
        assert artifact.pipeline_name == "test_pipeline"
        assert artifact.pipeline_kind == "standard"
        assert len(artifact.source_refs) == 1
        assert {item.source_class for item in artifact.source_class_provenance} == {
            "config_file",
            "cli_override",
            "env_override",
            "runtime_adjustment",
            "dq_policy_contract",
            "immutable_input_snapshot",
            "implicit_process_environment",
        }
        assert artifact.dq_policy_refs == []  # No DQ config provided

    def test_create_artifact_with_dq_config(self) -> None:
        """Test creation of artifact with DQ configuration."""
        pipeline_config: dict[str, Any] = {
            "pipeline": {"name": "chembl_molecule", "version": "1.0.0"},
            "settings": {"batch_size": 5000},
        }

        dq_config = DQConfig(
            contract_ref="chembl_molecule",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
            disposition_overrides={
                "schema.molecule_id": DQDisposition.FAIL,
                "schema.assay_id": DQDisposition.QUARANTINE,
            },
            strictness_mode="strict",
        )

        source_refs: list[ConfigSourceRef] = [
            ConfigSourceRef(
                source_type="file",
                source_path="configs/providers/chembl.yaml",
                source_hash="provider_hash",
                priority=1,
            )
        ]

        artifact = self.service.create_effective_config_artifact(
            pipeline_name="chembl_molecule",
            pipeline_kind="standard",
            resolved_config=pipeline_config,
            runtime_overrides={},
            source_refs=source_refs,
            dq_config=dq_config,
        )

        # Verify DQ integration
        assert len(artifact.dq_policy_refs) == 1
        assert artifact.dq_policy_refs[0].contract_ref == "chembl_molecule"
        assert len(artifact.dq_policy_snapshots) == 1
        assert artifact.dq_policy_snapshots[0].default_disposition == DQDisposition.WARN
        assert len(artifact.dq_policy_snapshots[0].disposition_overrides) == 2

    def test_create_artifact_with_runtime_overrides(self) -> None:
        """Test creation of artifact with runtime overrides."""
        pipeline_config: dict[str, Any] = {
            "pipeline": {"name": "test_pipeline", "version": "1.0.0"},
            "settings": {"batch_size": 1000, "timeout": 30},
        }

        runtime_overrides = {
            "cli": {"settings": {"batch_size": 2000}},
            "env": {"execution_environment": {"log_level": "DEBUG"}},
            "runtime": {"auto_adjust": True},
        }

        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            resolved_config=pipeline_config,
            runtime_overrides=runtime_overrides,
            source_refs=[],
        )

        # Verify overrides are applied
        effective_config = artifact.effective_execution_config.config_data
        assert effective_config["settings"]["batch_size"] == 2000  # Overridden
        assert effective_config["settings"]["timeout"] == 30  # Not overridden
        assert (
            effective_config["execution_environment"]["log_level"] == "DEBUG"
        )  # Added by override
        assert effective_config["auto_adjust"] is True  # Added by override

    def test_create_artifact_with_normalization_profile_identity(self) -> None:
        """Normalization profile identity should persist on the artifact surface."""
        artifact = self.service.create_effective_config_artifact(
            pipeline_name="pubchem_compound",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "pubchem_compound"}},
            runtime_overrides={},
            source_refs=[],
            normalization_profile_ref="pubchem.compound",
            normalization_profile_version="1.0.0",
            normalization_profile_hash="a" * 64,
        )

        assert artifact.normalization_profile_ref == "pubchem.compound"
        assert artifact.normalization_profile_version == "1.0.0"
        assert artifact.normalization_profile_hash == "a" * 64

    def test_create_artifact_rejects_non_allowlisted_env_overrides(self) -> None:
        """Semantic env overrides must stay inside the explicit allowlist."""
        with pytest.raises(
            ValueError,
            match=r"runtime_overrides\.env contains non-allowlisted semantic environment overrides",
        ):
            self.service.create_effective_config_artifact(
                pipeline_name="test_pipeline",
                pipeline_kind="standard",
                resolved_config={"pipeline": {"name": "test_pipeline"}},
                runtime_overrides={"env": {"BIOETL_PUBMED_API_KEY": "secret"}},
                source_refs=[],
                required_persistence_profile="replay_ready",
            )

    def test_create_artifact_requires_materialized_execution_environment_in_strict_context(
        self,
    ) -> None:
        """Strict reproducibility contexts must materialize semantic env values."""
        with pytest.raises(
            ValueError,
            match=r"runtime_overrides\.env\.execution_environment must be materialized",
        ):
            self.service.create_effective_config_artifact(
                pipeline_name="test_pipeline",
                pipeline_kind="standard",
                resolved_config={"pipeline": {"name": "test_pipeline"}},
                runtime_overrides={},
                source_refs=[],
                required_persistence_profile="replay_ready",
            )

    def test_artifact_id_generation(self) -> None:
        """Automatic artifact IDs should be deterministic semantic anchors."""
        artifact1 = self.service.create_effective_config_artifact(
            pipeline_name="test1",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test1"}},
            runtime_overrides={},
            source_refs=[],
        )

        artifact2 = self.service.create_effective_config_artifact(
            pipeline_name="test2",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test2"}},
            runtime_overrides={},
            source_refs=[],
        )

        # Should have different auto-generated IDs
        assert artifact1.artifact_id != artifact2.artifact_id
        assert artifact1.artifact_id.startswith("effective-config-")
        assert artifact2.artifact_id.startswith("effective-config-")

    def test_artifact_id_is_stable_for_identical_semantic_inputs(self) -> None:
        """Identical semantic inputs must yield the same artifact ID."""
        kwargs = {
            "pipeline_name": "test_pipeline",
            "pipeline_kind": "standard",
            "resolved_config": {"pipeline": {"name": "test_pipeline"}},
            "runtime_overrides": {"runtime": {"limit": 5}},
            "source_refs": [
                ConfigSourceRef(
                    source_type="file",
                    source_path="configs/entities/test/pipeline.yaml",
                    source_hash="abc123",
                    priority=1,
                )
            ],
        }

        artifact1 = self.service.create_effective_config_artifact(**kwargs)
        artifact2 = self.service.create_effective_config_artifact(**kwargs)

        assert artifact1.artifact_id == artifact2.artifact_id

    def test_source_refs_order_does_not_change_semantic_identity(self) -> None:
        """Equivalent source-ref sets must not perturb effective-config identity."""
        first_refs = [
            ConfigSourceRef(
                source_type="file",
                source_path="configs/entities/test/override.yaml",
                source_hash="override-hash",
                priority=20,
            ),
            ConfigSourceRef(
                source_type="file",
                source_path="configs/base/pipeline.yaml",
                source_hash="base-hash",
                priority=10,
            ),
        ]
        second_refs = list(reversed(first_refs))
        kwargs = {
            "pipeline_name": "test_pipeline",
            "pipeline_kind": "standard",
            "resolved_config": {"pipeline": {"name": "test_pipeline"}},
            "runtime_overrides": {"runtime": {"limit": 5}},
        }

        first = self.service.create_effective_config_artifact(
            **kwargs,
            source_refs=first_refs,
        )
        second = self.service.create_effective_config_artifact(
            **kwargs,
            source_refs=second_refs,
        )

        assert first.artifact_id == second.artifact_id
        assert first.source_fingerprint == second.source_fingerprint
        assert self.service.serialize_semantic_artifact(
            first
        ) == self.service.serialize_semantic_artifact(second)

    def test_stable_hash_uses_canonical_json_serializer_contract(self) -> None:
        """Effective-config hashes must share control-plane canonical JSON semantics."""
        payload = {"z": [3, 2, 1], "a": {"b": "café"}}

        expected = hashlib.sha256(
            serialize_json_canonical(payload).encode("utf-8")
        ).hexdigest()

        assert stable_hash(payload) == expected

    def test_stable_hash_rejects_non_finite_float_values(self) -> None:
        """Effective-config hashing must fail closed like execution fingerprints."""
        with pytest.raises(
            ValueError,
            match="Canonical JSON serialization does not allow NaN or Infinity",
        ):
            stable_hash({"runtime": {"limit": float("nan")}})

    def test_artifact_id_differs_from_legacy_hash_bundle_identifier(self) -> None:
        """Artifact identity must track full semantic payload, not only hash bundles."""
        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test_pipeline"}},
            runtime_overrides={"runtime": {"limit": 5}},
            source_refs=[
                ConfigSourceRef(
                    source_type="file",
                    source_path="configs/entities/test/pipeline.yaml",
                    source_hash="abc123",
                    priority=1,
                )
            ],
        )

        legacy_semantic_payload = {
            "pipeline_name": artifact.pipeline_name,
            "pipeline_kind": artifact.pipeline_kind,
            "resolved_config_hash": artifact.resolved_config_hash,
            "effective_config_hash": artifact.effective_config_hash,
            "source_fingerprint": artifact.source_fingerprint,
            "dq_contract_compatibility_hash": artifact.dq_contract_compatibility_hash,
        }
        legacy_artifact_id = (
            "effective-config-"
            + hashlib.sha256(
                json.dumps(
                    legacy_semantic_payload,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()[:16]
        )

        assert artifact.artifact_id != legacy_artifact_id

    def test_custom_artifact_id(self) -> None:
        """Test custom artifact ID usage."""
        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test"}},
            runtime_overrides={},
            source_refs=[],
            artifact_id="custom_artifact_123",
        )

        assert artifact.artifact_id == "custom_artifact_123"

    def test_serialization_integration(self) -> None:
        """Test serialization integration."""
        pipeline_config: dict[str, Any] = {
            "pipeline": {"name": "test_pipeline", "version": "1.0.0"},
            "settings": {"batch_size": 1000},
        }

        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            resolved_config=pipeline_config,
            runtime_overrides={},
            source_refs=[],
        )

        # Serialize the artifact
        json_str = self.service.serialize_artifact(artifact)

        # Should be valid JSON
        import json

        parsed = json.loads(json_str)
        assert parsed["artifact_id"] == artifact.artifact_id
        assert parsed["semantic_artifact"]["pipeline_name"] == "test_pipeline"
        assert parsed["semantic_artifact"]["source_class_provenance"]
        assert {
            item["source_class"]
            for item in parsed["semantic_artifact"]["source_class_provenance"]
        } == {
            "config_file",
            "cli_override",
            "env_override",
            "runtime_adjustment",
            "dq_policy_contract",
            "immutable_input_snapshot",
            "implicit_process_environment",
        }
        assert "occurrence_envelope" in parsed

    def test_source_class_provenance_marks_anchored_external_and_policy_excluded_classes(
        self,
    ) -> None:
        """Source provenance distinguishes anchored, external, and policy-excluded inputs."""
        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test_pipeline"}},
            runtime_overrides={},
            source_refs=[],
        )

        provenance_by_class = {
            item.source_class: item for item in artifact.source_class_provenance
        }

        env_override = provenance_by_class["env_override"]
        assert env_override.provenance_status == "identity_anchored"
        assert (
            env_override.artifact_surface
            == "semantic_artifact.runtime_overrides.env_overrides"
        )
        assert env_override.anchor_field == "override_hash"

        immutable_snapshot = provenance_by_class["immutable_input_snapshot"]
        assert immutable_snapshot.provenance_status == "external_anchor"
        assert immutable_snapshot.anchor_field == "content_hash"
        assert (
            immutable_snapshot.artifact_surface
            == "run_manifest.source_refs[*].input_snapshots[*]"
        )

        ambient_environment = provenance_by_class["implicit_process_environment"]
        assert ambient_environment.provenance_status == "policy_excluded"
        assert (
            ambient_environment.artifact_surface
            == "semantic_artifact.execution_environment"
        )
        assert ambient_environment.anchor_field == "environment_hash"

    def test_execution_environment_snapshot_materializes_explicit_env_overrides(
        self,
    ) -> None:
        """Explicit env overrides should be a semantic effective-config surface."""
        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test_pipeline"}},
            runtime_overrides={
                "env": {
                    "execution_environment": {"BIOETL_BATCH_LIMIT": "100"},
                }
            },
            source_refs=[],
            required_persistence_profile="replay_ready",
        )

        assert artifact.execution_environment.materialized_env_keys == (
            "execution_environment",
        )
        assert artifact.execution_environment.materialized_env_overrides == {
            "execution_environment": {"BIOETL_BATCH_LIMIT": "100"}
        }
        assert artifact.execution_environment.ambient_environment_policy == (
            "materialized_via_execution_environment"
        )
        assert (
            artifact.execution_environment.non_materialized_semantic_env_dependencies
            == ()
        )
        assert artifact.execution_environment.environment_hash

    def test_semantic_serialization_omits_empty_runtime_override_sections(
        self,
    ) -> None:
        """Serialized semantic payload should not imply absent override provenance."""
        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test_pipeline"}},
            runtime_overrides={},
            source_refs=[],
        )

        payload = json.loads(self.service.serialize_semantic_artifact(artifact))

        assert payload["runtime_overrides"] == {}

    def test_semantic_serialization_is_stable_across_occurrence_timestamps(
        self,
    ) -> None:
        """Semantic serialization should ignore occurrence envelope timestamps."""
        kwargs = {
            "pipeline_name": "test_pipeline",
            "pipeline_kind": "standard",
            "resolved_config": {"pipeline": {"name": "test_pipeline"}},
            "runtime_overrides": {"runtime": {"limit": 5}},
            "source_refs": [],
        }

        artifact1 = self.service.create_effective_config_artifact(**kwargs)
        artifact2 = self.service.create_effective_config_artifact(**kwargs)

        assert artifact1.created_at != artifact2.created_at
        assert self.service.serialize_semantic_artifact(
            artifact1
        ) == self.service.serialize_semantic_artifact(artifact2)

    def test_hash_computation_integration(self) -> None:
        """Test hash computation integration."""
        pipeline_config: dict[str, Any] = {
            "pipeline": {"name": "test_pipeline", "version": "1.0.0"},
            "settings": {"batch_size": 1000},
        }

        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            resolved_config=pipeline_config,
            runtime_overrides={},
            source_refs=[],
        )

        # Compute hashes
        hashes = self.service.compute_artifact_hashes(artifact)

        # Verify hash structure
        assert hashes.resolved_config_hash == artifact.resolved_config_hash
        assert hashes.effective_config_hash == artifact.effective_config_hash
        assert len(hashes.resolved_config_hash) == 64  # SHA256
        assert len(hashes.effective_config_hash) == 64  # SHA256

    def test_dq_compatibility_checking(self) -> None:
        """Test DQ compatibility checking."""
        dq_config = DQConfig(
            contract_ref="test_contract",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
        )

        # Create two artifacts with same DQ config
        artifact1 = self.service.create_effective_config_artifact(
            pipeline_name="test1",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test1"}},
            runtime_overrides={},
            source_refs=[],
            dq_config=dq_config,
        )

        artifact2 = self.service.create_effective_config_artifact(
            pipeline_name="test2",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test2"}},
            runtime_overrides={},
            source_refs=[],
            dq_config=dq_config,
        )

        # Should be compatible
        assert self.service.check_dq_compatibility(artifact1, artifact2) is True

        # Create artifact with different DQ config
        different_dq_config = DQConfig(
            contract_ref="different_contract",
            contract_version="2.0.0",
            rule_bundle_version="2.0.0",
            default_disposition_policy=DQDisposition.FAIL,
        )

        artifact3 = self.service.create_effective_config_artifact(
            pipeline_name="test3",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test3"}},
            runtime_overrides={},
            source_refs=[],
            dq_config=different_dq_config,
        )

        # Should not be compatible
        assert self.service.check_dq_compatibility(artifact1, artifact3) is False

    def test_convenience_method(self) -> None:
        """Test the convenience method for pipeline config."""
        pipeline_config: dict[str, Any] = {
            "pipeline": {"name": "chembl_molecule", "version": "1.0.0"},
            "settings": {"batch_size": 5000},
        }

        dq_config = DQConfig(
            contract_ref="chembl_molecule",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
        )

        runtime_overrides = {
            "cli": {"settings": {"batch_size": 10000}},
            "env": {"execution_environment": {"log_level": "INFO"}},
        }

        artifact = self.service.create_artifact_from_pipeline_config(
            pipeline_name="chembl_molecule",
            pipeline_kind="standard",
            pipeline_config=pipeline_config,
            dq_config=dq_config,
            runtime_overrides=runtime_overrides,
        )

        # Verify artifact was created correctly
        assert isinstance(artifact, EffectiveConfigArtifact)
        assert artifact.pipeline_name == "chembl_molecule"
        assert len(artifact.dq_policy_refs) == 1

        # Verify overrides were applied
        effective_config = artifact.effective_execution_config.config_data
        assert effective_config["settings"]["batch_size"] == 10000  # Overridden

    def test_composite_pipeline_artifact(self) -> None:
        """Test creation of composite pipeline artifact."""
        composite_config: dict[str, Any] = {
            "composite": {
                "name": "activity_composite",
                "version": "1.0.0",
                "entities": ["molecule", "assay", "activity"],
            },
            "merge_strategy": "hierarchical",
            "output_policy": "consolidated",
        }

        artifact = self.service.create_effective_config_artifact(
            pipeline_name="activity_composite",
            pipeline_kind="composite",
            resolved_config=composite_config,
            runtime_overrides={},
            source_refs=[],
        )

        # Verify composite artifact
        assert artifact.pipeline_kind == "composite"
        assert artifact.resolved_config.config_type == "composite"
        assert "composite" in artifact.resolved_config.config_data

    def test_artifact_immutability(self) -> None:
        """Test that created artifacts are immutable."""
        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test"}},
            runtime_overrides={},
            source_refs=[],
        )

        # Should not be able to modify artifact
        with pytest.raises(Exception):
            artifact.pipeline_name = "modified"  # type: ignore


class TestDQPolicyIntegration:
    """Tests for DQ policy integration in EffectiveConfigService."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.service = _create_service_with_degraded_default()

    def test_dq_policy_snapshot_creation(self) -> None:
        """Test DQ policy snapshot creation from DQ config."""
        dq_config = DQConfig(
            contract_ref="chembl_molecule",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
            disposition_overrides={
                "schema.molecule_id": DQDisposition.FAIL,
                "schema.assay_id": DQDisposition.QUARANTINE,
                "threshold.completeness": DQDisposition.WARN,
            },
            strictness_mode="strict",
        )

        artifact = self.service.create_effective_config_artifact(
            pipeline_name="chembl_molecule",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "chembl_molecule"}},
            runtime_overrides={},
            source_refs=[],
            dq_config=dq_config,
        )

        # Verify policy snapshot
        assert len(artifact.dq_policy_snapshots) == 1
        snapshot = artifact.dq_policy_snapshots[0]

        assert snapshot.contract_ref == "chembl_molecule"
        assert snapshot.contract_version == "1.0.0"
        assert snapshot.rule_bundle_version == "1.0.0"
        assert len(snapshot.policy_hash) == 64  # Should be a valid SHA256 hash
        assert snapshot.default_disposition == DQDisposition.WARN
        assert snapshot.strictness_mode == "strict"
        assert len(snapshot.disposition_overrides) == 3

    def test_dq_policy_ref_creation(self) -> None:
        """Test DQ policy reference creation."""
        dq_config = DQConfig(
            contract_ref="test_contract",
            contract_version="2.0.0",
            rule_bundle_version="2.0.0",
            default_disposition_policy=DQDisposition.FAIL,
        )

        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test"}},
            runtime_overrides={},
            source_refs=[],
            dq_config=dq_config,
        )

        # Verify policy ref
        assert len(artifact.dq_policy_refs) == 1
        policy_ref = artifact.dq_policy_refs[0]

        assert policy_ref.contract_ref == "test_contract"
        assert policy_ref.contract_version == "2.0.0"
        assert policy_ref.rule_bundle_version == "2.0.0"

    def test_dq_rule_bundle_versions(self) -> None:
        """Test DQ rule bundle version tracking."""
        dq_config = DQConfig(
            contract_ref="chembl_molecule",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
        )

        artifact = self.service.create_effective_config_artifact(
            pipeline_name="chembl_molecule",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "chembl_molecule"}},
            runtime_overrides={},
            source_refs=[],
            dq_config=dq_config,
        )

        # Verify rule bundle versions
        assert len(artifact.dq_rule_bundle_versions) == 1
        assert "chembl_molecule" in artifact.dq_rule_bundle_versions
        assert artifact.dq_rule_bundle_versions["chembl_molecule"] == "1.0.0"

    def test_no_dq_config_handling(self) -> None:
        """Test handling when no DQ config is provided."""
        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test_pipeline",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test"}},
            runtime_overrides={},
            source_refs=[],
        )

        # Should have empty DQ fields
        assert artifact.dq_policy_refs == []
        assert artifact.dq_policy_snapshots == []
        assert artifact.dq_rule_bundle_versions == {}
        assert artifact.dq_contract_compatibility_hash == "no_dq_policies"


class TestOverrideApplication:
    """Tests for runtime override application."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.service = _create_service_with_degraded_default()

    def test_deep_override_application(self) -> None:
        """Test deep nested override application."""
        base_config: dict[str, Any] = {
            "pipeline": {"name": "test", "version": "1.0"},
            "settings": {
                "batch": {"size": 1000, "timeout": 30},
                "retry": {"max_attempts": 3, "backoff": "exponential"},
            },
        }

        overrides = {
            "cli": {"settings": {"batch": {"size": 2000}, "retry": {"max_attempts": 5}}}
        }

        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test",
            pipeline_kind="standard",
            resolved_config=base_config,
            runtime_overrides=overrides,
            source_refs=[],
            required_persistence_profile="degraded_observable",
        )

        effective_config = artifact.effective_execution_config.config_data

        # Verify deep overrides were applied
        assert effective_config["settings"]["batch"]["size"] == 2000  # Overridden
        assert effective_config["settings"]["batch"]["timeout"] == 30  # Not overridden
        assert effective_config["settings"]["retry"]["max_attempts"] == 5  # Overridden
        assert (
            effective_config["settings"]["retry"]["backoff"] == "exponential"
        )  # Not overridden

    def test_multiple_override_sources(self) -> None:
        """Test override application from multiple sources."""
        base_config: dict[str, Any] = {
            "pipeline": {"name": "test"},
            "settings": {"batch_size": 1000, "timeout": 30, "log_level": "INFO"},
        }

        overrides = {
            "cli": {"settings": {"batch_size": 2000}},  # CLI override
            "env": {"settings": {"log_level": "DEBUG"}},  # Environment override
            "runtime": {"auto_adjust": True},  # Runtime adjustment
        }

        artifact = self.service.create_effective_config_artifact(
            pipeline_name="test",
            pipeline_kind="standard",
            resolved_config=base_config,
            runtime_overrides=overrides,
            source_refs=[],
            required_persistence_profile="degraded_observable",
        )

        effective_config = artifact.effective_execution_config.config_data

        # Verify all override sources were applied
        assert effective_config["settings"]["batch_size"] == 2000  # CLI override
        assert effective_config["settings"]["log_level"] == "DEBUG"  # Env override
        assert effective_config["auto_adjust"] is True  # Runtime adjustment
        assert effective_config["settings"]["timeout"] == 30  # Base value

    def test_override_hash_computation(self) -> None:
        """Test override hash computation."""
        overrides1 = {
            "cli": {"batch_size": 1000},
            "env": {"execution_environment": {"log_level": "INFO"}},
        }

        overrides2 = {
            "env": {"execution_environment": {"log_level": "INFO"}},
            "cli": {"batch_size": 1000},  # Same content, different order
        }

        # Create artifacts with same overrides but different ordering
        artifact1 = self.service.create_effective_config_artifact(
            pipeline_name="test1",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test1"}},
            runtime_overrides=overrides1,
            source_refs=[],
        )

        artifact2 = self.service.create_effective_config_artifact(
            pipeline_name="test2",
            pipeline_kind="standard",
            resolved_config={"pipeline": {"name": "test2"}},
            runtime_overrides=overrides2,
            source_refs=[],
        )

        # Override hashes should be the same (deterministic)
        assert (
            artifact1.runtime_overrides.override_hash
            == artifact2.runtime_overrides.override_hash
        )
