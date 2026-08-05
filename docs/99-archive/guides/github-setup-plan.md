______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
  - BioETL Team
Last verified: '2026-06-02'

______________________________________________________________________

> **ARCHIVED (docs audit cycle 2, 2026-08-05):** historical working draft. Not an active SSOT. See published dashboard/GitHub guides under `docs/03-guides/`.

# План настройки работы с GitHub репозиторием BioETL

*Комплексное руководство по настройке и оптимизации GitHub workflow для проекта BioETL.*

______________________________________________________________________

## Обзор

Этот документ описывает пошаговый план настройки полноценной работы с GitHub репозиторием для проекта BioETL, включая локальную конфигурацию, CI/CD, систему review, безопасность и автоматизацию.

## Текущее состояние

Проект уже имеет развитую GitHub инфраструктуру:
- ✅ 37 GitHub Actions workflows (see [canonical inventory](../04-reference/github-actions-workflows.md))
- ✅ CODEOWNERS и branch protection policy
- ✅ Dependabot для автоматических обновлений
- ✅ Шаблоны для issues и pull requests
- ✅ Комплексный security scanning
- ✅ Документация по локальным workflows

## План настройки

### Этап 1: Локальная Git конфигурация (Приоритет: КРИТИЧЕСКИЙ)

#### 1.1 Базовая конфигурация Git

```bash
# Настройка идентификации
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Рекомендуемые настройки для проекта
git config pull.ff only                    # Fast-forward only для main
git config push.default simple             # Безопасный push
git config fetch.prune true                # Автоматическая очистка
git config rerere.enabled true             # Переиспользование разрешений конфликтов
git config rebase.autosquash true          # Автосквош в rebase
git config merge.conflictstyle zdiff3      # Улучшенный формат конфликтов
git config branch.autoSetupMerge true      # Автоматический tracking
git config branch.autoSetupRebase always   # Rebase по умолчанию
```

#### 1.2 Настройка remote репозитория

```bash
# Проверка текущей конфигурации
git remote -v
git config --get remote.origin.url

# Если нужно, установить правильный origin
# (предполагается, что origin уже настроен, иначе):
# git remote add origin https://github.com/SatoryKono/BioactivityDataAcquisition.git
```

#### 1.3 GitHub CLI установка и настройка

```powershell
# Windows (через winget)
winget install GitHub.cli

# После установки - авторизация
gh auth login
# Выбрать: GitHub.com > HTTPS > Login with a web browser

# Проверка настройки
gh auth status
gh repo view --json nameWithOwner
```

#### 1.4 Git hooks (опционально, для автоматизации)

```bash
# Pre-commit hook для линтинга (создать .git/hooks/pre-commit)
cat > .git/hooks/pre-commit << 'HOOK'
#!/bin/bash
make lint || {
  echo "Lint check failed. Please fix errors before committing."
  exit 1
}
HOOK

chmod +x .git/hooks/pre-commit
```

___

### Этап 2: Настройка рабочего окружения (Приоритет: ВЫСОКИЙ)

#### 2.1 Установка зависимостей

```bash
# Установка uv (рекомендуется)
# Windows PowerShell:
Invoke-WebRequest https://astral.sh/uv/install.ps1 | Invoke-Expression

# Установка зависимостей проекта
uv sync --extra dev --extra tests --extra tracing

# Проверка окружения
uv run python --version
uv run pytest --version
uv run mypy --version
```

#### 2.2 Конфигурация для Windows + WSL (если используется)

```powershell
# Windows: использовать отдельный venv
.\scripts\engineering\dev\setup_env_windows.ps1

# Проверка
.\scripts\engineering\dev\run_pytest.ps1 tests\smoke\ -v
.\scripts\engineering\dev\run_mypy.ps1
```

```bash
# WSL: использовать отдельный venv
bash scripts/engineering/dev/setup_env_wsl.sh

# Проверка
bash scripts/engineering/dev/run_pytest.sh tests/smoke/ -v
bash scripts/engineering/dev/run_mypy.sh
```

#### 2.3 Настройка IDE (рекомендации для PyCharm/VS Code)

**PyCharm:**
- Settings → Tools → Python Integrated Tools → Default test runner: `pytest`
- Settings → Tools → Python Integrated Tools → Docstring format: `reStructuredText`
- Settings → Editor → Code Style → Python: Follow PEP 8

**VS Code:**
```json
// .vscode/settings.json
{
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.analysis.typeCheckingMode": "strict"
}
```

___

### Этап 3: Понимание и настройка CI/CD (Приоритет: ВЫСОКИЙ)

#### 3.1 Обязательные CI checks для PR

| Check Name | Workflow | Описание | При провале |
|------------|----------|----------|-------------|
| `checks-complete` | `import-linter.yml` | Lint + C901 + arch tests + import boundaries | Блокировка merge |
| `coverage-verify` | `tests.yml` | Комбинированное покрытие ≥85% | Блокировка merge |
| `type-check` | `type-checking.yml` | mypy strict mode | Блокировка merge |
| `schema-governance-status` | `schema-governance.yml` | Schema parity + contracts | Блокировка merge |
| `detect-secrets` | `security.yml` | Поиск утечек credentials | Блокировка merge |
| `commit-lint` | `commit-lint.yml` | Conventional Commits | Блокировка merge |
| `root-hygiene` | `root-hygiene.yml` | Чистота корня репозитория | Блокировка merge |

#### 3.2 Локальная верификация перед push

**Минимальный набор проверок:**
```bash
# 1. Lint check
make lint

# 2. Tests (быстрые)
make test

# 3. Type checking
uv run python -m mypy --strict src/bioetl/

# 4. Architecture tests
uv run pytest tests/architecture/ -v
```

**Полный набор (рекомендуется перед финальным PR):**
```bash
# Все тесты с coverage
make test-coverage

# Quality metrics
make qa-debt

# Security scans
make security-check

# Docs build
make docs
```

#### 3.3 Понимание тестовых lanes в CI

```
tests.yml workflow structure:
├── dependency-preflight       # Первая линия защиты: uv lock drift
├── smoke-check               # VCR + imports + версии
├── governance-preflight      # Quality exemptions + scripts + Neo4j
├── config-schema-preflight   # Config validation + schema checks
├── control-plane-e2e         # E2E smoke для completeness
├── contract-confidence       # Offline contract surfaces
├── track-d-gates            # Runtime linkage fail-fast
├── dq-consistency-gate      # DQ validation
├── quality-metrics-gate     # Debt scores + observability
├── test-fast                # Quick feedback loop (unit, no slow)
├── test-matrix              # Parallel shards (6 groups × Py 3.12)
├── memory-tests             # Neo4j memory audit
├── performance-budgets      # Hotspot budget gates
├── coverage-verify          # Final 85% threshold + serial tests
└── duration-telemetry       # Slow test summaries
```

**Порядок триажа при падении CI:**
1. Если много jobs падают быстро → смотрим `dependency-preflight` лог первым
2. Если падает `checks-complete` → смотрим в порядке: `lint` → `c901-governance` → `arch-tests`
3. Если падает `coverage-verify` → смотрим matrix shards + serial pass
4. Если падает `schema-governance-status` → смотрим contract exports + parity

#### 3.4 Настройка GitHub Secrets (для maintainers)

Необходимые secrets для полноценной работы CI:
```
Repository secrets (Settings → Secrets and variables → Actions):

# Observability (опционально)
BIOETL_OBSERVABILITY_PROMETHEUS_URL
BIOETL_OBSERVABILITY_PROMETHEUS_TOKEN

# Release (для автопубликации в PyPI)
PYPI_API_TOKEN
TEST_PYPI_API_TOKEN

# Container Registry (для docker.yml)
GHCR_TOKEN  # или использовать GITHUB_TOKEN (автоматический)
```

___

### Этап 4: Branch Strategy и Workflow (Приоритет: ВЫСОКИЙ)

#### 4.1 Branch naming convention

```
<type>/<short-description>

Types:
  feat/        - новый функционал
  fix/         - исправление бага
  refactor/    - refactoring без изменения поведения
  docs/        - изменения документации
  test/        - добавление/изменение тестов
  chore/       - maintenance tasks
  ci/          - изменения CI/CD

Examples:
  feat/pubchem_compound_pipeline
  fix/chembl_rate_limit_429
  refactor/storage_clear_contract
  docs/update_github_workflow
  ci/add_performance_gates
```

#### 4.2 Feature development workflow

```bash
# 1. Создание feature branch
git switch main
git fetch --prune origin
git pull --ff-only
git switch -c feat/short-description

# 2. Работа в branch
# ... делаем изменения ...
git add .
git commit -m "feat(scope): description of changes"

# 3. Регулярная синхронизация с main
git fetch --prune origin
git rebase origin/main

# 4. Push и создание PR
git push -u origin HEAD
gh pr create --title "feat(scope): Short PR title" --body "Description"

# 5. После merge - cleanup
git switch main
git pull --ff-only
git branch -d feat/short-description
```

#### 4.3 Использование worktrees (рекомендуется для сложных задач)

```bash
# Создание isolated worktree
git fetch --prune origin
git worktree add .worktrees/feat-short-description -b feat/short-description origin/main
cd .worktrees/feat-short-description

# Работа в worktree
# ... changes ...

# После завершения
cd ../..
git worktree remove .worktrees/feat-short-description
```

#### 4.4 Commit message format (Conventional Commits)

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Types:**
- `feat` — новый функционал (MINOR bump)
- `fix` — исправление бага (PATCH bump)
- `refactor` — рефакторинг без изменения API
- `docs` — документация
- `test` — изменения тестов
- `chore` — maintenance
- `ci` — изменения CI/CD

**Breaking changes:**
```
feat(storage)!: migrate to Delta Lake 3.0

BREAKING CHANGE: Old checkpoint format no longer supported.
Migration guide: docs/migration/delta-lake-3.md
```

___

### Этап 5: Pull Request Workflow (Приоритет: ВЫСОКИЙ)

#### 5.1 Создание качественного PR

```bash
# Перед созданием PR
make lint && make test

# Создание PR через GitHub CLI
gh pr create \
  --title "feat(chembl): Add compound activity pipeline" \
  --body "
## Summary
Adds pipeline for fetching ChEMBL compound activities.

## Changes
- New adapter: ChEMBLActivityAdapter
- Silver schema: chembl_compound_activity_v1
- Integration tests with VCR cassettes
- Documentation update

## Type
- [x] New feature

## Affected layers
- [x] Infrastructure (adapter)
- [x] Config (pipeline config)

## Test plan
- [x] Unit tests pass
- [x] Architecture tests pass
- [x] Type check passes
- [x] Manual verification: ran against ChEMBL test instance
"

# Или создать draft PR для раннего feedback
gh pr create --draft
```

#### 5.2 Мониторинг CI checks

```bash
# Проверка статуса PR
gh pr status

# Просмотр последних workflow runs
gh run list --limit 10

# Проверка конкретного workflow
gh run view <run-id> --log

# Повторный запуск при flaky tests
gh run rerun <run-id>
```

#### 5.3 Review процесс

**Для автора PR:**
- Убедитесь, что все CI checks зелёные
- Ответьте на все review comments
- После внесения изменений по review, сделайте push (не force-push)
- Используйте "Request re-review" после исправлений

**Для reviewer:**
- Проверьте PR checklist в шаблоне
- Проверьте архитектурные constraints (см. `.github/CONTRIBUTING.md`)
- Используйте GitHub suggestions для мелких правок
- Используйте "Request changes" если нужны обязательные исправления

#### 5.4 После approval

```bash
# Squash merge (рекомендуется для feature branches)
gh pr merge --squash --delete-branch

# Rebase merge (для чистых linear commits)
gh pr merge --rebase --delete-branch

# Merge commit (редко используется)
gh pr merge --merge --delete-branch
```

___

### Этап 6: Code Review Policy (Приоритет: СРЕДНИЙ)

#### 6.1 CODEOWNERS конфигурация

Текущая конфигурация (`.github/CODEOWNERS`):
```
# Default owner
* @SatoryKono

# Architecture-critical paths
src/bioetl/domain/ @SatoryKono
src/bioetl/composition/ @SatoryKono
.github/workflows/ @SatoryKono
docs/00-project/ @SatoryKono
docs/02-architecture/ @SatoryKono
```

**Расширенная конфигурация (при росте команды):**
```
# Добавить в .github/CODEOWNERS:

# Provider adapters
src/bioetl/infrastructure/providers/ @team-integrations

# Data quality rules
configs/quality/ @team-data-quality

# Security configurations
.github/workflows/security.yml @security-team
configs/quality/scripts_inventory_manifest.json @security-team

# Documentation
docs/ @team-docs *.md @team-docs
```

#### 6.2 Review checklist (для reviewers)

**Обязательные проверки:**
- [ ] `make lint` passes локально
- [ ] `make test` passes локально
- [ ] Нет hardcoded secrets/credentials
- [ ] Architecture tests pass
- [ ] Документация обновлена (если поведение изменилось)
- [ ] Conventional Commits формат
- [ ] Нет import boundary violations

**Архитектурные проверки:**
- [ ] Domain не импортирует application/infrastructure
- [ ] Application не импортирует infrastructure
- [ ] Dependency injection используется корректно
- [ ] Нет I/O операций в domain layer
- [ ] Нет `print()`, только structured logging

**Security проверки:**
- [ ] Нет `.env` файлов в commits
- [ ] VCR cassettes sanitized (нет secrets в записях)
- [ ] External input validated
- [ ] No SQL injection vectors

___

### Этап 7: Dependency Management (Приоритет: СРЕДНИЙ)

#### 7.1 Dependabot настройка (уже настроен)

Текущая конфигурация (`.github/dependabot.yml`):
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    labels: ["dependencies"]

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    labels: ["ci"]

  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
    labels: ["dependencies", "ci"]
```

#### 7.2 Работа с Dependabot PRs

**Еженедельный triage workflow:**
```bash
# Список открытых Dependabot PRs
gh pr list --label dependencies

# Для каждого PR:
# 1. Проверить CI status
gh pr checks <pr-number>

# 2. Если security patch (CRITICAL/HIGH):
#    - Приоритетный review
#    - Merge в тот же день

# 3. Если routine update:
#    - Проверить changelog
#    - Проверить breaking changes
#    - Merge в течение недели

# 4. Если major version bump:
#    - Тщательный review
#    - Локальное тестирование
#    - Migration plan
```

**Upgrade policy по приоритету:**
| CVE Severity | Action | SLA |
|-------------|--------|-----|
| CRITICAL | Immediate patch | 24 hours |
| HIGH | Priority patch | 72 hours |
| MEDIUM | Normal update | Next sprint |
| LOW/None | Routine update | Weekly triage |

#### 7.3 Добавление новых зависимостей

```bash
# Добавление runtime dependency
uv add httpx

# Добавление dev dependency
uv add --dev pytest-mock

# Обновление зависимостей
uv lock --upgrade

# Проверка уязвимостей
make security-check  # или напрямую: pip-audit
```

___

### Этап 8: Security и Compliance (Приоритет: КРИТИЧЕСКИЙ)

#### 8.1 Secret management

**Правила работы с секретами:**
```bash
# ✅ Правильно: Environment variables
export BIOETL_CHEMBL_API_KEY="your-key-here"

# ✅ Правильно: .env файл (в .gitignore)
echo "BIOETL_CHEMBL_API_KEY=your-key" >> .env

# ❌ Неправильно: hardcoded в коде
API_KEY = "sk-1234567890"  # НИКОГДА!

# ❌ Неправильно: в VCR cassettes без sanitization
# Используйте before_record hooks!
```

**Настройка VCR sanitization:**
```python
# В тестах
@pytest.fixture(scope="module")
def vcr_config():
    return {
        "before_record_response": sanitize_response,
        "filter_headers": ["authorization", "x-api-key"],
    }
```

#### 8.2 Security scanning workflows

**Автоматические проверки (в CI):**
```
.github/workflows/security.yml:
├── detect-secrets    # Credential leak detection
├── pip-audit        # Python dependency vulnerabilities
└── trivy            # Container image scanning (в docker.yml)
```

**Локальные проверки перед commit:**
```bash
# Поиск секретов в коде
detect-secrets scan

# Аудит зависимостей
pip-audit --strict

# Проверка .env файлов
git status | grep ".env"  # должно быть пусто!
```

#### 8.3 GitHub Actions security

**Supply chain security:**
- Все actions SHA-pinned (не используем tags)
- Проверка через `check_github_actions_runtime_policy.py`
- Minimal permissions по умолчанию

**Проверка SHA pins:**
```bash
uv run python scripts/engineering/repo/check_github_actions_runtime_policy.py
```

___

### Этап 9: Release Process (Приоритет: СРЕДНИЙ)

#### 9.1 Versioning (Semantic Versioning)

```
MAJOR.MINOR.PATCH

MAJOR: Breaking changes (API incompatibility)
MINOR: New features (backward compatible)
PATCH: Bug fixes (backward compatible)

Examples:
  5.0.0 → 6.0.0  (breaking change)
  6.0.0 → 6.1.0  (new feature)
  6.1.0 → 6.1.1  (bug fix)
```

#### 9.2 Release workflow

```bash
# 1. Обновить версию
# Редактировать pyproject.toml: version = "6.2.0"

# 2. Обновить CHANGELOG.md
# Добавить секцию для новой версии с notable changes

# 3. Commit и tag
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): bump version to 6.2.0"
git tag -a v6.2.0 -m "Release v6.2.0"
git push origin main --tags

# 4. Создать GitHub Release
gh release create v6.2.0 \
  --title "v6.2.0" \
  --notes-file CHANGELOG.md#6.2.0 \
  --verify-tag

# 5. CI автоматически:
#    - Соберёт wheel и sdist
#    - Протестирует на Python 3.11, 3.12, 3.13
#    - Опубликует в TestPyPI
#    - Опубликует в PyPI (если release, не draft)
#    - Прикрепит artifacts к release
```

#### 9.3 Hotfix workflow

```bash
# 1. Создать hotfix branch от production tag
git checkout -b fix/critical-bug v6.1.0

# 2. Исправить bug
# ... changes ...
git commit -m "fix(chembl): handle null compound names"

# 3. Bump patch version
# pyproject.toml: version = "6.1.1"
git commit -m "chore(release): bump version to 6.1.1"

# 4. Tag и merge обратно в main
git tag -a v6.1.1 -m "Hotfix v6.1.1"
git push origin fix/critical-bug --tags
gh pr create --base main --title "Hotfix v6.1.1"

# 5. После merge - создать release
gh release create v6.1.1 --title "v6.1.1 (Hotfix)" --notes "..."
```

___

### Этап 10: Issue Management (Приоритет: СРЕДНИЙ)

#### 10.1 Issue templates

**Bug Report** (`.github/ISSUE_TEMPLATE/bug_report.yml`):
```yaml
name: Bug Report
title: "[BUG]: "
labels: ["bug"]
body:
  - type: textarea
    id: description
    attributes:
      label: Bug Description
      description: Clear description of the bug
    validations:
      required: true
  - type: textarea
    id: reproduction
    attributes:
      label: Steps to Reproduce
      placeholder: |
        1. Run command: ...
        2. See error: ...
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected Behaviour
  - type: input
    id: version
    attributes:
      label: BioETL Version
      placeholder: "6.1.3"
```

**Feature Request** (`.github/ISSUE_TEMPLATE/feature_request.yml`):
```yaml
name: Feature Request
title: "[FEATURE]: "
labels: ["enhancement"]
body:
  - type: textarea
    id: problem
    attributes:
      label: Problem Statement
      description: What problem does this feature solve?
  - type: textarea
    id: solution
    attributes:
      label: Proposed Solution
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives Considered
```

#### 10.2 Issue workflow

```bash
# Создание issue
gh issue create \
  --title "Add support for PDB protein structures" \
  --body "Feature request: integrate PDB API for protein 3D structure data" \
  --label enhancement

# Список issues
gh issue list --label bug
gh issue list --assignee @me

# Назначение issue
gh issue edit <issue-number> --add-assignee @username

# Закрытие issue
gh issue close <issue-number> --comment "Fixed in #123"
```

#### 10.3 Issue labels (рекомендуемая схема)

```
Type:
  - bug          # Что-то работает неправильно
  - enhancement  # Новый функционал
  - refactor     # Code improvement без изменения API

Priority:
  - critical     # Blocking, security, data loss
  - high         # Important, affects many users
  - medium       # Normal priority
  - low          # Nice to have

Component:
  - domain       # Domain layer
  - application  # Application layer
  - infrastructure # Infrastructure/adapters
  - ci           # CI/CD
  - docs         # Documentation

Status:
  - triage       # Needs initial review
  - accepted     # Ready for implementation
  - in-progress  # Being worked on
  - blocked      # Waiting on something
  - wontfix      # Closed without fix
```

___

### Этап 11: Monitoring и Analytics (Приоритет: НИЗКИЙ)

#### 11.1 GitHub Insights

**Регулярный мониторинг (еженедельно):**
```bash
# Недавние PRs
gh pr list --state all --limit 20

# Недавние issues
gh issue list --state all --limit 20

# Workflow runs за последнюю неделю
gh run list --limit 50 --json conclusion,name,event

# Failed runs
gh run list --status failure --limit 10
```

**Metrics to track:**
- PR merge time (target: < 2 days)
- CI success rate (target: > 95%)
- Test duration trends
- Coverage trends (via `coverage-report` artifacts)

#### 11.2 Grafana dashboards (если настроена observability)

```bash
# Доступ к метрикам
# http://localhost:3000 (локально)
# Dashboards: grafana/dashboards/bioetl_*.json

# Prometheus metrics endpoint
# http://localhost:8000/metrics (приложение)
```

#### 11.3 Quality metrics tracking

```bash
# Weekly quality debt report
make qa-debt

# Просмотр trends в artifacts:
# .github/workflows/quality-debt-weekly.yml
# Artifacts: ci-quality-metrics, debt-scorecard
```

___

### Этап 12: Advanced Topics (Приоритет: НИЗКИЙ)

#### 12.1 GitHub Projects для планирования

```bash
# Создание project board
gh project create --title "BioETL Sprint 1" --body "Sprint planning"

# Добавление issues в project
gh project item-add <project-id> --url <issue-url>
```

#### 12.2 GitHub Discussions (для community)

```bash
# Включить Discussions в Settings → General → Features

# Категории:
# - Announcements (releases, important updates)
# - Q&A (questions from users)
# - Ideas (feature discussions)
# - Show and Tell (user contributions)
```

#### 12.3 GitHub Packages (для Docker images)

```yaml
# Уже настроено в .github/workflows/docker.yml
# Images публикуются в: ghcr.io/satorykono/bioetl

# Pull image:
docker pull ghcr.io/satorykono/bioetl:latest
```

___

## Checklist для быстрого старта

### Для нового участника команды

- [ ] Склонировать репозиторий
- [ ] Настроить Git config (pull.ff, push.default, etc.)
- [ ] Установить GitHub CLI и авторизоваться
- [ ] Установить `uv` и зависимости проекта
- [ ] Настроить IDE (PyCharm/VS Code)
- [ ] Прочитать `.github/CONTRIBUTING.md`
- [ ] Прочитать `docs/00-project/RULES.md`
- [ ] Запустить `make lint && make test` локально
- [ ] Создать test PR для понимания CI flow

### Для maintainer

- [ ] Настроить GitHub Secrets (если нужны)
- [ ] Проверить CODEOWNERS
- [ ] Настроить branch protection (если требуется)
- [ ] Настроить notifications (Settings → Notifications)
- [ ] Настроить project boards (если используются)
- [ ] Еженедельный triage Dependabot PRs
- [ ] Мониторинг CI success rate

### Регулярные задачи (еженедельно)

- [ ] Triage новых issues
- [ ] Review открытых PRs
- [ ] Проверить Dependabot PRs
- [ ] Проверить failed CI runs
- [ ] Обновить documentation при необходимости
- [ ] Мониторинг security alerts

___

## Приложения

### A. Полезные команды GitHub CLI

```bash
# Aliases для удобства (добавить в ~/.gitconfig)
[alias]
  pr-list = !gh pr list
  pr-view = !gh pr view
  pr-checks = !gh pr checks
  issue-list = !gh issue list
  run-list = !gh run list --limit 10
  run-watch = run watch

# Или создать gh aliases:
gh alias set prl 'pr list'
gh alias set prv 'pr view'
gh alias set prc 'pr checks'
```

### B. CI Troubleshooting Guide

**Если `checks-complete` fails:**
1. Открыть logs для `lint`
2. Если lint OK → открыть logs для `c901-governance`
3. Если c901 OK → открыть logs для `arch-tests`

**Если `coverage-verify` fails:**
1. Проверить matrix shards (test-matrix job)
2. Проверить serial pass
3. Скачать coverage-report artifact для деталей

**Если `dependency-preflight` fails:**
1. Скачать `dependency-preflight.log` artifact
2. Проверить `uv lock --check` вывод
3. Локально запустить `uv lock --upgrade` если needed

### C. Полезные ссылки

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub CLI Manual](https://cli.github.com/manual/)
- [Git Worktrees Guide](https://git-scm.com/docs/git-worktree)
- [Semantic Versioning](https://semver.org/)

___

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-02 | Initial comprehensive GitHub setup plan |

______________________________________________________________________

*См. также:*
- *[.github/CONTRIBUTING.md](../../.github/CONTRIBUTING.md)*
- *[docs/00-project/governance/05-github-policy.md](../00-project/governance/05-github-policy.md)*
- *[docs/03-guides/github-local-workflow.md](./github-local-workflow.md)*
- *[.github/SECURITY.md](../../.github/SECURITY.md)*
