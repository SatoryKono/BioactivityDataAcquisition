# Сбор evidence завершён: domain-observability-di-remediation

Review note (2026-03-27): included in the repo-wide evidence-pack sweep; see `docs/reports/evidence/project-evidence-rebaseline/06-status/EVIDENCE-PACK-REVIEW-2026-03-27.md` for wave status, retained-vs-reopened interpretation, and current review scope.

**Создано объектов evidence:** 7
**Gate Статус:** PASSED

## Сводка evidence

| ID                                                                                        | Claim Summary                                                                    | Confidence |
| ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ---------- |
| EV-domain-observability-di-remediation-staged-enforcement-imports-structlog               | `staged_enforcement.py` imports and uses `structlog` inside domain.              | 0.98       |
| EV-domain-observability-di-remediation-policy-forbids-domain-io-and-hardcoded-di          | Project policy forbids domain I/O, hard-coded DI, and non-composition factories. | 0.99       |
| EV-domain-observability-di-remediation-composite-validation-hardcodes-collaborators       | `CompositeValidationService.__init__` hard-codes its collaborators.              | 0.97       |
| EV-domain-observability-di-remediation-composite-validation-recreates-governance-per-call | `validate_composite()` creates a new governance service per request.             | 0.96       |
| EV-domain-observability-di-remediation-composite-validation-domain-factory-leaks-assembly | Domain exports a factory helper for `CompositeValidationService`.                | 0.95       |
| EV-domain-observability-di-remediation-staged-enforcement-has-no-external-callers         | `staged_enforcement.py` has no detected external callers.                        | 0.92       |
| EV-domain-observability-di-remediation-composite-validation-usage-is-test-heavy           | Composite validation usage is concentrated in tests and docs.                    | 0.91       |

## Ключевые выводы

- The policy violation in `staged_enforcement.py` is direct and can be removed narrowly.
- `CompositeValidationService` has both constructor-level and method-level DI violations.
- The right convenience seam is composition-owned assembly, not a domain factory.
- This refactor can stay focused because the affected surfaces have low runtime blast radius in the current repo.
