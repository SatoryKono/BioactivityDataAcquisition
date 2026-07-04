# Memory: py-test-bot

*Статус: internal-only (agent memory)*

*Version: 1.0.1 | Date: 2026-04-06 | Parent: agent-memory.md*

> **Focus**: Test execution, coverage analysis, VCR management, failure classification, baseline/final/retest.

______________________________________________________________________

## 1. Identity & Scope

- **Role**: Objective code state measurement through tests
- **Write zone**: `tests/`
- **Output artifacts**: `02-test-baseline.md`, `05-test-final.md`
- **ID system**: `FAIL-001`, `FAIL-002`, ...
- **Model**: sonnet

## Evidence Anchors

For test recommendations that imply structural conclusions, consult:

- `docs/reports/evidence/project-package-topology/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md`
- `docs/reports/evidence/governance-signals/SUMMARY.md`

Do not infer that a broad layer needs reorganization from test spread alone. Prefer family-level calibration plus failing evidence.

## Debt Tracking During Test Edits

When tests are added or changed alongside code:

- treat test evidence as support for debt evaluation, not as a standalone debt
  classifier;
- preserve the hard rule `ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.`;
- if the task changes tracked files, include debt outcome in the closeout:
  `improved`, `unchanged`, or `worsened`;
- when tests cover exemption or scorecard behavior, keep
  `configs/quality/debt_scorecard.yaml` and
  `configs/quality/architecture_metric_exemptions.yaml` semantics aligned.

______________________________________________________________________

## 2. Test Directory Structure

```
tests/
├── unit/              # Fast, in-memory fakes
├── integration/       # VCR.py for HTTP
├── architecture/      # Layer boundaries (1392 collected tests)
├── contract/          # API contract tests
├── e2e/               # End-to-end tests
├── benchmarks/        # Performance benchmarks
├── performance/       # Load tests
├── security/          # Security tests
├── smoke/             # Quick smoke tests
└── fixtures/
    └── vcr/           # VCR cassettes per provider
        ├── chembl/
        ├── pubchem/
        ├── uniprot/
        └── ...
```

______________________________________________________________________

## 3. Quality Thresholds

| Metric                 | Threshold | Action on Violation |
| ---------------------- | :-------: | ------------------- |
| Coverage (overall)     |  >= 85%   | MUST: add tests     |
| Coverage (domain)      |  >= 90%   | MUST: add tests     |
| mypy errors            |     0     | MUST: fix           |
| Architecture tests     | 100% pass | MUST: fix           |
| New code without tests |     0     | MUST: add tests     |

______________________________________________________________________

## 4. Test Selection Strategy

| Changed Files                         | Tests to Run                                                                       |
| ------------------------------------- | ---------------------------------------------------------------------------------- |
| `domain/**`                           | `tests/unit/domain/` + `tests/architecture/`                                       |
| `application/**`                      | `tests/unit/application/` + related integration                                    |
| `infrastructure/adapters/{provider}/` | `tests/unit/infrastructure/adapters/{provider}/` + `tests/integration/{provider}/` |
| `composition/**`                      | `tests/unit/composition/` + `tests/architecture/`                                  |
| `interfaces/**`                       | `tests/unit/interfaces/`                                                           |
| `configs/**`                          | `tests/integration/` (config validation)                                           |
| Any Python file                       | `make lint` first                                                                  |

______________________________________________________________________

## 5. Execution Commands

```bash
# Unit tests (specific module)
pytest tests/unit/path/to/test_module.py -v --tb=short

# Unit tests with coverage
pytest tests/unit/path/ -v --cov=src/bioetl/path/ --cov-report=term-missing

# Integration tests
pytest tests/integration/path/ -v --tb=short

# Architecture tests (ALWAYS run for boundary changes)
pytest tests/architecture/ -v

# Full run (for final phase)
pytest tests/ -v --cov=src/bioetl/ --cov-report=term-missing --tb=short

# Type checking
mypy src/bioetl/path/to/module.py --strict

# Lint check
make lint
```

______________________________________________________________________

## 6. VCR.py Cassette Management

```bash
# Record new cassette (requires network)
pytest tests/integration/chembl/ --vcr-record=new_episodes -v

# Playback only (CI mode, default)
pytest tests/integration/ --vcr-record=none -v
```

### Cassette Rules

- One cassette per test function
- Store in `tests/fixtures/vcr/{provider}/`
- Sanitize secrets in `before_record` callback
- Re-record when API contract changes

______________________________________________________________________

## 7. Failure Classification

| Error Type        | Diagnosis                             | Action                 |
| ----------------- | ------------------------------------- | ---------------------- |
| `AssertionError`  | Logic bug, check expected vs actual   | -> py-debug-bot        |
| `ImportError`     | Missing dependency or circular import | Check layer boundaries |
| `AttributeError`  | API change or typo                    | Check signatures       |
| `TypeError`       | Signature mismatch                    | Check type hints       |
| `ValidationError` | Schema violation (Pandera/Pydantic)   | Check schema drift     |
| `ConnectionError` | Network/VCR cassette issue            | Check VCR setup        |
| `TimeoutError`    | Async timeout                         | Check async patterns   |

______________________________________________________________________

## 8. Baseline Report Template

```markdown
# Test Baseline: <task_id>

**Date**: YYYY-MM-DD HH:MM
**Phase**: baseline | final | retest
**RF scope**: RF-001, RF-002

## Results
| Category | Total | Pass | Fail | Skip | Error |
|----------|:-----:|:----:|:----:|:----:|:-----:|
| unit | 42 | 40 | 1 | 1 | 0 |
| architecture | 97 | 97 | 0 | 0 | 0 |

## Coverage
| Module | Coverage |
|--------|:--------:|
| overall | 88.43% |

## Failures (if any)
### FAIL-001
- **Test**: `tests/unit/.../test_X.py::test_something`
- **RF**: RF-001
- **Stack trace**: <first 20 lines>
- **Status**: forwarded to py-debug-bot
```

______________________________________________________________________

## 9. Test Writing Conventions

### Unit Tests

- Arrange-Act-Assert pattern
- No I/O, mock via DI (inject fakes)
- Test edge cases and error paths
- Use `pytest.mark.parametrize` for variants

### Integration Tests

- VCR.py for HTTP (MANDATORY)
- One cassette per test function
- Test pagination, rate limiting, error responses

### Architecture Tests

- Verify import boundaries
- 1392 collected tests in `tests/architecture/`
- Run after any layer boundary changes

______________________________________________________________________

## 10. Integration with Other Agents

| Event                               | Action                               |
| ----------------------------------- | ------------------------------------ |
| Plan ready (py-plan-bot)            | -> test-bot (phase=baseline)         |
| Baseline FAIL                       | -> py-debug-bot with FAIL-\* report  |
| Code complete (orchestrator/direct) | -> test-bot (phase=final)            |
| Final FAIL                          | -> py-debug-bot with FAIL-\* report  |
| Fix applied (py-debug-bot)          | -> test-bot (phase=retest)           |
| All tests pass                      | -> py-doc-bot + py-audit-bot (final) |

______________________________________________________________________

## 11. Key Files for Testing

| What                | Path                                    |
| ------------------- | --------------------------------------- |
| Test configuration  | `pyproject.toml` (pytest section)       |
| Conftest (root)     | `tests/conftest.py`                     |
| VCR fixtures        | `tests/fixtures/vcr/`                   |
| Architecture tests  | `tests/architecture/`                   |
| Config gap analysis | `scripts/schema/config_gap_analysis.py` |

______________________________________________________________________

## 12. Unified Script Commands (test & CI)

```bash
# CI test execution
python -m scripts.engineering.ci run-tests                 # Resilient pytest runner
python -m scripts.engineering.ci quality-gate              # Quality integral gate
python -m scripts.engineering.ci e2e-skip-rate             # E2E skip rate check
python -m scripts.engineering.ci e2e-rerun                 # E2E rerun stability

# Data integrity (pre-test validation)
python -m scripts.engineering.qa.vcr check-placement  # VCR cassette placement
python -m scripts.engineering.qa.vcr check-naming     # VCR naming conventions
python -m scripts.ops.data check-delta                # Delta table integrity

# Schema validation (config tests)
python -m scripts.schema validate-configs
python -m scripts.schema check-invariants --verbose

# Dev shortcuts
python -m scripts.engineering.dev run-tests                # Local test runner
python -m scripts.engineering.dev test-changed             # Tests for changed files only
```

______________________________________________________________________

*This memory file is specific to py-test-bot. For general project context see `agent-memory.md`.*
