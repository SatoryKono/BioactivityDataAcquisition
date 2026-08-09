# Migrations

- `active/`: repeatable migrations that remain part of supported operational flows.
- `oneoff/`: one-time migrations that must define explicit sunset/deprecation policy.

## Lifecycle Policy

See `LIFECYCLE.md` for the complete migration script lifecycle policy, including:
- Sunset date requirements
- Lifecycle stages (Active, Deprecated, Sunset)
- Sunset date validation
- Archive policy
- Exceptions process

Canonical active migration entrypoints currently retained:

- `scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py`
- `scripts/ops/migrations/windows_disk_to_d_migration.ps1` (checklist runner for external Windows disk migration plans)

Canonical one-off migration entrypoints currently retained:

- `scripts/ops/migrations/oneoff/migrate_exemption_keys_to_paths.py` (SUNSET: 2027-02-09)
- `scripts/ops/migrations/oneoff/migrate_vcr_extensionless.py` (SUNSET: 2027-02-09)
