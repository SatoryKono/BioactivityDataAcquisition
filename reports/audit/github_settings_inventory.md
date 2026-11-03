# GitHub Settings Inventory

This report contains a read-only inventory of GitHub settings for the BioactivityDataAcquisition repository.
It documents actual settings for rulesets, environments, branch protection, and secrets to identify discrepancies with policy.

## 1. Rulesets

| Ruleset Name | Enforcement Status | Target Branches | Required Contexts |
| :--- | :--- | :--- | :--- |
| `main` | Disabled | `main` | `ci/circleci: pr-gate-complete` (Dead) |
| `release-tags-v-protection` | Disabled | `tag` | N/A |

## 2. Environments

| Environment Name | Protection Rules | Required Reviewers |
| :--- | :--- | :--- |
| `pypi` | None | None |
| `testpypi` | None | None |

## 3. Branch Protection

| Branch | Status | Required Approving Reviews | Required Status Checks |
| :--- | :--- | :--- | :--- |
| `main` | Unverified | 1 | `ci/circleci: pr-gate-complete` (Dead) |

## 4. Secrets Inventory

| Environment / Scope | Secret Names |
| :--- | :--- |
| Repository | (Not Verified) |
| `pypi` | (Not Verified) |
| `testpypi` | (Not Verified) |

## 5. Расхождения с политикой (Discrepancies)

1. **Dead Required Context:** The required context for branch protection is `ci/circleci: pr-gate-complete`, which is a dead context. The real context should be `pr-gate-complete`.
2. **Disabled Ruleset:** The rulesets are currently disabled, leaving the `main` branch and tags without enforced protection.
3. **Environment Protection:** The `pypi` and `testpypi` environments lack explicit protection rules and required reviewers.
