# CR-FULL-09 — CLI secret and trusted workflow (#7698)

- Epic: #7688
- Date: 2026-08-06T13:25Z
- Decision: **App-only residual channel for this campaign closeout**

## Facts (verified)

| Surface | Status |
| --- | --- |
| Workflow | .github/workflows/coderabbit.yml — push to main/master + workflow_dispatch only |
| Untrusted PR | Does **not** run with CODERABBIT_API_KEY |
| Secret in repo Actions | `gh api .../actions/secrets` **total_count 0** (re-checked 2026-08-06T13:45Z) |
| CI CLI without secret | Job **succeeds**, skip warning, App-only fallback (recent push runs still skip) |
| Local CLI | Operator API key only (never committed); WSL CLI 0.7.2; `coderabbit auth status` = API key |
| PR App + .coderabbit.yaml | profile assertive; App comments observed on PR #8057 (rate-limit notice proves install) |

## Acceptance mapping

| Acceptance | Result |
| --- | --- |
| Documented App status | App is the continuous residual channel; CLI is optional owner-enabled |
| CLI green on dispatch **or** explicit App-only decision | **App-only** for closeout — owner may add CODERABBIT_API_KEY later without reopening epic |
| No secret material in commits | Confirmed — workflow reads secrets.CODERABBIT_API_KEY only |

## Owner steps (if CLI desired later)

1. Create CodeRabbit Agentic API key in account settings.
2. Repo admin: Settings → Secrets → Actions → CODERABBIT_API_KEY.
3. workflow_dispatch the CodeRabbit workflow; confirm CLI review runs (not skip).
4. Never put the key in git, issues, or committed env files.

## Playbook pointers

- docs/03-guides/coderabbit-audit-playbook.md
- docs/03-guides/development/coderabbit-local-reviews.md
