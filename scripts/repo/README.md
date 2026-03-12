# scripts/repo — Repository Governance

Repository hygiene and inventory governance tooling.

## Unified Entry Point

```bash
python -m scripts.repo --help
python -m scripts.repo <command> [args...]
```

## Commands

| Command | Script | Description |
|---------|--------|-------------|
| `check-inventory` | `check_scripts_inventory.py` | Check scripts inventory drift against manifest |
| `check-catalog` | `check_scripts_catalog.py` | Validate catalog governance policy |
| `check-versions` | `check_version_consistency.py` | Check version consistency across project files |
| `check-cleanliness` | `audit_root_cleanliness.py` | Audit repository root layout allowlist |
| `all` | *(all above)* | Run all checks sequentially |

## Other Files

| File | Description |
|------|-------------|
| `preflight_cleanup.sh` | Pre-commit cleanup helper |
