______________________________________________________________________

Status: generated
Class: repo-only
Owner: BioETL Team
Last verified: '2026-08-05'

______________________________________________________________________

> **Generated artifact** (not human SSOT). Produced by
> `python -m scripts.schema.generate_config_matrix` (or project wrapper).
> Do not hand-edit; regenerate after config-surface changes.

# Config Discrepancies Report

Total configs: 27
Total unique parameters: 419
Actionable inconsistent parameters: 0
Sanctioned partial variance parameters: 0
Raw partial parameter count: 0

## Actionable Drift Parameters

No unsanctioned config drift detected.

## Sanctioned Partial Variance Parameters

These parameters are intentionally partial across governed config families and remain tracked as sanctioned variance rather than actionable drift.

No sanctioned partial variance detected.

## Parameter Ownership Taxonomy

Parameter ownership taxonomy is derived from flattened config parameter paths. It is a governance/reporting projection, not a second config source of truth.


### composite_runtime

Owner: BioETL Team
Parameters: 157

- `domain_entity_contract`: 100
- `dq_validation`: 36
- `medallion_write_policy`: 5
- `provider_source_access`: 3
- `replay_provenance`: 5
- `runtime_control_plane`: 8

### entity_effective

Owner: BioETL Team
Parameters: 262

- `domain_entity_contract`: 36
- `dq_validation`: 57
- `medallion_write_policy`: 105
- `provider_source_access`: 34
- `replay_provenance`: 3
- `runtime_control_plane`: 27

## Interpretation

- CI should fail on actionable drift.
- Sanctioned partial variance remains inventory debt, not a merge blocker, while its governance contract stays current.