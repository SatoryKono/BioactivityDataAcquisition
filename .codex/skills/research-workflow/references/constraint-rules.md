# Constraint Rules

The constrained spec workflow is intentionally strict.

## Non-Negotiable Rules

1. No PRD or architecture section may exist without at least one `DEC-*` citation.
1. Requirements must cite the decision that authorizes them.
1. Architecture choices must cite the decision that justifies them.
1. Relevant risks must be cross-referenced with `RISK-*` IDs.
1. Evidence should be cited with `EV-*` IDs when a claim depends on research, measurement, or user findings.

## Allowed Citation Patterns

- Section heading: `## 2. MVP Scope (DEC-scope-web-only)`
- Inline statement: `Web-only access for MVP. (DEC-scope-web-only)`
- Evidence plus decision: `Users drop off at invitation stage. (EV-users-onboarding-dropoff, DEC-ux-simplified-onboarding)`

## Forbidden Content

- Feature descriptions without a supporting decision.
- Architecture sections that introduce new technical commitments without a decision.
- Requirements that contradict accepted decisions.
- Vague filler text with no traceable rationale.

## Validation Checklist

- Every heading includes one or more `DEC-*` IDs.
- Every concrete requirement has a traceable citation.
- Every technical choice cites a decision.
- Risk notes are included where the choice introduces known downside.
- No section expands scope beyond the decision ledger.
