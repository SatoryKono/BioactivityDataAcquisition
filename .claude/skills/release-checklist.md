# /release-checklist

Pre-release чеклист для BioETL: версии, тесты, документация, CI, security.

## Использование

```
/release-checklist [mode]
```

**Режимы:**
- `check` — проверить готовность к релизу (по умолчанию)
- `prepare` — подготовить релиз (обновить версии, CHANGELOG, docs)
- `validate` — запустить полный набор валидаций

**Примеры:**
```
/release-checklist                          # проверить готовность
/release-checklist prepare                  # подготовить релиз
/release-checklist validate                 # полная валидация
```

---

## Инструкции для Claude

### Режим: `check` (по умолчанию)

Выполнить все проверки и сформировать отчёт:

**1. Version Consistency**
```bash
# Текущая версия
uv run python -c "import bioetl; print(bioetl.__version__)"

# Версия в pyproject.toml
grep "^version" pyproject.toml

# Версия в RULES.md
grep -m1 "version\|Version\|v[0-9]" docs/00-project/RULES.md | head -3
```

Проверить: все версии совпадают?

**2. CHANGELOG**
```bash
head -30 CHANGELOG.md
```

Проверить:
- [ ] `[Unreleased]` секция не пуста
- [ ] Формат Keep-a-Changelog (Added/Changed/Fixed/Removed)
- [ ] Все значимые изменения описаны

**3. Tests**
```bash
uv run python -m pytest tests/ -v --tb=short -q 2>&1 | tail -10
```

Проверить:
- [ ] 0 FAILED
- [ ] Coverage ≥85%
- [ ] Architecture тесты проходят

**4. Type Checking**
```bash
uv run python -m mypy --strict src/bioetl/ 2>&1 | tail -5
```

Проверить: 0 errors

**5. Linting**
```bash
uv run ruff check src/ tests/ 2>&1 | tail -5
uv run ruff format --check src/ tests/ 2>&1 | tail -5
```

**6. Security**
```bash
make security 2>&1 | tail -20
```

Проверить: нет critical vulnerabilities

**7. ADR Status**
```bash
grep -r "Status:" docs/02-architecture/decisions/ADR-*.md | grep -v Accepted | grep -v Superseded
```

Проверить: нет ADR со статусом Draft или Proposed

**8. Documentation**
```bash
# Orphan rate
find docs/ -name "*.md" -not -path "*/99-archive/*" | wc -l
grep -c "\.md" mkdocs.yml
```

Проверить:
- [ ] mkdocs.yml navigation актуальна
- [ ] Orphan rate < 10%
- [ ] docs/00-map.md счётчики верны

**9. Dependencies**
```bash
uv run pip-audit --skip-editable 2>&1 | tail -10
```

**10. Git Status**
```bash
git status --short
git log --oneline -5
```

Проверить: нет uncommitted changes

**Отчёт:**
```
Release Readiness Checklist
===========================
Version: X.Y.Z
Date: YYYY-MM-DD

| # | Check | Status | Details |
|:-:|-------|:------:|---------|
| 1 | Version consistency | ✅/❌ | pyproject.toml, __init__, RULES |
| 2 | CHANGELOG updated | ✅/❌ | Unreleased section |
| 3 | Tests passing | ✅/❌ | N passed, M failed |
| 4 | Coverage ≥85% | ✅/❌ | N% |
| 5 | Architecture tests | ✅/❌ | N/N pass |
| 6 | mypy --strict | ✅/❌ | N errors |
| 7 | Ruff clean | ✅/❌ | N issues |
| 8 | Security scan | ✅/❌ | N vulnerabilities |
| 9 | ADR statuses | ✅/❌ | N draft/proposed |
| 10 | Docs navigation | ✅/❌ | N% orphan rate |
| 11 | Dependencies | ✅/❌ | N CVEs |
| 12 | Git clean | ✅/❌ | N uncommitted |

Overall: READY / NOT READY
Blockers: <list>
```

### Режим: `prepare`

1. Спросить у пользователя тип релиза: `major | minor | patch`
2. Обновить версию:
   ```bash
   make bump-version TYPE={type}
   ```
3. Обновить CHANGELOG: переименовать `[Unreleased]` → `[X.Y.Z] - YYYY-MM-DD`
4. Обновить версию в RULES.md header
5. Запустить `check` для верификации

### Режим: `validate`

Запустить полный набор CI-подобных проверок:
```bash
make ci 2>&1 | tail -30
```

Или поэтапно:
```bash
make lint && make test && make security
```
