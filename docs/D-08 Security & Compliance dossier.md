______________________________________________________________________

Version: 0.3.0
Status: draft
Class: repo-only
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last synchronized: '2026-05-08'

______________________________________________________________________

# D-08 Security and Compliance Dossier (Draft Sync Note)

## Назначение

D-08 фиксирует рамку будущего consolidated security/compliance handbook.
Сейчас документ является non-normative draft и не заменяет опубликованные security policy, runbooks и governance rules.

## Канонические источники

- `.github/SECURITY.md`
- `docs/00-project/RULES.md`
- `docs/05-operations/runbooks/incident-response.md`
- `docs/03-guides/troubleshooting.md`
- `.github/workflows/security.yml`
- `tests/security/test_security.py`
- `.gitleaks.toml`

## Текущий validated security contour (summary)

- Security policy и threat model уже опубликованы в `.github/SECURITY.md`.
- Security CI checks уже выделены в отдельный workflow `security.yml` (`detect-secrets`, `pip-audit`).
- Secret leakage guards и VCR/source scanning уже закреплены в `tests/security/test_security.py` и `.gitleaks.toml`.
- Incident/security triage для Local-Only runtime уже покрыт runbook-секциями `incident-response.md` и operational troubleshooting guidance.

## Текущие зоны дрейфа

- Риск возникает, когда draft-документы дублируют конкретные контрольные таблицы (SLO, IAM, PII/algorithm details) без синхронизации с кодом/policy.
- Security/compliance утверждения должны опираться на репозиторные source-of-truth документы и реально исполняемые CI checks.
- D-08 не должен формировать альтернативный нормативный контур рядом с `.github/SECURITY.md` и `RULES.md`.

## План синхронизации D-08

1. Оставлять в D-08 только карту canonical security/compliance surfaces.
1. Не дублировать исполняемые security checks; ссылаться на workflow и тестовые файлы.
1. Любые изменения policy сначала вносить в `.github/SECURITY.md` и governance/runbook docs, затем отражать в D-08 как summary.
1. При появлении нового compliance gate сначала закреплять его в CI и published docs, и только после этого добавлять в D-08.

## Критерии промоушена в future published handbook

1. Единый security/compliance glossary согласован между policy, rules, runbooks и CI checks.
1. D-08 не содержит дублируемых нормативных таблиц и не конфликтует с `.github/SECURITY.md`.
1. Все утверждения в D-08 трассируются к published source и проверяемым controls в CI/tests.
