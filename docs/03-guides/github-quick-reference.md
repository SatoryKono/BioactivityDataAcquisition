# GitHub Quick Reference для BioETL

*Краткая справка по основным командам и workflow для ежедневной работы.*

## Быстрый старт

```bash
# Первичная настройка
git config pull.ff only
git config push.default simple
git config fetch.prune true
git config rerere.enabled true
git config rebase.autosquash true
git config merge.conflictstyle zdiff3

# GitHub CLI
gh auth login
gh repo view --json nameWithOwner
```

## Ежедневные команды

### Создание feature branch

```bash
git switch main
git fetch --prune origin
git pull --ff-only
git switch -c feat/my-feature
```

### Проверка перед commit

```bash
make lint && make test
```

### Commit + Push + PR

```bash
git status
git add path/to/reviewed/file
git commit -m "feat(scope): description"
git push -u origin HEAD
gh pr create
```

Do not stage the entire working tree at once: that can include `.env`, machine-local files, and unrelated WIP.

### Мониторинг PR

```bash
gh pr status
gh pr checks <number>
gh run list --limit 10
```

## CI Checks - Критичные

| Check | Что проверяет |
|-------|--------------|
| `checks-complete` | lint + C901 + arch tests |
| `coverage-verify` | 85% coverage |
| `type-check` | mypy strict |
| `schema-governance-status` | schema parity |
| `detect-secrets` | no credentials |
| `commit-lint` | Conventional Commits |

## CI Troubleshooting

**Падает `checks-complete`?**
```bash
# Смотрим в порядке:
1. lint job logs
2. c901-governance logs
3. arch-tests logs
```

**Падает много jobs сразу?**
```bash
# Сначала проверяем dependency-preflight artifact:
# reports/ci/dependency-preflight.log
```

**Падает `coverage-verify`?**
```bash
# Локально проверяем coverage:
make test-coverage
uv run python -m coverage report --show-missing
```

## Branch Types

```
feat/         - новый функционал
fix/          - bug fix
refactor/     - рефакторинг
docs/         - документация
test/         - тесты
chore/        - maintenance
ci/           - CI/CD изменения
```

## Commit Format

```
<type>(<scope>): <description>

feat(chembl): add compound activity pipeline
fix(pubchem): handle rate limit 429
docs: update github workflow guide
```

## Release Process

```bash
# 1. Bump version в pyproject.toml
# 2. Update CHANGELOG.md
git commit -m "chore(release): bump version to 6.2.0"
git tag -a v6.2.0 -m "Release v6.2.0"
git push origin main --tags
gh release create v6.2.0 --title "v6.2.0" --notes-file CHANGELOG.md
```

## Worktrees (для сложных задач)

```bash
# Создать isolated worktree
git worktree add .worktrees/feat-name -b feat/name origin/main
cd .worktrees/feat-name

# После завершения
cd ../..
git worktree remove .worktrees/feat-name
```

## Dependabot PRs

```bash
# Еженедельный triage
gh pr list --label dependencies

# Приоритеты:
# CRITICAL CVE → merge в течение 24 часов
# HIGH CVE → merge в течение 72 часов
# Routine → merge в течение недели
```

## Security Checks

```bash
# Локальная проверка перед commit
detect-secrets scan
pip-audit --strict
git status | grep ".env"  # должно быть пусто!
```

## Полезные aliases

```bash
# ~/.gitconfig
[alias]
  co = checkout
  sw = switch
  st = status
  br = branch
  ci = commit
  pf = push --force-with-lease
  lg = log --oneline --graph --decorate
  
# gh aliases
gh alias set prl 'pr list'
gh alias set prv 'pr view'
gh alias set prc 'pr checks'
```

## Emergency Procedures

**Нужен hotfix в production:**
```bash
git checkout -b fix/critical-bug v6.1.0
# ... fix ...
git commit -m "fix(critical): description"
# Bump patch: version = "6.1.1"
git tag -a v6.1.1 -m "Hotfix v6.1.1"
git push origin fix/critical-bug --tags
gh pr create --base main
```

**Случайно закоммитили секрет:**
```bash
# 1. НЕ force-push (history в GitHub сохраняется)
# 2. Немедленно rotate секрет в provider
# 3. Создать новый commit без секрета
# 4. Обратиться к maintainer для полной очистки истории
```

## Links

- [Полный план настройки](./github-setup-plan.md)
- [GitHub Workflow Guide](./github-local-workflow.md)
- [Contributing Guide](../../.github/CONTRIBUTING.md)
- [GitHub Policy](../00-project/governance/05-github-policy.md)

