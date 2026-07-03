---
trigger: glob
description: "BioETL Testing — VCR, E2E, Architecture Tests"
globs:
  - "tests/**/*.py"
---

# Testing Levels

**Canonical references:** `AGENTS.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, `docs/02-architecture/decisions/`.

| Level | Scope | Key Requirements |
|-------|-------|------------------|
| Unit | Domain logic | In-memory fakes, NO MagicMock |
| Integration | API adapters | VCR.py cassettes, sanitize secrets |
| E2E | Full pipeline | `@pytest.mark.e2e`, local-only |
| Architecture | Layer boundaries | NO random/datetime violations |
| Contract | Live APIs | Monthly, separate CI |

# VCR.py Rules

- Store in: `tests/fixtures/vcr/`
- **MANDATORY sanitization** before commit: redact `Authorization`, `X-Api-Key`, `X-Auth-Token`, `Set-Cookie`, `Cookie`, `access_token`, `refresh_token`, `password`, `secret`, `api_key`, `token`, `client_secret`, `private_key`
- Values MUST be obvious placeholders (`DUMMY_TOKEN`, `FAKE_API_KEY`, `REDACTED`) — never production-like (`sk_live_`, JWT triplets, long hex/base64)
- Configure `filter_sensitive_data` for each new sensitive header/field
- CI: `--vcr-record=none` (fail if cassette missing)

# E2E Tests

- Runtime: local-only (filesystem, MemoryLock, LocalCheckpoint)
- Helpers: `create-test-context()`, `assert-bronze-files-exist()`
- Run: `pytest tests/e2e/ -v -m e2e`

# Critical Architecture Tests

| Test | Validates |
|------|-----------|
| `test_no_random_in_writers.py` | No `random` in storage writers |
| `test_no_datetime_now_in_infrastructure.py` | No `datetime.now()` in infra |
| `test_no_structlog_in_application_interfaces.py` | No direct `structlog` import |
| `test_future_annotations_policy.py` | `__future__` annotations present |
| `test_quality_debt_scorecard.py` | Debt compliance |

# Coverage

**Minimum 85%** — enforced in CI via `--cov-fail-under=85`
- CI MUST fail when coverage drops below 85%
- New/modified files MUST NOT be significantly below 85% even if global passes

# Quick Verification

```bash
# File stats
wc -l <file>
grep -c "def \|async def " <file>

# Delegation pattern
grep -o "self\.[a-z_]*\." <file> | sort -u

# Find tests
find tests -name "*.py" -exec grep -l "ClassName" {} \;
```
