# Cleanup Policy
*Синхронизировано с RULES.md v5.0 (2025-12-15)*

This document defines deterministic cleanup rules and automation for removing caches, build artifacts, and temporary files.

## Уровни Требований (RFC 2119)
- **MUST**: Абсолютное требование.
- **SHOULD**: Сильная рекомендация.
- **MAY**: На усмотрение разработчика.

## 1. Whitelist Patterns (Cleanup Targets)

### 1.1. Python Artifacts
- `**/__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `**/*.pyc`, `**/*.pyo`, `**/*.pyd`

### 1.2. Coverage
- `.coverage*`
- `coverage.xml`
- `htmlcov/`

### 1.3. Build/Dist
- `build/`
- `dist/`
- `**/*.egg-info/`

### 1.4. Logs/Temp
- `**/*.log`
- `**/*.tmp`
- `**/*report*.txt`
- `full_log.txt`
- `final_report*.txt`
- `project_rules_failures.txt`

### 1.5. IDE/OS
- `.idea/workspace.xml`
- `.DS_Store`
- `Thumbs.db`
- `.ipynb_checkpoints/`

### 1.6. JavaScript (if applicable)
- `node_modules/`
- `.next/`
- `web/dist/`

### 1.7. Vercel Cache
- `.vercel/cache/` (keep `.vercel/project.json`)

## 2. Exclusions (MUST NOT Remove)

| Path | Reason |
|------|--------|
| `src/**` | Source code |
| `configs/**` | Runtime configs |
| `tests/**` | Tests |
| `docs/**` | Documentation |
| `qc/golden/**` | Golden test data |
| `data/input/**` | Input datasets |
| `.gitignore` | Git config |
| `.pre-commit-config.yaml` | Pre-commit hooks |
| `.vscode/settings.json` | IDE settings |
| `.windsurf/**` | Windsurf rules |
| `.trae/**` | Trae rules |
| `.cursor/rules/**` | Cursor rules |

## 3. Data Retention (Medallion Architecture)

### 3.1. Bronze Layer
| Parameter | Value |
|-----------|-------|
| Retention | 90 дней hot → Archive (S3 Lifecycle) |
| Format | JSONL + zstd |
| Path | `bronze/{format_version}/{provider}/{entity}/{date}/` |

### 3.2. Silver Layer
| Parameter | Value |
|-----------|-------|
| Retention | Постоянно |
| Format | Delta Lake |
| VACUUM | **MUST** еженедельно, `retention_period=7 days` |
| Forensic | 7 дней (default), 30 дней для Critical tables |

### 3.3. Gold Layer
| Parameter | Value |
|-----------|-------|
| Retention | Постоянно |
| Format | Delta/Parquet |

### 3.4. Quarantine (`common.quarantine`)
| Parameter | Value |
|-----------|-------|
| Retention | 30 дней (S3 Lifecycle) |
| Triage | Еженедельно |
| Purge | `make quarantine-purge PIPELINE=...` |

### 3.5. Logs and Metrics
| Type | Retention |
|------|-----------|
| Logs | 30 дней |
| Metrics | 90 дней |

## 4. Automation

### 4.1. .gitignore (MUST)

All whitelist patterns **MUST** be in `.gitignore`.

### 4.2. Cleanup Script

Location: `src/tools/cleanup_project.py`

| Flag | Behavior |
|------|----------|
| `--dry-run` | Prints candidates and sizes (default) |
| `--apply` | Deletes candidates |
| `--archive-logs` | Moves logs to `reports/` instead of deleting |
| `--purge-logs` | Forces deletion of logs |

Logging: Structured JSON via `UnifiedLogger`.

### 4.3. Delta Lake VACUUM (MUST)

```bash
# Weekly VACUUM for Silver tables
make vacuum-silver RETENTION_DAYS=7
```

**VACUUM MUST** запускаться еженедельно для:
- Очистки старых файлов.
- Уменьшения стоимости хранения.

### 4.4. Quarantine Operations

```bash
# Inspect quarantine errors
make quarantine-inspect PIPELINE=chembl_activity

# Replay corrected records
make quarantine-replay PIPELINE=chembl_activity

# Purge old quarantine data
make quarantine-purge PIPELINE=chembl_activity
```

## 5. Verification (MUST)

### 5.1. Post-Cleanup Validation

| Check | Command |
|-------|---------|
| Tests pass | `pytest -q` (without network) |
| Golden tests green | `pytest tests/golden/ -v` |
| Class inventory unchanged | Compare `tests/project_rules/class_inventory_baseline.json` |
| Smoke run | One pipeline, identical artifacts |

### 5.2. Checksum Verification

After cleanup, verify checksums of critical artifacts:
```bash
make verify-checksums
```

## 6. Commands

### 6.1. Basic Operations

```bash
# Dry-run (default)
python src/tools/cleanup_project.py

# Apply with log archive
python src/tools/cleanup_project.py --apply --archive-logs

# Full purge
python src/tools/cleanup_project.py --apply --purge-logs
```

### 6.2. Delta Lake Maintenance

```bash
# VACUUM all Silver tables
make vacuum-silver

# VACUUM specific table
make vacuum-table TABLE=silver/chembl/activity
```

### 6.3. Quarantine Management

```bash
# Weekly triage
make quarantine-triage

# Inspect specific pipeline
make quarantine-inspect PIPELINE=chembl_activity

# Replay after fix
make quarantine-replay PIPELINE=chembl_activity BATCH_ID=...

# Purge old records
make quarantine-purge DAYS=30
```

## 7. CI & Pre-commit

### 7.1. Pre-commit Hooks (MUST)

`.pre-commit-config.yaml` **MUST** forbid:
- `*.pyc`
- `__pycache__`
- `.env` files with secrets

### 7.2. CI Workflow

`compiled-artifacts-block.yml` **MUST** fail builds if compiled artifacts are present.

### 7.3. Scheduled Jobs (SHOULD)

| Job | Schedule | Action |
|-----|----------|--------|
| `vacuum-silver` | Weekly (Sunday 02:00 UTC) | VACUUM Delta tables |
| `quarantine-purge` | Daily (03:00 UTC) | Purge records >30 days |
| `log-rotate` | Daily (04:00 UTC) | Archive logs >30 days |

## 8. Disaster Recovery Cleanup

### 8.1. After DR Restore

```bash
# 1. Verify restored data
make verify-checksums

# 2. Clean stale checkpoints
make cleanup-checkpoints

# 3. Reset quarantine state
make quarantine-reset

# 4. Rebuild Silver (if needed)
make full-rebuild PIPELINE=chembl_activity
```

### 8.2. Checkpoint Cleanup

Stale checkpoints **SHOULD** be cleaned after successful pipeline completion:

```python
# After successful run
async def cleanup_checkpoint(run_id: UUID) -> None:
    checkpoint_path = f"s3://bioetl/checkpoints/{run_id}.json"
    await s3.delete(checkpoint_path)
    logger.info("Checkpoint deleted", run_id=str(run_id))
```

## 9. Environment-Specific Cleanup

### 9.1. Dev Environment

```bash
# Full cleanup for dev
make clean-dev
# Equivalent to:
# python src/tools/cleanup_project.py --apply --purge-logs
# docker-compose down -v
```

### 9.2. Staging Environment

```bash
# Staging cleanup (preserve data structure)
make clean-staging
```

### 9.3. Prod Environment

Production cleanup **MUST** be done through CI/CD only. Manual cleanup **MUST NOT**.

| Action | Approval Required |
|--------|-------------------|
| VACUUM | No (automated) |
| Quarantine purge | No (automated, >30 days) |
| Bronze archive | No (S3 Lifecycle) |
| Manual delete | Yes (P0 incident only) |
