# /dependency-audit

Аудит зависимостей BioETL: CVE, обновления, совместимость, лицензии.

## Использование

```
/dependency-audit [action]
```

**Действия:**
- `check` — полный аудит зависимостей (по умолчанию)
- `security` — только проверка CVE/уязвимостей
- `outdated` — показать устаревшие пакеты
- `licenses` — проверка лицензий
- `tree` — дерево зависимостей

**Примеры:**
```
/dependency-audit                           # полный аудит
/dependency-audit security                  # только CVE
/dependency-audit outdated                  # устаревшие пакеты
/dependency-audit licenses                  # лицензии
/dependency-audit tree                      # дерево зависимостей
```

---

## Инструкции для Claude

### Действие: `check` (по умолчанию)

Выполнить все проверки последовательно и сформировать сводный отчёт.

### Действие: `security`

**Шаг 1: pip-audit**
```bash
uv run pip-audit --skip-editable 2>&1
```

**Шаг 2: osv-scanner (если установлен)**
```bash
osv-scanner scan . 2>&1 || echo "osv-scanner not installed"
```

**Шаг 3: bandit (code security)**
```bash
uv run bandit -r src/bioetl/ -c pyproject.toml 2>&1 | tail -20
```

**Шаг 4: detect-secrets**
```bash
uv run python -m pytest tests/architecture/test_antipatterns.py::test_no_hardcoded_secrets -v --tb=short 2>&1
```

**Отчёт:**
```
Security Audit
==============
Date: YYYY-MM-DD

| Tool | Findings | Critical | High | Medium | Low |
|------|:--------:|:--------:|:----:|:------:|:---:|
| pip-audit | N | N | N | N | N |
| osv-scanner | N | N | N | N | N |
| bandit | N | N | N | N | N |
| detect-secrets | N | — | — | — | — |

Details:
<перечисление найденных уязвимостей>
```

### Действие: `outdated`

**Шаг 1:** Проверить устаревшие пакеты:
```bash
uv pip list --outdated 2>&1 || pip list --outdated 2>&1
```

**Шаг 2:** Прочитать текущие pinned versions из `pyproject.toml`:
```bash
grep -A1 "dependencies" pyproject.toml | head -30
```

**Шаг 3:** Сформировать таблицу:
```
| Package | Current | Latest | Pinned Range | Risk |
|---------|---------|--------|-------------|------|
| httpx | 0.27.0 | 0.28.1 | >=0.27 | LOW |
| polars | 1.5.0 | 1.8.2 | >=1.0 | MEDIUM |
```

Risk: LOW (patch), MEDIUM (minor), HIGH (major), BREAKING (incompatible)

### Действие: `licenses`

```bash
uv run pip-licenses --format=markdown --with-urls 2>&1 | head -50
```

Проверить: нет GPL/AGPL зависимостей (если проект MIT/Apache).

### Действие: `tree`

```bash
uv pip tree 2>&1 | head -60 || pip install pipdeptree && pipdeptree 2>&1 | head -60
```

Показать: конфликты версий, circular dependencies.

### Сводный отчёт (для `check`)

```
Dependency Audit Report
=======================
Date: YYYY-MM-DD
Total dependencies: N (direct) + M (transitive)

| Check | Status | Details |
|-------|:------:|---------|
| CVE/Vulnerabilities | ✅/❌ | N critical, M high |
| Outdated packages | ✅/⚠️ | N major, M minor behind |
| License compliance | ✅/❌ | All MIT/Apache/BSD |
| Version conflicts | ✅/❌ | N conflicts |
| Pinning quality | ✅/⚠️ | N unpinned |

Recommendations:
1. <action item>
2. <action item>
```
