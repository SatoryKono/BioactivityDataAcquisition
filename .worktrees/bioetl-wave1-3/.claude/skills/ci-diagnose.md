# /ci-diagnose

Диагностика падающих CI workflows для BioETL.

## Использование

```
/ci-diagnose [action] [target]
```

**Действия:**
- `status` — показать статус всех workflows (по умолчанию)
- `investigate` — разобрать конкретный падающий workflow
- `reproduce` — воспроизвести CI локально
- `fix` — предложить fix для падения

**Target (опционально):**
- Имя workflow: `tests`, `security`, `type-checking`, `architecture`, `docs`,
  `import-linter`, `contract-tests`, `schema-governance`, `mutation-testing`,
  `duplication-complexity`, `vacuum`, `validate-mermaid`, `root-hygiene`,
  `compiled-artifacts-block`, `commit-lint`, `port-contracts`
- URL PR/run из GitHub Actions
- Без target — все workflows

**Примеры:**
```
/ci-diagnose                                # статус всех workflows
/ci-diagnose investigate tests              # разобрать падение tests.yml
/ci-diagnose reproduce type-checking        # воспроизвести mypy CI локально
/ci-diagnose fix architecture               # предложить fix для arch CI
```

---

## Инструкции для Claude

### Действие: `status` (по умолчанию)

**Шаг 1: Inventory всех workflows**
```bash
ls .github/workflows/*.yml | sort
```

**Шаг 2: Карта workflows**

| Workflow | Файл | Что проверяет | Локальный аналог |
|----------|------|---------------|-----------------|
| Tests | `tests.yml` | unit/integration/e2e/arch | `make test` |
| Security | `security.yml` | secrets + pip-audit | `make security` |
| Type Checking | `type-checking.yml` | mypy --strict | `uv run mypy --strict src/bioetl/` |
| Architecture | `architecture.yml` | arch tests | `uv run pytest tests/architecture/ -v` |
| Docs | `docs.yml` | mkdocs build | `mkdocs build --strict` |
| Import Linter | `import-linter.yml` | import boundaries | `make arch-lint` |
| Contract Tests | `contract-tests.yml` | API contracts | `uv run pytest tests/contract/ -v` |
| Schema Governance | `schema-governance.yml` | schema parity | `uv run python src/tools/verify_schema_parity.py` |
| Mutation Testing | `mutation-testing.yml` | mutmut | `uv run mutmut run` |
| Duplication | `duplication-complexity.yml` | radon/xenon | `uv run xenon --max-average B src/bioetl/` |
| Vacuum | `vacuum.yml` | dead code | `uv run vulture src/bioetl/` |
| Mermaid | `validate-mermaid.yml` | diagram syntax | `make validate-diagrams-syntax` |
| Root Hygiene | `root-hygiene.yml` | root file checks | — |
| Compiled Artifacts | `compiled-artifacts-block.yml` | no .pyc in repo | — |
| Commit Lint | `commit-lint.yml` | conventional commits | — |
| Port Contracts | `port-contracts.yml` | port compliance | `uv run pytest tests/architecture/ -k port` |

### Действие: `investigate`

**Шаг 1:** Прочитать workflow файл:
```bash
cat .github/workflows/{workflow}.yml
```

**Шаг 2:** Воспроизвести локально (см. таблицу "Локальный аналог")

**Шаг 3:** Если есть URL — получить лог:
```bash
gh run view {run_id} --log-failed 2>&1 | tail -50
```

**Шаг 4:** Классифицировать падение:

| Категория | Признаки | Действие |
|-----------|----------|----------|
| Flaky | Нестабильно | Перезапустить, проверить shared state |
| Dependency | pip-audit/CVE | Обновить зависимость |
| Code | Тест/lint/type error | Исправить код |
| Config | YAML/schema error | Исправить конфиг |
| Infrastructure | Network/timeout | Проверить VCR cassettes |
| Version | Python version diff | Проверить compatibility |

**Шаг 5:** Сформировать диагноз:
```
CI Diagnosis: {workflow}
========================
Status: FAILING
Root cause: {category} — {description}
Evidence: {command output}
Recommended fix: {action}
Local reproduction: {command}
```

### Действие: `reproduce`

Запустить локальный аналог workflow:
```bash
# Для каждого workflow — соответствующая make/pytest команда
make {target}
```

### Действие: `fix`

1. Запустить `investigate`
2. На основе диагноза предложить конкретный fix
3. Применить fix (если пользователь согласен)
4. Запустить `reproduce` для верификации
