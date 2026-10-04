"""Finalize composite contract evidence only after its runtime lock is held."""

from collections.abc import Callable
from pathlib import Path

from bioetl.application.services.control_plane.manifest.contract_evidence import (
    build_runtime_contract_evidence,
)
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.infrastructure.control_plane import FileRunManifestStore
from bioetl.infrastructure.control_plane.file_contract_evidence_recorder import (
    FileContractEvidenceRecorder,
)


def create_composite_contract_finalizer(
    *,
    pipeline_name: str,
    manifest_id: str,
) -> Callable[[str, bool], None]:
    root = Path(get_settings().data_dir) / "output/control/run_manifest"
    store = FileRunManifestStore(base_path=root)
    recorder = FileContractEvidenceRecorder(base_path=root)

    def finalize(run_id: str, resume_requested: bool) -> None:
        manifest = store.get(manifest_id)
        if manifest is None:
            raise RuntimeError("Composite contract manifest is missing")
        if str(manifest.run_id) != run_id or manifest.pipeline_name != pipeline_name:
            raise RuntimeError("Composite contract manifest identity mismatch")
        provenance = manifest.code_provenance
        recorder.record(
            manifest_id,
            build_runtime_contract_evidence(
                manifest_id=manifest_id,
                contract_ref=provenance.contract_ref,
                contract_schema_hash=provenance.contract_schema_hash,
                resume_requested=resume_requested,
                lock_owner_id=run_id,
            ),
        )

    return finalize
