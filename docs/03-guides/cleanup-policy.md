# Cleanup Policy

*Синхронизировано с RULES.md v5.20 (2026-01-06)*

This document defines deterministic cleanup rules and automation for removing caches, build artifacts, and temporary files.

## Уровни Требований (RFC 2119)

- **MUST**: Абсолютное требование.
- **SHOULD**: Сильная рекомендация.
- **MAY**: На усмотрение разработчика.

## 1. Whitelist Patterns (Cleanup Targets)

### 1.1. Python Artifacts

- `**/--pycache--/`
- `.pytest-cache/`
- `.mypy-cache/`
- `.ruff-cache/`
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
- `full-log.txt`
- `final-report*.txt`
- `project-rules-failures.txt`

### 1.5. IDE/OS

- `.idea/workspace.xml`
- `.DS-Store`
- `Thumbs.db`
- `.ipynb-checkpoints/`

### 1.6. JavaScript (if applicable)

- `node-modules/`
- `.next/`
- `web/dist/`

### 1.7. Vercel Cache

- `.vercel/cache/` (keep `.vercel/project.json`)

## 2. Exclusions (MUST NOT Remove)

| Path                      | Reason           |
| ------------------------- | ---------------- |
| `src/**`                  | Source code      |
| `configs/**`              | Runtime configs  |
| `tests/**`                | Tests            |
| `docs/**`                 | Documentation    |
| `qc/golden/**`            | Golden test data |
| `data/input/**`           | Input datasets   |
| `.gitignore`              | Git config       |
| `.pre-commit-config.yaml` | Pre-commit hooks |
| `.vscode/settings.json`   | IDE settings     |
| `.windsurf/**`            | Windsurf rules   |
| `.trae/**`                | Trae rules       |
| `.cursor/rules/**`        | Cursor rules     |

## 3. Data Retention (Medallion Architecture)

### 3.1. Bronze Layer

| Parameter | Value                                                 |
| --------- | ----------------------------------------------------- |
| Retention | 90 дней hot → Archive (local archive policy)          |
| Format    | JSONL + zstd                                          |
| Path      | `bronze/{format-version}/{provider}/{entity}/{date}/` |

### 3.2. Silver Layer

| Parameter | Value                                           |
| --------- | ----------------------------------------------- |
| Retention | Постоянно                                       |
| Format    | Delta Lake                                      |
| VACUUM    | **MUST** еженедельно, `retention-period=7 days` |
| Forensic  | 7 дней (default), 30 дней для Critical tables   |

### 3.3. Gold Layer

| Parameter | Value         |
| --------- | ------------- |
| Retention | Постоянно     |
| Format    | Delta/Parquet |

### 3.4. Quarantine (`common.quarantine`)

| Parameter | Value                                |
| --------- | ------------------------------------ |
| Retention | 30 дней (local retention policy)     |
| Triage    | Еженедельно                          |
| Purge     | `make quarantine-purge PIPELINE=...` |

### 3.5. Logs and Metrics

| Type    | Retention |
| ------- | --------- |
| Logs    | 30 дней   |
| Metrics | 90 дней   |

## 4. Automation

### 4.1. .gitignore (MUST)

All whitelist patterns **MUST** be in `.gitignore`.

### 4.2. Cleanup Script

Location: `src/tools/cleanup-project.py`

| Flag             | Behavior                                     |
| ---------------- | -------------------------------------------- |
| `--dry-run`      | Prints candidates and sizes (default)        |
| `--apply`        | Deletes candidates                           |
| `--archive-logs` | Moves logs to `reports/` instead of deleting |
| `--purge-logs`   | Forces deletion of logs                      |

Logging: Structured JSON via `UnifiedLogger`.

### 4.3. Delta Lake VACUUM (MUST)

```bash
# Weekly VACUUM for Silver tables
make vacuum-silver RETENTION-DAYS=7
```

**VACUUM MUST** запускаться еженедельно для:

- Очистки старых файлов.
- Уменьшения стоимости хранения.

### 4.4. Quarantine Operations

```bash
# Inspect quarantine errors
make quarantine-inspect PIPELINE=chembl-activity

# Replay corrected records
make quarantine-replay PIPELINE=chembl-activity

# Purge old quarantine data
make quarantine-purge PIPELINE=chembl-activity
```

## 5. Verification (MUST)

### 5.1. Post-Cleanup Validation

| Check                     | Command                                                     |
| ------------------------- | ----------------------------------------------------------- |
| Tests pass                | `pytest -q` (without network)                               |
| Golden tests green        | `pytest tests/golden/ -v`                                   |
| Class inventory unchanged | Compare `tests/project-rules/class-inventory-baseline.json` |
| Smoke run                 | One pipeline, identical artifacts                           |

### 5.2. Checksum Verification

After cleanup, verify checksums of critical artifacts:

```bash
make verify-checksums
```

## 6. Commands

### 6.1. Basic Operations

```bash
# Dry-run (default)
python src/tools/cleanup-project.py

# Apply with log archive
python src/tools/cleanup-project.py --apply --archive-logs

# Full purge
python src/tools/cleanup-project.py --apply --purge-logs
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
make quarantine-inspect PIPELINE=chembl-activity

# Replay after fix
make quarantine-replay PIPELINE=chembl-activity BATCH-ID=...

# Purge old records
make quarantine-purge DAYS=30
```

## 7. CI & Pre-commit

### 7.1. Pre-commit Hooks (MUST)

`.pre-commit-config.yaml` **MUST** forbid:

- `*.pyc`
- `--pycache--`
- `.env` files with secrets

### 7.2. CI Workflow

`compiled-artifacts-block.yml` **MUST** fail builds if compiled artifacts are present.

### 7.3. Root Audit Artifacts Policy (MUST)

Root-level audit artifacts **MUST NOT** be committed.

| Artifact           | Generator                                                      | Frequency              | Storage Policy                                                                               |
| ------------------ | -------------------------------------------------------------- | ---------------------- | -------------------------------------------------------------------------------------------- |
| `coverage.json`    | Local `pytest --cov ... --cov-report=json` or CI coverage jobs | On demand / per CI run | Keep local only; attach to CI artifacts if needed; never commit to repository root           |
| `all-fixtures.txt` | Fixture inventory/debug scripts run by maintainers             | On demand              | Keep local only; if needed for review, attach to PR/CI artifacts, not git-tracked root files |

Enforcement:

- `.gitignore` **MUST** include `/coverage.json` and `/all-fixtures.txt`.
- CI **MUST** run a root-level allowlist check from `.github/root-allowlist.txt`.
- Any intentional new root-level tracked file **MUST** be added to `.github/root-allowlist.txt` in the same PR with justification.

### 7.4. Scheduled Jobs (SHOULD)

| Job                | Schedule                  | Action                 |
| ------------------ | ------------------------- | ---------------------- |
| `vacuum-silver`    | Weekly (Sunday 02:00 UTC) | VACUUM Delta tables    |
| `quarantine-purge` | Daily (03:00 UTC)         | Purge records >30 days |
| `log-rotate`       | Daily (04:00 UTC)         | Archive logs >30 days  |

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
make full-rebuild PIPELINE=chembl-activity
```

### 8.2. Checkpoint Cleanup

Stale checkpoints **SHOULD** be cleaned after successful pipeline completion:

```python
# After successful run
async def cleanup-checkpoint(run-id: UUID) -> None:
    checkpoint-path = f"data/output/checkpoints/{run-id}.json"
    await s3.delete(checkpoint-path)
    logger.info("Checkpoint deleted", run-id=str(run-id))
```

## 9. Environment-Specific Cleanup

### 9.1. Dev Environment

```bash
# Full cleanup for dev
make clean-dev
# Equivalent to:
# python src/tools/cleanup-project.py --apply --purge-logs
# docker-compose down -v
```

### 9.2. Staging Environment

```bash
# Staging cleanup (preserve data structure)
make clean-staging
```

### 9.3. Prod Environment

Production cleanup **MUST** be done through CI/CD only. Manual cleanup **MUST NOT**.

| Action           | Approval Required           |
| ---------------- | --------------------------- |
| VACUUM           | No (automated)              |
| Quarantine purge | No (automated, >30 days)    |
| Bronze archive   | No (local retention policy) |
| Manual delete    | Yes (P0 incident only)      |
