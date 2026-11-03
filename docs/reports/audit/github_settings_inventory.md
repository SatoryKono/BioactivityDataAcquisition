# GitHub Settings Audit Report

## 1. Rulesets

Found 1 repository ruleset.

| Ruleset Name | ID | Enforcement | Status Checks |
|---|---|---|---|
| main | 13643213 | disabled | `pr-gate-complete` |

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

No classic branch protection was found for `main`. Repository ruleset `13643213` is disabled. Parent rulesets were not assessed, so this report makes no claim about organization-level protection.

## 4. Secrets Inventory

### Environment Secrets

The available audit record reports zero secrets for `pypi` and `testpypi`. Secret counts for `copilot`, `ghcr-publish`, and `observability-render-host` were not available in that record. The connected GitHub API does not expose environment-secret endpoints, so those three counts could not be independently verified for this update.

| Environment | Secret count | Scope |
|---|---:|---|
| copilot | Not verified | Not present in the available audit record |
| ghcr-publish | Not verified | Not present in the available audit record |
| observability-render-host | Not verified | Not present in the available audit record |
| pypi | 0 | Available audit record |
| testpypi | 0 | Available audit record |

The `publish-testpypi` and `publish-pypi` workflows use OIDC trusted publishing (`id-token: write` and `pypa/gh-action-pypi-publish`), so the absence of environment secrets in those two environments is not evidence of a publishing problem.

### Repository Secrets

Found 1 repository secret.
- `MUSE_API_KEY`

## 5. Расхождения с политикой (Discrepancies)

- Ruleset `13643213` is disabled, so its stored `pr-gate-complete` context is not enforced by that ruleset. The configured context matches `deployment.required_context`; `ci/circleci: pr-gate-complete` is the previous context, not a current discrepancy.
- Secret counts for three environments remain unverified; this report does not infer a policy discrepancy from missing inventory data.
