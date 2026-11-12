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

<!-- policy-anchor:deployment-provider --> `deployment.provider` is `github_actions`. <!-- policy-anchor:ruleset-enforcement-mode --> Ruleset `13643213` is `enforcement: active` (GET 2026-11-06); rulesets `15730586` and `24517966` were deleted on 2026-11-02 (settings-audit phase 0). <!-- policy-anchor:stored-ruleset-contexts --> The active rule requires `pr-gate-complete` (GET 2026-11-06); the rule binds this context to GitHub Actions App 15368 (integration_id=15368). <!-- policy-anchor:target-gha-context --> Target `pr-gate-complete` is the context stored on ruleset `13643213` since 2026-11-02. <!-- policy-anchor:enforcement-verified-date --> Catalog `enforcement_verified_date` `2026-10-09` is not proof of active merge protection. <!-- policy-anchor:merge-block --> A successful `pr-gate-complete` does not by itself block merge; the active server rule requires it. An offline catalog match does not confirm live server rulesets. Positive/negative merge acceptance was not run in this audit.

The coordinator aggregate is `pr-gate-complete`. While ruleset enforcement is
disabled, that job is not live merge protection. Leaf jobs below are aggregator
inputs, not independent required contexts.

| Check | Что проверяет |
|-------|--------------|
| `pr-gate-complete` | fail-closed aggregator; not live merge protection |
| `checks-complete` | lint + C901 + arch tests (leaf) |
| `coverage-verify` | 85% coverage (leaf) |
| `type-check` | mypy strict (leaf) |
| `schema-governance-status` | schema parity (leaf) |
| `detect-secrets` | no credentials (leaf) |
| `commit-lint` | Conventional Commits (leaf) |

## CI Troubleshooting

**Падает `pr-gate-complete`?**
```bash
# Смотрим в порядке:
1. coordinator classification / owner N/A evidence
2. lint / c901-governance / arch-tests (checks-complete leaf)
3. coverage-verify, type-check, schema, secrets, root-hygiene
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
git push origin HEAD
# After the release PR merges to main, push the annotated tag only:
git push origin v6.2.0
gh release create v6.2.0 --title "v6.2.0" --notes-file CHANGELOG.md
```

## Worktrees (для сложных задач)

Bootstrap and path/consent rules:
[Governed local worktrees](../../.github/CONTRIBUTING.md#governed-local-worktrees).

```bash
# Создать isolated worktree
# Only after per-task approval for creating the tracked .env.example:
python D:/github/BioactivityDataAcquisition/.git/hooks/bioetl-create-worktree.py feat-name --env-example-approved
cd D:/github/BioactivityDataAcquisition-worktrees/feat-name

# После завершения
# Only for a clean unused tree, with separate approval to delete any .env*:
cd D:/github/BioactivityDataAcquisition
git worktree remove D:/github/BioactivityDataAcquisition-worktrees/feat-name
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

