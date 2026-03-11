# Release Checklist v5.9.0

> **Historical Document**: This checklist was created for BioETL v5.9.0 (verified 2026-01-13).
> It is preserved for reference only. For current release procedures, create a new checklist
> aligned with the latest project version.

This checklist documents the pre-release verification completed for BioETL v5.9.0.

## Final Verification Results

### 5.1. Build & Test Verification

| Command                | Status  | Notes                                                |
| ---------------------- | ------- | ---------------------------------------------------- |
| `make clean`           | ✅ Pass | Build artifacts cleaned                              |
| `make clean-preflight` | ✅ Pass | Extended cleanup via `scripts/preflight-cleanup.sh`  |
| `make install`         | ✅ Pass | Dependencies installed via uv                        |
| `make lint`            | ✅ Pass | ruff and mypy checks were green at verification time |
| `make test`            | ✅ Pass | Stable local test suite was green at verification time |

### 5.2. Smoke Tests

| Test           | Status  | Result                           |
| -------------- | ------- | -------------------------------- |
| Version import | ✅ Pass | `bioetl.--version-- = "5.9.0"`   |
| CLI help       | ✅ Pass | All commands displayed correctly |

## Documentation Checklist

| Item                                      | Status | Location                  |
| ----------------------------------------- | ------ | ------------------------- |
| README.md актуален и содержит Quick Start | ✅     | `/README.md`              |
| CHANGELOG.md заполнен для v5.9.0          | ✅     | `/CHANGELOG.md`           |
| LICENSE файл присутствует                 | ✅     | `/LICENSE` (MIT)          |
| CONTRIBUTING.md описывает процесс         | ✅     | `/CONTRIBUTING.md`        |
| SECURITY.md определяет политику           | ✅     | `/SECURITY.md`            |
| API docs сгенерированы                    | ✅     | `/docs/04-reference/api/` |

## Code Quality

| Metric                      | Target   | Actual            | Status  |
| --------------------------- | -------- | ----------------- | ------- |
| Coverage                    | ≥85%     | 88.43% at verification time | ✅ Pass |
| mypy --strict               | 0 errors | 0 errors          | ✅ Pass |
| Ruff                        | 0 errors | 0 errors          | ✅ Pass |
| All tests green             | Yes      | Yes, at verification time | ✅ Pass |
| No TODO/FIXME without issue | N/A      | Verified          | ✅ Pass |

## Security

| Check                      | Status  | Notes                                            |
| -------------------------- | ------- | ------------------------------------------------ |
| pip-audit: 0 HIGH/CRITICAL | ✅ Pass | urllib3 upgraded to 2.6.3 (CVE-2026-21441 fixed) |
| Нет хардкода секретов      | ✅ Pass | Environment variables used                       |
| VCR кассеты санитизированы | ✅ Pass | No Authorization/API keys in cassettes           |
| Dependencies pinned        | ✅ Pass | uv.lock file present                             |

## Release Artifacts

| Item                   | Status     | Value                    |
| ---------------------- | ---------- | ------------------------ |
| pyproject.toml version | ✅         | 5.9.0                    |
| `--version--`          | ✅         | 5.9.0                    |
| README badge version   | ✅         | 5.9.0                    |
| Git tag                | ⏳ Pending | v5.9.0 (to be created)   |
| RELEASE-NOTES          | ⏳ Pending | In CHANGELOG.md          |
| Wheel и sdist          | ⏳ Pending | CI will build on release |

## CI/CD

| Component        | Status        | Notes                             |
| ---------------- | ------------- | --------------------------------- |
| CI pipeline      | ✅ Configured | `.github/workflows/tests.yml`     |
| Release workflow | ✅ Configured | `.github/workflows/release.yml`   |
| PyPI credentials | ✅ Configured | OIDC trusted publishing           |
| Coverage gate    | ✅ Enforced   | `--cov-fail-under=85` in Makefile |

## Known Issues

### pytest-xdist Collection Issue (RESOLVED)

~~When running `make test` with parallel execution (`-n auto`), there's a test collection difference error.~~

**Status**: RESOLVED (2026-01-16)

**Resolution**: The issue was intermittent and no longer occurs with current test configuration.
Tests now run correctly with `pytest-xdist` using `--dist loadscope`.

**Performance**:

- Serial execution: ~147s
- Parallel execution: ~54s (63% improvement)

## Release Steps

1. ✅ Run `make clean-preflight` (or `make clean-preflight DRY-RUN=1` for preview)
1. ✅ Complete this checklist verification
1. ✅ Fix urllib3 vulnerability (CVE-2026-21441)
1. ⏳ Create release branch: `git checkout -b release/v5.9.0`
1. ⏳ Create git tag: `git tag -a v5.9.0 -m "Release v5.9.0"`
1. ⏳ Push tag: `git push origin v5.9.0`
1. ⏳ Create GitHub Release with release notes

----------------------------------------------------------------------

*Verified: 2026-01-13*
*Version: 5.9.0*
