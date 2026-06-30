# BioETL Governed Export Policy

Last verified: 2026-06-30

BioETL governed exports are application-level exports. Grafana inspector output
is not a governed export surface.

## Contract

Each governed export records:

| Field | Purpose |
| --- | --- |
| `audit_ref` | Stable reference derived from table, layer, format, filters, role, requester, row count, output columns, and redaction profile. |
| `requester` | Operator or service identity supplied by the caller. |
| `role` | Bounded role: `viewer`, `investigator`, `exporter`, or `admin`. |
| `filters_hash` | Stable hash of the filtered query input used for query/export parity evidence. |
| `row_count` | Exported row count after deterministic redaction. |
| `checksum_manifest_path` | Checksum sidecar path for the exported data and manifests. |
| `expires_at` | ISO-8601 expiry timestamp for download semantics when an HTTP/download surface exists. |
| `redaction_profile` | `default` or `none`. `none` requires a privileged role. |
| `redacted_columns` | Sensitive columns removed from the materialized export. |

## Access Rules

- `viewer` may export only redacted datasets.
- `investigator`, `exporter`, and `admin` may request `redaction_profile=none`
  when backend authorization allows raw-sensitive access.
- Sensitive field detection is deterministic and based on bounded column-name
  tokens: `payload`, `raw`, `secret`, `token`, `password`, `credential`.
- A non-privileged request for raw sensitive fields fails closed.
- If deterministic redaction would remove every column, export fails closed.
- Expired exports must be denied by any HTTP/download adapter. The application
  service records `expires_at`; adapters must enforce it before serving files.

## Sidecars

The export writer persists:

- data file;
- provenance manifest with `export_governance`;
- licensing manifest;
- checksum manifest.

The application service does not perform filesystem access directly. It uses
`ExportWriterPort`; infrastructure adapters write files and fingerprints.

## Validation

Unit and architecture tests cover:

- redaction and role denial:
  `tests/unit/application/services/test_export_service.py`;
- sidecar governance metadata:
  `tests/unit/application/services/test_export_manifests.py`;
- CLI option propagation:
  `tests/unit/interfaces/cli/commands/test_export_support.py`,
  `tests/unit/interfaces/cli/commands/test_export.py`;
- rollout closeout:
  `tests/architecture/test_observability_export_dashboard_rollout_closeout.py`.
