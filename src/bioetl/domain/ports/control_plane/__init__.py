"""Control-plane port exports.

## Public contract surface

This package re-exports the stable domain ports that form the BioETL
control-plane boundary (run/workflow manifests, ledgers, lineage, and
effective-config artifacts).

| Concern | Port |
| --- | --- |
| Run planning artifact | `RunManifestPort` |
| Persisted raw-manifest diagnostics | `RawRunManifestInspectionPort` |
| Run lifecycle ledger | `RunLedgerPort` |
| Workflow planning artifact | `WorkflowManifestPort` |
| Workflow lifecycle ledger | `WorkflowLedgerPort` |
| Workflow execution state | `WorkflowExecutionStatePort` |
| Lineage graph store | `LineageStorePort` |
| Effective config artifact store | `EffectiveConfigArtifactStorePort` |
| Artifact byte comparison | `ArtifactByteComparisonPort` |

## Release / governance

- **ADR:** [ADR-044](../../../../docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
  (Run Manifest and Run Ledger Control Plane).
- **Stability:** additive, domain-layer contracts. Implementations live under
  `infrastructure` / `application` and must satisfy these Protocols.
- **Migration:** importing from
  `bioetl.domain.ports.control_plane` is the preferred public path. Deep
  imports of individual modules remain supported for backward compatibility;
  no consumer migration is required when only this package `__all__` surface is
  used.
- **Rollback:** revert this package to prior re-exports / remove unused symbols
  from `__all__`. Downstream adapters keep implementing the same Protocol
  modules under `domain/ports/control_plane/*.py`.

Nominal import-surface coverage lives in
`tests/unit/domain/ports/test_control_plane_port_exports.py`.
"""

from __future__ import annotations

from bioetl.domain.ports.control_plane.artifact_byte_comparison import (
    ArtifactByteComparisonPort,
)
from bioetl.domain.ports.control_plane.contract_evidence import (
    ContractEvidenceRecorderPort,
)
from bioetl.domain.ports.control_plane.effective_config_artifact import (
    EffectiveConfigArtifactStorePort,
)
from bioetl.domain.ports.control_plane.lineage import LineageStorePort
from bioetl.domain.ports.control_plane.run_ledger import RunLedgerPort
from bioetl.domain.ports.control_plane.run_manifest import (
    RawManifestInspection,
    RawRunManifestInspectionPort,
    RunManifestPort,
)
from bioetl.domain.ports.control_plane.workflow_execution_state import (
    WorkflowExecutionStatePort,
)
from bioetl.domain.ports.control_plane.workflow_ledger import WorkflowLedgerPort
from bioetl.domain.ports.control_plane.workflow_manifest import WorkflowManifestPort

__all__ = [
    "ArtifactByteComparisonPort",
    "ContractEvidenceRecorderPort",
    "EffectiveConfigArtifactStorePort",
    "LineageStorePort",
    "RawManifestInspection",
    "RawRunManifestInspectionPort",
    "RunLedgerPort",
    "RunManifestPort",
    "WorkflowExecutionStatePort",
    "WorkflowLedgerPort",
    "WorkflowManifestPort",
]
