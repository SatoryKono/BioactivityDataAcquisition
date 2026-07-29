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
"""Unit tests for RunManifest with DQ integration."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest

from bioetl.domain.control_plane.run_manifest import RunCodeProvenance, RunManifest
from bioetl.domain.types import RunID, RunType


pytestmark = pytest.mark.unit


class TestRunCodeProvenanceDQIntegration:
    """Tests for RunCodeProvenance with DQ integration."""

    def test_code_provenance_with_dq_fields(self) -> None:
        """Test RunCodeProvenance creation with DQ fields."""
        provenance = RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc123",
            config_hash="config_hash_123",
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            contract_schema_hash="schema_hash_123",
            dq_policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1.0",
            dq_contract_compatibility_hash="dq_hash_abc",
            effective_config_artifact_id="config_artifact_001",
        )

        assert provenance.pipeline_version == "1.0.0"
        assert provenance.git_commit == "abc123"
        assert provenance.config_hash == "config_hash_123"
        assert provenance.contract_ref == "chembl.activity"
        assert provenance.contract_version == "1.0.0"
        assert provenance.contract_schema_hash == "schema_hash_123"
        assert provenance.dq_policy_ref == "chembl.dq.v1"
        assert provenance.rule_bundle_version == "dq-rules.v1.0"
        assert provenance.dq_contract_compatibility_hash == "dq_hash_abc"
        assert provenance.effective_config_artifact_id == "config_artifact_001"

    def test_code_provenance_without_dq_fields(self) -> None:
        """Test RunCodeProvenance creation without DQ fields (backward compatibility)."""
        provenance = RunCodeProvenance(
            pipeline_version="1.0.0", git_commit="abc123", config_hash="config_hash_123"
        )

        assert provenance.dq_contract_compatibility_hash is None
        assert provenance.effective_config_artifact_id is None

    def test_code_provenance_immutability(self) -> None:
        """Test that RunCodeProvenance is immutable."""
        provenance = RunCodeProvenance(dq_contract_compatibility_hash="test_hash")

        with pytest.raises(Exception):
            provenance.dq_contract_compatibility_hash = "modified"  # type: ignore

    def test_code_provenance_serialization(self) -> None:
        """Test RunCodeProvenance serialization with DQ fields."""
        provenance = RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc123",
            config_hash="config_hash_123",
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            contract_schema_hash="schema_hash_123",
            dq_policy_ref="chembl.dq.v1",
            rule_bundle_version="dq-rules.v1.0",
            dq_contract_compatibility_hash="dq_hash_abc",
            effective_config_artifact_id="config_artifact_001",
        )

        # Test to_dict serialization
        provenance_dict = {
            "pipeline_version": "1.0.0",
            "git_commit": "abc123",
            "config_hash": "config_hash_123",
            "contract_ref": "chembl.activity",
            "contract_version": "1.0.0",
            "contract_schema_hash": "schema_hash_123",
            "dq_policy_ref": "chembl.dq.v1",
            "rule_bundle_version": "dq-rules.v1.0",
            "dq_contract_compatibility_hash": "dq_hash_abc",
            "effective_config_artifact_id": "config_artifact_001",
        }

        # Test from_dict deserialization
        loaded_provenance = RunCodeProvenance(**provenance_dict)
        assert loaded_provenance == provenance


class TestRunManifestDQIntegration:
    """Tests for RunManifest with DQ integration."""

    def test_run_manifest_creation_with_dq_fields(self) -> None:
        """Test RunManifest creation with DQ fields in code provenance."""
        code_provenance = RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc123",
            config_hash="config_hash_123",
            dq_contract_compatibility_hash="dq_hash_abc",
            effective_config_artifact_id="config_artifact_001",
        )

        manifest = RunManifest(
            manifest_id="manifest_123",
            execution_fingerprint="exec_fingerprint_123",
            schema_version="1.0",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            run_id=RunID(UUID("12345678-1234-5678-1234-567812345678")),
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={},
            runtime_config={},
            resolved_config={},
            code_provenance=code_provenance,
        )

        assert manifest.code_provenance.dq_contract_compatibility_hash == "dq_hash_abc"
        assert (
            manifest.code_provenance.effective_config_artifact_id
            == "config_artifact_001"
        )

    def test_run_manifest_serialization_with_dq_fields(self) -> None:
        """Test RunManifest serialization/deserialization with DQ fields."""
        code_provenance = RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc123",
            config_hash="config_hash_123",
            dq_contract_compatibility_hash="dq_hash_abc",
            effective_config_artifact_id="config_artifact_001",
        )

        manifest = RunManifest(
            manifest_id="manifest_123",
            execution_fingerprint="exec_fingerprint_123",
            schema_version="1.0",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            run_id=RunID(UUID("12345678-1234-5678-1234-567812345678")),
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={},
            runtime_config={},
            resolved_config={},
            code_provenance=code_provenance,
        )

        # Test to_dict serialization
        manifest_dict = manifest.to_dict()
        assert "code_provenance" in manifest_dict
        assert (
            manifest_dict["code_provenance"]["dq_contract_compatibility_hash"]
            == "dq_hash_abc"
        )
        assert (
            manifest_dict["code_provenance"]["effective_config_artifact_id"]
            == "config_artifact_001"
        )

        # Test from_dict deserialization
        loaded_manifest = RunManifest.from_dict(manifest_dict)
        assert loaded_manifest == manifest
        assert (
            loaded_manifest.code_provenance.dq_contract_compatibility_hash
            == "dq_hash_abc"
        )
        assert (
            loaded_manifest.code_provenance.effective_config_artifact_id
            == "config_artifact_001"
        )

    def test_run_manifest_backward_compatibility(self) -> None:
        """Test RunManifest backward compatibility without DQ fields."""
        # Create manifest without DQ fields
        code_provenance = RunCodeProvenance(
            pipeline_version="1.0.0", git_commit="abc123", config_hash="config_hash_123"
        )

        manifest = RunManifest(
            manifest_id="manifest_123",
            execution_fingerprint="exec_fingerprint_123",
            schema_version="1.0",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            run_id=RunID(UUID("12345678-1234-5678-1234-567812345678")),
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={},
            runtime_config={},
            resolved_config={},
            code_provenance=code_provenance,
        )

        # Should have None DQ fields
        assert manifest.code_provenance.dq_contract_compatibility_hash is None
        assert manifest.code_provenance.effective_config_artifact_id is None

        # Should serialize and deserialize correctly
        manifest_dict = manifest.to_dict()
        loaded_manifest = RunManifest.from_dict(manifest_dict)
        assert loaded_manifest == manifest

    def test_run_manifest_equality_with_dq_fields(self) -> None:
        """Test RunManifest equality with DQ fields."""
        code_provenance1 = RunCodeProvenance(
            dq_contract_compatibility_hash="dq_hash_abc"
        )

        manifest1 = RunManifest(
            manifest_id="manifest_123",
            execution_fingerprint="exec_fingerprint_123",
            schema_version="1.0",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            run_id=RunID(UUID("12345678-1234-5678-1234-567812345678")),
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={},
            runtime_config={},
            resolved_config={},
            code_provenance=code_provenance1,
        )

        code_provenance2 = RunCodeProvenance(
            dq_contract_compatibility_hash="dq_hash_abc"
        )

        manifest2 = RunManifest(
            manifest_id="manifest_123",
            execution_fingerprint="exec_fingerprint_123",
            schema_version="1.0",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            run_id=RunID(UUID("12345678-1234-5678-1234-567812345678")),
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={},
            runtime_config={},
            resolved_config={},
            code_provenance=code_provenance2,
        )

        # Should be equal
        assert manifest1 == manifest2

        # Different DQ hash should make them unequal
        code_provenance3 = RunCodeProvenance(
            dq_contract_compatibility_hash="different_hash"
        )

        manifest3 = RunManifest(
            manifest_id="manifest_123",
            execution_fingerprint="exec_fingerprint_123",
            schema_version="1.0",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            run_id=RunID(UUID("12345678-1234-5678-1234-567812345678")),
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={},
            runtime_config={},
            resolved_config={},
            code_provenance=code_provenance3,
        )

        assert manifest1 != manifest3

    def test_from_dict_does_not_alias_legacy_config_hash_to_explicit_hash_fields(
        self,
    ) -> None:
        """Legacy config_hash must not backfill resolved/effective hashes on hydrate."""
        manifest = RunManifest.from_dict(
            {
                "manifest_id": "manifest_legacy",
                "execution_fingerprint": "exec_fingerprint_legacy",
                "schema_version": "1.0",
                "created_at": "2023-01-01T12:00:00",
                "run_id": "12345678-1234-5678-1234-567812345678",
                "run_type": "incremental",
                "pipeline_name": "chembl_activity",
                "provider": "chembl",
                "entity": "activity",
                "launch_context": {},
                "runtime_config": {},
                "resolved_config": {},
                "code_provenance": {
                    "config_hash": "legacy_hash_123",
                    "git_commit": "abc123",
                },
            }
        )

        assert manifest.code_provenance.config_hash == "legacy_hash_123"
        assert manifest.code_provenance.resolved_config_hash is None
        assert manifest.code_provenance.effective_config_hash is None
