---
description: Диагностика падающих CI workflows BioETL (18 workflows). Действия: status, investigate, reproduce, fix. Пример: /ci-diagnose investigate tests
---

# /ci-diagnose

Диагностика падающих CI workflows для BioETL.

## Использование
```
/ci-diagnose [action] [target]
```

**Действия:** `status` (default), `investigate`, `reproduce`, `fix`
**Target:** workflow name, URL, or omit for all.

---

## Инструкции

### `status` (default)

```bash
ls .github/workflows/*.yml | sort
```

**Workflow → Local analog map:**

| Workflow | Файл | Локальный аналог |
|----------|------|-----------------|
| Tests | `tests.yml` | `make test` |
| Security | `security.yml` | `make security` |
| Type Checking | `type-checking.yml` | `uv run mypy --strict src/bioetl/` |
| Architecture | `architecture.yml` | `uv run pytest tests/architecture/ -v` |
| Docs | `docs.yml` | `mkdocs build --strict` |
| Import Linter | `import-linter.yml` | `make arch-lint` |
| Contract Tests | `contract-tests.yml` | `uv run pytest tests/contract/ -v` |
| Schema Governance | `schema-governance.yml` | `uv run python src/tools/verify_schema_parity.py` |
| Mutation Testing | `mutation-testing.yml` | `uv run mutmut run` |
| Duplication | `duplication-complexity.yml` | `uv run xenon --max-average B src/bioetl/` |
| Vacuum | `vacuum.yml` | `uv run vulture src/bioetl/` |
| Mermaid | `validate-mermaid.yml` | `make validate-diagrams-syntax` |
| Root Hygiene | `root-hygiene.yml` | — |
| Compiled Artifacts | `compiled-artifacts-block.yml` | — |
| Commit Lint | `commit-lint.yml` | — |
| Port Contracts | `port-contracts.yml` | `uv run pytest tests/architecture/ -k port` |

### `investigate`

1. Read workflow: `.github/workflows/{workflow}.yml`
2. Reproduce locally (see table above)
3. If URL provided: `gh run view {run_id} --log-failed 2>&1 | tail -50`
4. Classify failure:

| Категория | Признаки | Действие |
|-----------|----------|----------|
| Flaky | Нестабильно | Перезапустить, проверить shared state |
| Dependency | pip-audit/CVE | Обновить зависимость |
| Code | Тест/lint/type error | Исправить код |
| Config | YAML/schema error | Исправить конфиг |
| Infrastructure | Network/timeout | Проверить VCR cassettes |
| Version | Python version diff | Проверить compatibility |

5. Output:
```
CI Diagnosis: {workflow}
========================
Status: FAILING
Root cause: {category} — {description}
Evidence: {command output}
Recommended fix: {action}
Local reproduction: {command}
```

### `reproduce`
Run local analog from the workflow map table.

### `fix`
1. `investigate` → 2. Propose fix → 3. Apply (if approved) → 4. `reproduce` to verify.
