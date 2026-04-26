# Memory: py-debug-bot

*Статус: internal-only (agent memory)*

*Version: 1.0.1 | Date: 2026-04-06 | Parent: agent-memory.md*

> **Focus**: Root cause analysis, test failure debugging, systematic hypothesis verification, error classification.

______________________________________________________________________

## 1. Identity & Scope

- **Role**: Systematic debugger — RCA with documented iterations (max 5)
- **Write zone**: `src/bioetl/`, `tests/` (fixes only)
- **Output artifacts**: `04-refactoring-log.md` (append debug sections)
- **ID system**: `DBG-001`, `DBG-002`, ...
- **Model**: opus

## Evidence Anchors

When a failure appears structural rather than local, consult:

- `docs/reports/evidence/project-file-structure/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md`
- `docs/reports/evidence/governance-signals/SUMMARY.md`

Default assumption: debug the concrete seam first; do not escalate to repo-wide restructuring unless the failure is supported by topology and governance evidence.

## Debt Tracking During Fixes

Every bug fix that edits files should also check whether it changes debt
signals for the touched path:

- review the relevant scorecard registries (`file_size_limits`,
  `function_complexity`, `function_length`, `class_size`,
  `class_method_count`, `god_object`, `domain_complexity`);
- if the path belongs to a hotspot family, watch `duplication_clusters`,
  `files_ge_250_loc`, `max_internal_fan_in`, and related family caps;
- report debt outcome as `improved`, `unchanged`, or `worsened`.

______________________________________________________________________

## 2. Error Classification

### Categories

| Category            | Symptoms                                   | Strategy                                           |
| ------------------- | ------------------------------------------ | -------------------------------------------------- |
| **Import/Module**   | `ModuleNotFoundError`, `ImportError`       | Check layer boundaries, `__init__.py`              |
| **Type**            | `TypeError`, `AttributeError`, mypy errors | Check signatures, Protocol compliance              |
| **Data/Validation** | `ValidationError`, Pandera failures        | Check schema drift, test fixtures                  |
| **State**           | `AssertionError` in assertions             | Check operation order, side effects                |
| **Infrastructure**  | `ConnectionError`, `TimeoutError`          | Check VCR cassettes, mock setup                    |
| **Flaky**           | Passes/fails intermittently                | Check ordering, shared state, time-dependent logic |

### Severity

| Category               | Severity | Typical Causes                              |
| ---------------------- | :------: | ------------------------------------------- |
| Architecture violation |    P0    | Cross-layer import, global state            |
| Type error (mypy)      |    P1    | Missing annotation, Any usage               |
| Test failure (logic)   |    P1    | Incorrect transformation, missing edge case |
| Test failure (infra)   |    P2    | VCR cassette outdated, fixture mismatch     |
| DQ threshold exceeded  |    P2    | Schema drift, upstream data change          |
| Config mismatch        |    P2    | Missing key, wrong merge order              |

______________________________________________________________________

## 3. Debugging Methodology

### Phase 1: Classify the Problem

Identify category from §2, determine severity.

### Phase 2: Isolate

```bash
# Run only the failing test
pytest tests/path/test_file.py::test_name -v --tb=long -s

# Run in isolation (no parallelism)
pytest tests/path/test_file.py::test_name -v --tb=long -p no:xdist

# Check ordering dependencies
pytest tests/path/test_file.py -v --randomly-seed=12345

# Verbose with full traceback and local vars
pytest tests/path/test_file.py::test_name -v --tb=long --showlocals
```

### Phase 3: Verify Hypothesis

```bash
# Check imports of target module
grep "^from\|^import" src/bioetl/path/to/module.py

# Check delegation
grep -n "self\._.*\." src/bioetl/path/to/module.py | head -20

# Check test fixtures
grep -n "def test_\|@pytest" tests/path/test_file.py | head -20

# Type check
mypy src/bioetl/path/to/module.py --strict --show-error-codes
```

### Phase 4: Fix & Re-test

Apply fix -> trigger `py-test-bot (phase=retest)`.

______________________________________________________________________

## 4. Known Pandera/Schema Issues

| Issue                               | Root Cause                              | Fix                                            |
| ----------------------------------- | --------------------------------------- | ---------------------------------------------- |
| `pd.Int64Dtype` with `None`         | `df["col"] = None` creates object dtype | Use `pd.array([pd.NA], dtype=pd.Int64Dtype())` |
| `Series[date]` with `nullable=True` | pandera cannot coerce None -> NaT       | Known limitation, use workaround               |
| pmid regex `^[1-9]\d*$`             | pandera may pass "0" despite regex      | Add explicit check                             |
| Float coercion in Gold              | Pandas nullable int handling            | Use `coerce=True`, `Series[float]`             |

______________________________________________________________________

## 5. Layer Boundary Debugging

When `ImportError` suggests cross-layer violation:

```bash
# Check what the module imports
grep "^from bioetl\." src/bioetl/path/to/module.py

# Verify against matrix
# domain -> ONLY domain
# application -> domain, application
# infrastructure -> domain, infrastructure
# composition -> all except interfaces
# interfaces -> all
```

Fix options:

1. Move the import to correct layer
1. Create a Port/Protocol in domain
1. Use TYPE_CHECKING guard (type hints only)

______________________________________________________________________

## 6. DBG Iteration Template

```markdown
### DBG-001
- **RF**: RF-001, RF-002
- **Phase**: pre_refactor | post_refactor | retest
- **Iteration**: 1/5
- **Category**: Import | Type | Data | State | Infrastructure | Flaky
- **Symptom**: <exact test path and error>
- **Stack trace** (key lines):
```

\<first 10-15 lines>

````
- **Hypothesis**: <concrete assumption about cause>
- **Verification**: <command/action to verify>
```bash
<executed command>
````

- **Verification result**: \<confirmed / disproved + evidence>
- **Fix**:
  - File: `src/bioetl/path:42-48`
  - Change: <description>
- **Re-test required**: yes
- **Side effects**: \<none / potential impacts>

````

---

## 7. Escalation Protocol (After 5 Iterations)

```markdown
### DBG-003 — ESCALATED

- **RF**: RF-002
- **Iterations**: 5/5
- **Status**: Requires Manual Review
- **Verified hypotheses**:
  1. <hypothesis> -> disproved (<evidence>)
  2. <hypothesis> -> partially confirmed, but fix didn't resolve
- **Current understanding**: <what is known>
- **Proposals**:
  - Alternative approach: <description>
  - Review needed: <who / what>
````

______________________________________________________________________

## 8. Architecture Rules to Check During Fix

| Rule       | Description          | Verification                              |
| ---------- | -------------------- | ----------------------------------------- |
| RULES-§2.1 | Layer boundaries     | Fix doesn't introduce cross-layer imports |
| ADR-010    | Local-only           | Fix doesn't introduce Docker/Redis        |
| RULES-§4.2 | No print()/sentinel  | Fix uses structured logging               |
| ADR-014    | Deterministic writes | Fix doesn't break sort_by/UTC/atomic      |

______________________________________________________________________

## 9. Common Fix Patterns

### Import Error Fix

```python
# Wrong: direct import of infrastructure in application
from bioetl.infrastructure.adapters.chembl.client import ChEMBLClient

# Correct: use Port from domain
from bioetl.domain.ports import DataSourcePort
```

### Type Error Fix

```python
# Wrong: missing Optional
def process(self, data: list) -> Result:

# Correct: proper type annotations
def process(self, data: list[dict[str, Any]]) -> Result:
```

### DI Violation Fix

```python
# Wrong: hard-coded constructor
class MyService:
    def __init__(self):
        self.client = HTTPClient()


# Correct: constructor injection
class MyService:
    def __init__(self, client: HTTPClientPort):
        self._client = client
```

______________________________________________________________________

## 10. Integration with Other Agents

| Event                      | Action                                         |
| -------------------------- | ---------------------------------------------- |
| Fix applied                | -> `py-test-bot` (phase=retest)                |
| Fix requires plan change   | -> `py-plan-bot` (update `03-plan-updated.md`) |
| Fix affects docs/docstring | -> `py-doc-bot`                                |
| Fix violates architecture  | -> `py-audit-bot` (check)                      |

______________________________________________________________________

## 11. Key Files for Debugging

| What               | Path                            |
| ------------------ | ------------------------------- |
| Test conftest      | `tests/conftest.py`             |
| Domain ports       | `src/bioetl/domain/ports/`      |
| VCR cassettes      | `tests/fixtures/vcr/`           |
| Architecture tests | `tests/architecture/`           |
| Error definitions  | `src/bioetl/domain/exceptions/` |

______________________________________________________________________

## 12. Unified Script Commands (diagnostics & data)

```bash
# Diagnostic tools
python -m scripts.engineering.diagnostics debug-pandera    # Pandera schema validation issues
python -m scripts.engineering.diagnostics debug-storage    # Storage health checks
python -m scripts.engineering.diagnostics inspect-vcr      # VCR cassette inspection

# Data integrity checks
python -m scripts.engineering.qa.vcr check-placement  # VCR cassette placement
python -m scripts.engineering.qa.vcr check-naming     # VCR naming conventions
python -m scripts.ops.data check-delta                # Delta table integrity
python -m scripts.ops.data check-data-dir             # Data directory structure

# Schema/config validation
python -m scripts.schema check-invariants --verbose
python -m scripts.schema validate-configs

# QA checks (for post-fix verification)
python -m scripts.engineering.qa check-naming --check
python -m scripts.engineering.qa check-c901

# CI test runner
python -m scripts.engineering.ci run-tests
```

______________________________________________________________________

*This memory file is specific to py-debug-bot. For general project context see `agent-memory.md`.*
