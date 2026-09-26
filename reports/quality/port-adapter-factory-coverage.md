# Port Adapter Factory Coverage

- schema_version: 1.0.0
- scope: core_active_ports
- row_count: 10
- covered_count: 10
- unresolved_count: 0

| port | status | adapters | factories | tests | missing_surfaces |
| --- | --- | --- | ---: | ---: | --- |
| `DataSourcePort` | `covered` | `ChemblAdapter`, `PubChemAdapter`, `UniProtAdapter` | 3 | 3 | - |
| `CheckpointPort` | `covered` | `LocalCheckpointAdapter` | 3 | 3 | - |
| `QuarantinePort` | `covered` | `UnifiedQuarantineAdapter` | 3 | 3 | - |
| `RunManifestPort` | `covered` | `FileRunManifestStore` | 2 | 3 | - |
| `RunLedgerPort` | `covered` | `FileRunLedgerStore` | 2 | 3 | - |
| `MetricsPort` | `covered` | `PrometheusMetrics`, `NoOpMetrics` | 2 | 3 | - |
| `ClockPort` | `covered` | `SystemClock` | 3 | 3 | - |
| `BronzeStoragePort` | `covered` | `StorageBundle`, `BronzeWriter` | 2 | 3 | - |
| `SilverStoragePort` | `covered` | `StorageBundle`, `SilverWriter` | 2 | 3 | - |
| `GoldStoragePort` | `covered` | `StorageBundle`, `GoldWriter` | 2 | 3 | - |
