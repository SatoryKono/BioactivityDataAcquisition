# GitHub Settings Audit Report

## 1. Rulesets

Found 1 rulesets.

| Ruleset Name | ID | Enforcement | Status Checks |
|---|---|---|---|
| main | 13643213 | disabled | [{"context": "pr-gate-complete"}] |

## 2. Environments

Found 5 environments.

| Environment Name | Protection Rules |
|---|---|
| copilot | required_reviewers, branch_policy |
| ghcr-publish | required_reviewers, branch_policy |
| observability-render-host | required_reviewers, branch_policy |
| pypi | required_reviewers, branch_policy |
| testpypi | required_reviewers, branch_policy |

## 3. Branch Protection (main)

No classic branch protection found for main (likely managed via rulesets).

## 4. Secrets Inventory

### Environment Secrets

- **pypi**: 0 secrets
- **testpypi**: 0 secrets

### Repository Secrets

Found 1 repository secrets.
- `MUSE_API_KEY`

## 5. Расхождения с политикой (Discrepancies)

- Фактический required context в ruleset: `pr-gate-complete`, тогда как политика или другие зависимости могли ожидать `ci/circleci: pr-gate-complete` (согласно контексту из #12581).
- Ruleset `main` находится в состоянии `disabled`.
- Секреты окружений `pypi` и `testpypi` отсутствуют (0 секретов), что может мешать публикации.
