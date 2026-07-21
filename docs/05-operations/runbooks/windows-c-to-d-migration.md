______________________________________________________________________

Version: 1.0.0
Status: active
Class: runbook
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-21'

______________________________________________________________________

# Windows workstation migration: C: to D: (legacy app cleanup)

## Trigger

Use this runbook when a workstation migration plan exists in
`D:\migration-plan-C-to-D.md` and the user needs an operator-safe way to
execute it with audit logs and repeatable checkpoints.

## Impact

Potentially significant local workspace, IDE, and developer-tool movement.
Changes should stay limited to explicitly approved binaries and data roots.

## Preconditions

- Confirm local governance constraints: Docker, WSL, VM, Hyper-V objects are out of scope.
- Create OS restore point.
- Verify write access to `D:\Migration_Backup\2026-07-21` and `D:\Migration_Logs`.
- Verify `D:` has at least 85 GiB free before each wave.

## Procedure

1. Inspect the plan and generate wave previews:

```powershell
pwsh -NoProfile -File scripts/ops/migrations/windows_disk_to_d_migration.ps1 `
  -PlanPath 'D:\migration-plan-C-to-D.md' `
  -BackupRoot 'D:\Migration_Backup\2026-07-21' `
  -LogRoot 'D:\Migration_Logs' `
  -Waves Wave1,Wave2,Wave3,Wave4
```

2. Optional narrow run (single app or wave):

```powershell
pwsh -NoProfile -File scripts/ops/migrations/windows_disk_to_d_migration.ps1 `
  -Waves Wave1 `
  -OnlyApps APP-06,APP-07
```

3. For each printed item:
   - execute only backup command template for user data (not installer binaries),
   - run uninstall/install via official installer in custom D:\ path where supported,
   - validate startup + CLI/service/path associations after a reboot,
   - keep rollback evidence in the generated migration log.

## Script responsibilities

- Parse `migration-plan-C-to-D.md` candidate tables into structured action rows.
- Group rows by migration wave.
- Emit per-item backup and validation checklist.
- Validate minimum `D:` free space.
- Write an execution log under `D:\Migration_Logs`.

## Verification

Use this checklist after each app and after each wave:

1. Old location no longer launched by shortcuts, PATH, service, or task.
2. New location referenced where expected.
3. Smoke test: app opens and processes one real document/project.
4. Update/license/extension checks and file associations behave as before.
5. Backup is retained for at least seven days.

## Rollback

Rollback is manual:

- keep backup directories untouched,
- uninstall failed D:\ installation,
- reinstall original version to prior location if required by business continuity,
- restore only user data from backup.

## Notes

- This runbook intentionally avoids destructive automation. It provides a
  guard-railed execution template and traceable command list.
- For script source, see `scripts/ops/migrations/windows_disk_to_d_migration.ps1`.
