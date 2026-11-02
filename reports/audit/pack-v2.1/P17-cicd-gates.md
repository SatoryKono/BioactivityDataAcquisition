# P17. CI/CD, GitHub Actions, release и dependency/build gates

## A. Audit Manifest
- **Repo:** `https://github.com/SatoryKono/BioactivityDataAcquisition`
- **Branch:** `main`
- **Revision (pin commit):** `ddbb7a0ee687365258bc407110e38601c4c3b765`
- **Scope:** `.github/workflows/**`, `.github/actions/**`, build/package/tool configs, release automation
- **Date/Time:** 2026-11-02
- **Environment:** OS Ubuntu, Python 3.12/3.13, uv 0.11.26
- **Unverified items:** Настройки хостинга (branch protection, required checks, environments) отмечены как `NOT_VERIFIABLE` из-за отсутствия доступа к GitHub API.

## B. Scope/ownership и exclusions
- **In Scope:** CI gate correctness, transitive workflow behavior, release automation (`release.yml`), dependency governance.
- **Out of Scope (Excluded):** Live GitHub settings (доступа нет).

## C. Evidence Ledger
- `E1 NORMATIVE`: `RULES.md`, `ADR-045` и другие.
- `E2 STATIC`: `.github/workflows/release.yml`, `.github/workflows/tests.yml`, `pyproject.toml`
- `E3 EXECUTABLE`: Не применялось, только read-only чтение файлов.
- `E4 RUNTIME`: Отсутствует, так как нет доступа к истории запусков CI.

## D. Findings Register

### Finding 1
- **finding_id**: `pack-v2.1/P17-CICD-001`
- **root_cause_id**: `release-publish-removed`
- **owner_prompt**: `P17`
- **concern**: В файле `.github/workflows/release.yml` удален триггер `release` (см. комментарий "KEEP-DISABLED (#11182)"), оставлен только `workflow_dispatch`. При этом job `publish-pypi` все еще проверяет `if: github.event_name == 'release'`, что делает его недостижимым мертвым кодом.
- **severity**: `P1`
- **confidence**: `high`
- **status**: `CONFIRMED`
- **expected**: Если публикация через actions отключена, CI конфиг не должен содержать мертвого кода, ожидающего событие `release`. В качестве альтернативы, ручная публикация должна быть явно определена и достижима.
- **actual**: Условие в job `publish-pypi` (`github.event_name == 'release'`) никогда не выполнится, так как триггер удален.
- **evidence_ids**: `E2` (`.github/workflows/release.yml:214`)
- **attempted_disproof**: Проверено, может ли `workflow_dispatch` запустить его. Job `publish-testpypi` запускается при `workflow_dispatch` и `dry_run == false`. Однако `publish-pypi` явно требует `github.event_name == 'release'`.
- **exceptions_checked**: Исключения для мертвого кода CI отсутствуют.
- **impact**: Невозможно опубликовать пакет в PyPI с помощью этого workflow.
- **root_cause**: Неполное удаление логики публикации после #11182.
- **recommendation**: Удалить job `publish-pypi` или обновить условие для поддержки ручной публикации через `workflow_dispatch`.
- **scope / non-goals**: Только очистка CI файла.
- **acceptance criteria**: Условие публикации в PyPI достижимо или удалено.
- **verification command**: Изучение содержимого `release.yml`.
- **dependencies**: Нет.

### Finding 2
- **finding_id**: `pack-v2.1/P17-CICD-002`
- **root_cause_id**: `live-hosting-settings-unverified`
- **owner_prompt**: `P17`
- **concern**: Настройки branch protection и environments (например, `pypi`, `testpypi`) невозможно проверить статически.
- **severity**: `P3`
- **confidence**: `high`
- **status**: `NOT_VERIFIABLE`
- **expected**: Настройки хостинга соответствуют политике безопасности.
- **actual**: Невозможно проверить без доступа к API.
- **evidence_ids**: `E2`
- **attempted_disproof**: N/A
- **exceptions_checked**: N/A
- **impact**: Неизвестен статус защиты веток.
- **root_cause**: Отсутствие доступа к окружению.
- **recommendation**: Ручная проверка владельцем репозитория.
- **scope / non-goals**: N/A

## E. Quantitative Scorecard
- **Score:** 4
- **Justification:** Сильная реализация workflows (55 файлов), явное использование lock-файлов, матричное тестирование. Однако присутствует мертвый код в release pipeline, а также невозможно проверить live настройки. Доказательства: `E2`.

## F. Cross-cutting/root-cause clusters
- `release-publish-removed`
- `live-hosting-settings-unverified`

## G. Prioritized roadmap P0->P3
1. [P1] Исправить или удалить недостижимый job `publish-pypi` в `release.yml`.
2. [P3] Выполнить ручную проверку правил защиты веток (branch protections).

## H. Verification Matrix
- Transitive graph: Выполнено (статически)
- Triggers/Permissions: Выполнено (статически)
- Cache keys: Выполнено (статически)
- Secrets/OIDC: Выполнено (статически)
- Hosting settings: NOT_VERIFIABLE

## I. `NOT_VERIFIABLE` и missing evidence
- Конфигурация сред (GitHub Environments) и секретов (Secrets).
- Правила защиты веток (Branch protection rules).

## J. Self-check
- Unsupported claims: Нет.
- Stale evidence: Сверено с текущим HEAD.
- Exception handling: Проверено.
- Score/severity consistency: Согласовано.

## K. Verdict
В репозитории настроены обширные и надежные пайплайны CI/CD, используются явные закрепления версий, lock-файлы uv и комплексные матрицы тестирования. Главное замечание связано с мертвым кодом в рабочем процессе `release` из-за ранее удаленного триггера `release`. Проверка настроек хостинга не может быть выполнена из-за отсутствия доступа к GitHub API.

## Issue drafts

### Draft 1: release-publish-removed
**Title:** CI: Dead code in publish-pypi job of release.yml

**Body:**
```markdown
**Provenance block:**
- audit_id: pack-v2.1/P17
- audited SHA: ddbb7a0ee687365258bc407110e38601c4c3b765
- root_cause_id: release-publish-removed
- source finding IDs: pack-v2.1/P17-CICD-001
- final severity: P1
- final confidence: high
- final status: CONFIRMED

**Problem:**
The `release` trigger in `.github/workflows/release.yml` was removed (see `#11182`), leaving only `workflow_dispatch`. However, the `publish-pypi` job still strictly requires `if: github.event_name == 'release'`, making it completely unreachable dead code.

**Evidence:**
- `.github/workflows/release.yml:214` - `publish-pypi` job condition.

**Expected vs actual:**
- **Expected:** If the release trigger is removed, any dependent jobs should also be removed or updated to trigger under `workflow_dispatch`.
- **Actual:** The `publish-pypi` job requires an event that is no longer listed in the `on:` block.

**Impact:**
It is impossible to publish to PyPI using this workflow.

**Scope / non-goals:**
- Scope is limited to `.github/workflows/release.yml`.

**Architecture constraints:**
- None.

**Implementation outline:**
- Remove the `publish-pypi` job from `release.yml` OR update its condition to match manual publishing parameters.

**Acceptance criteria:**
- The CI configuration does not contain unreachable jobs for PyPI publication.

**Verification commands/tests:**
- Code review of `.github/workflows/release.yml`.

**Dependencies:**
- None.

**Rollback/risk:**
- Low risk; this removes dead code or fixes an existing unrunnable configuration.
```
