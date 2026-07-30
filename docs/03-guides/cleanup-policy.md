______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Cleanup Policy

*Синхронизировано с RULES.md v6.1 (2026-03-13)*

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
- `reports/coverage/coverage.xml`
- `reports/coverage/htmlcov/`
- legacy root outputs: `coverage.xml`, `htmlcov/`

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
- `.idea/shelf/`
- `.idea/dataSources*/`
- `.idea/.ai/`
- `.idea/AICommit.xml`
- `.idea/claudeCodeTabState.xml`
- `.idea/codex.xml`
- `.idea/copilot.data.migration*.xml`
- `.idea/csv-editor.xml`
- `.idea/git_toolbox_prj.xml`
- `.idea/junie.xml`
- `.idea/sonarlint.xml`
- `.idea/webResources.xml`
- `.sonarlint/connectedMode.json`
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

### 2.1. Root Env and Tooling Surfaces

Root env-like files are security-review surfaces, not cleanup targets:

- `.env`, `.env.*`, `*.env`, and `new.env` MUST NOT be read, printed, moved,
  renamed, overwritten, or deleted by automated cleanup.
- `.env.example` is the only tracked root env template and MUST remain free of
  real secrets.
- Any local env cleanup requires explicit per-task user approval and a
  path-specific security review.
- Cleanup evidence MUST classify env-like local files as
  `SECURITY_REVIEW_REQUIRED` or blocked, never as automatically safe.

Root AI/editor/runtime tooling decisions live in
`configs/quality/root_hygiene_review_registry.yaml`. Canonical runtime roots
such as `.codex/**` and `.gemini/**` are retained unless a separate runtime
migration decision changes the source of truth. Local cache/editor/vendor roots
such as `.agents`, `.ai`, `.cache`, `.npm-cache`, `caddy`, `.junie/history/`,
`.junie/state/`, `.junie/cache/`, `.sonarlint`, and `.windsurf` must remain
untracked or be reclassified through
the registry before any rehome/delete action.

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

| Parameter | Value                                    |
| --------- | ---------------------------------------- |
| Retention | 30 дней (local retention policy)         |
| Triage    | Еженедельно                              |
| Purge     | `bioetl quarantine purge --pipeline ...` |

### 3.5. Logs and Metrics

| Type    | Retention |
| ------- | --------- |
| Logs    | 30 дней   |
| Metrics | 90 дней   |

## 4. Automation

### 4.1. .gitignore (MUST)

All whitelist patterns **MUST** be in `.gitignore`.

### 4.2. Cleanup Automation (Makefile)

Основной путь deterministic local cleanup — цели в `Makefile`, которые
маршрутизируют в поддерживаемые `scripts.engineering.*` entrypoints:

| Command                                        | Behavior                                                                        |
| ---------------------------------------------- | ------------------------------------------------------------------------------- |
| `make clean`                                   | Local-only cleanup через `python -m scripts.engineering.diagnostics cleanup`    |
| `make clean-local-artifacts DRY_RUN=1`         | Preview локальной cleanup wave                                                  |
| `make clean-local-artifacts`                   | Применяет локальную cleanup wave, включая forbidden root outputs и `logs/`      |
| `make clean-local-artifacts PURGE_WORKTREES=1` | Дополнительно очищает локальные `.worktrees/.rollback`                          |
| `make clean-preflight DRY_RUN=1`               | Preview preflight-очистки через `python -m scripts.engineering.repo preflight-cleanup` |
| `make clean-all`                               | `clean` + purge локальных логов                                                 |

`scripts/ops/support/repo/cleanup_repository.py` больше не является broad
first-line cleanup tool. Он используется как deterministic repo-hygiene review
lane для exact candidate discovery, а не как blanket delete utility.

Cleanup proposals touching retention-sensitive or blocked surfaces MUST use the
dedicated GitHub template
`.github/ISSUE_TEMPLATE/retention_sensitive_cleanup.yml` or include the same
candidate inventory, classification table, dry-run evidence, reviewed apply
list, verification output, and rollback note.

Fixture, VCR, and golden pruning is inventory-driven only:

- VCR cassette removal requires metadata ownership, reachability evidence from
  `reports/quality/vcr-metadata-catalog.json`, and targeted replay/contract
  verification.
- Bronze fixture changes must keep `configs/base/bronze_fixture_gaps.yaml`
  empty unless every residual gap is explicitly owned.
- Golden fixture removal requires a reviewed replacement or replay/golden-test
  evidence. Filename age or broad text-search absence is not sufficient.
- The pruning policy is tracked in `configs/quality/fixture_governance_ledger.yaml`.

### 4.3. Delta Lake VACUUM (MUST)

**VACUUM MUST** запускаться еженедельно для:

- Очистки старых файлов.
- Уменьшения стоимости хранения.

### 4.4. Quarantine Operations

```bash
# Inspect quarantine errors
bioetl quarantine inspect --pipeline chembl_activity

# Replay corrected records
bioetl quarantine replay --pipeline chembl_activity

# Purge old quarantine data
bioetl quarantine purge --pipeline chembl_activity
```

## 5. Verification (MUST)

### 5.1. Post-Cleanup Validation

| Check                  | Command                                                                         |
| ---------------------- | ------------------------------------------------------------------------------- |
| Tests pass             | `pytest -q` (without network)                                                   |
| Smoke tests green      | `pytest tests/smoke/ -q`                                                        |
| Structure policy green | `python3 scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked` |
| Smoke run              | One pipeline, identical artifacts                                               |

### 5.2. Structural Verification

After cleanup, verify repository hygiene and structure policy:

```bash
python3 scripts/engineering/repo/audit_root_cleanliness.py
python3 scripts/engineering/diagnostics/audit_structure.py --path .
```

## 6. Commands

### 6.1. Basic Operations

```bash
# Python/cache/build cleanup
make clean

# Full cleanup (includes logs/temp files)
make clean-all

# Exact repo-hygiene review lane without mutation
python -m scripts.ops.support.repo.cleanup_repository --dry-run
```

### 6.2. Local Artifact Cleanup

```bash
# Preview before applying cleanup
make clean-local-artifacts DRY_RUN=1

# Apply cleanup
make clean-local-artifacts

# Include local .worktrees/.rollback purge
make clean-local-artifacts PURGE_WORKTREES=1
```

### 6.3. Quarantine Management

```bash
# Inspect specific pipeline
bioetl quarantine inspect --pipeline chembl_activity

# Replay after fix
bioetl quarantine replay --pipeline chembl_activity

# Purge old records
bioetl quarantine purge --pipeline chembl_activity
```

## 7. CI & Pre-commit

### 7.1. Pre-commit Hooks (MUST)

`.pre-commit-config.yaml` **MUST** forbid:

- `*.pyc`
- `__pycache__/`
- `.env` files with secrets

### 7.2. CI Workflow

`compiled-artifacts-block.yml` **MUST** fail builds if compiled artifacts are present.

### 7.3. Root Audit Artifacts Policy (MUST)

Root-level audit artifacts **MUST NOT** be committed.

| Artifact           | Generator                                                      | Frequency              | Storage Policy                                                                               |
| ------------------ | -------------------------------------------------------------- | ---------------------- | -------------------------------------------------------------------------------------------- |
| `coverage.json`    | Local `pytest --cov ... --cov-report=json` or CI coverage jobs | On demand / per CI run | Keep local only; attach to CI artifacts if needed; never commit to repository root           |
| `all_fixtures.txt` | Fixture inventory/debug scripts run by maintainers             | On demand              | Keep local only; if needed for review, attach to PR/CI artifacts, not git-tracked root files |

Enforcement:

- `.gitignore` **MUST** include `/coverage.json` and `/all_fixtures.txt`.
- CI **MUST** run `scripts/engineering/repo/audit_root_cleanliness.py --strict-untracked`;
  this
  validates `.github/root-allowlist.txt` and blocks tracked root/generated
  artifact regressions such as root coverage files, root Python helpers,
  non-canonical root text files, `src/tools/reports/`, and local runtime
  output trees.
- CI **MUST** run cleanup governance checks that block broad cleanup guidance
  from active docs/scripts and export deterministic cleanup classification
  evidence for review.
- Target state: GitHub branch protection for `main` **SHOULD** require the
  `root-hygiene` status check when repository rulesets are enabled.
- Current-state enforcement is tracked in
  `docs/00-project/governance/05-github-policy.md`; do not treat this cleanup
  guide as live branch-protection evidence on its own.
- Any intentional new root-level tracked file **MUST** be added to `.github/root-allowlist.txt` in the same PR with justification.

### 7.4. Scheduled Jobs (SHOULD)

| Job                 | Schedule   | Action                                       |
| ------------------- | ---------- | -------------------------------------------- |
| `root-hygiene`      | On PR/Push | Проверка root allowlist                      |
| `no-pyc-check`      | On PR/Push | Блокировка `*.pyc` / `__pycache__`           |
| `preflight cleanup` | On demand  | Локальная/операционная очистка перед релизом |

## 8. Disaster Recovery Cleanup

### 8.1. After DR Restore

```bash
# 1. Validate repository hygiene
python3 scripts/engineering/repo/audit_root_cleanliness.py

# 2. Run cleanup preflight
make clean-preflight DRY_RUN=1

# 3. Quarantine triage for affected pipeline
bioetl quarantine inspect --pipeline chembl_activity
bioetl quarantine replay --pipeline chembl_activity
bioetl quarantine purge --pipeline chembl_activity
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
# Safe preview
make clean-local-artifacts DRY_RUN=1

# Apply local cleanup
make clean-local-artifacts

# Optional: purge local worktrees/rollback snapshots
make clean-local-artifacts PURGE_WORKTREES=1
```

### 9.2. Staging-Like Local Profile

```bash
# Staging-like profile cleanup (preserve tracked project structure)
make clean
make clean-preflight
```

### 9.3. Production-Like Local Profile

Production-like local cleanup SHOULD run inside a change window with a backup or
restore point available. Repository cleanup is manual/operator-driven in the
current Local-Only runtime; no CI/CD-only cleanup path is required.

| Action           | Approval Required              |
| ---------------- | ------------------------------ |
| VACUUM           | No (automated)                 |
| Quarantine purge | No (automated, >30 days)       |
| Bronze archive   | No (local retention policy)    |
| Manual delete    | Yes (change window / incident) |
