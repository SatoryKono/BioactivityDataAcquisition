______________________________________________________________________

Version: 1.0.0
Status: template
Class: internal
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-XXX: <Decision Title>

**Date:** <YYYY-MM-DD>
**Status:** \<Proposed|Accepted|Superseded|Rejected>
**Decision makers:** <role-or-team>
**Related:** <ADR-010>, <ADR-014>, <issue-or-pr>

## Context

- State the problem in one sentence.
- List constraints that MUST be honored.
- List assumptions that SHOULD remain explicit.
- Link source-of-truth artifacts that motivated the decision.

## Decision

- State the chosen option in one sentence.
- The implementation MUST describe the target behavior, not only intent.
- Architecture boundaries MUST remain compatible with the project import matrix.
- Deviations from current policy SHOULD be enumerated explicitly.
- Any temporary workaround MUST include an exit condition.

## Compliance

| Control        | Requirement                                                       | Status   | Evidence |
| -------------- | ----------------------------------------------------------------- | -------- | -------- |
| Classification | Document class MUST match publication intent                      | \`\<pass | fail     |
| Architecture   | Decision MUST align with relevant ADRs                            | \`\<pass | fail     |
| Requirements   | Normative statements MUST use RFC 2119 keywords where binding     | \`\<pass | fail     |
| Runtime        | Decision MUST state ADR-010 impact if runtime behavior changes    | \`\<pass | fail     |
| Contracts      | Contract impact SHOULD be linked when schema/API behavior changes | \`\<pass | fail     |

## Consequences

### Positive

- `<positive consequence>`
- `<positive consequence>`

### Negative

- `<negative consequence>`
- `<negative consequence>`

## Rollout

- Preconditions MUST be listed before implementation starts.
- Migration steps SHOULD be ordered and testable.
- Backward-compatibility window MUST be stated for breaking changes.
- Ownership MUST be assigned for each rollout phase.

## Rollback

- Rollback trigger MUST be explicit.
- Rollback action MUST return the system to a known-good state.
- Data or contract rollback SHOULD include validation checkpoints.

## Verification

- List the checks that MUST pass before the ADR is considered implemented.
- Include tests, docs updates, contract checks, and operational validation as applicable.

## Alternatives Considered

### <Alternative A>

- Why it was considered.
- Why it was rejected.

### <Alternative B>

- Why it was considered.
- Why it was rejected.

## References

- `<link-or-path>`
- `<link-or-path>`
