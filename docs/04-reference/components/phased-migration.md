# Phased migration runtime — retired

The historical `PhasedMigrationCoordinator` runtime and its compatibility shim
are retired. BioETL no longer performs dynamic phased-migration fallback in the
domain layer.

Current configuration compatibility is governed through
`configs/quality/config_compatibility_registry.yaml`. New code must use the
canonical configuration models and migration rules referenced by that registry;
it must not import `bioetl.domain.behavior.phased_migration_support` or
`PhasedMigrationCoordinator`.

The absence of the retired import surface is enforced by
`tests/architecture/test_tech_debt_issues_5811_5816_closeout.py`. Reintroducing
it would create transition compatibility debt and violate the repository's
zero-growth compatibility budget.
