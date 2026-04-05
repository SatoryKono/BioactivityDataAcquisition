# Migrations

- `active/`: repeatable migrations that remain part of supported operational flows.
- `oneoff/`: one-time migrations that must define explicit sunset/deprecation policy.

Canonical active migration entrypoints currently retained:

- `scripts/migrations/active/backfill_vcr_metadata_sidecars.py`

Canonical one-off migration entrypoints currently retained:

- `scripts/migrations/oneoff/migrate_exemption_keys_to_paths.py`
- `scripts/migrations/oneoff/migrate_vcr_extensionless.py`
