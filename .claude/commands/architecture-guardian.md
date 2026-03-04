---
description: "Аудит архитектурных границ BioETL: матрица импортов, DI violations, naming conventions, anti-patterns. Использовать после изменений в src/bioetl/ или перед PR."
---

# Architecture Guardian

## Objective
Protect the BioETL hexagonal architecture by auditing code changes for boundary violations, DI issues, naming conventions, and ADR compliance.

## Import Rules Matrix (Critical)
| From \ To | domain | application | infrastructure | composition | interfaces |
|---|---|---|---|---|---|
| domain | OK | NO | NO | NO | NO |
| application | OK | OK | NO | NO | NO |
| infrastructure | OK (ports only) | NO | OK | NO | NO |
| composition | OK | OK | OK | OK | NO |
| interfaces | OK | OK | OK | OK | OK |

## Allowed Exceptions
- `TYPE_CHECKING` imports (type hints only, no runtime dependency).
- `domain.ports` imports in infrastructure (port protocols are contracts).
- `domain.types` and `domain.exceptions` imports everywhere.

## DI Violations (Critical)
| ID | Pattern | Detection |
|---|---|---|
| DI-V001 | Hard-coded constructor | `rg "self\\.[a-z_]* = [A-Z][a-zA-Z]*\\(" src/bioetl/application -g "*.py"` |
| DI-V002 | Method-level instantiation | Inspect method bodies |
| DI-V003 | Service locator | `rg "Locator\|Container\\.resolve" src/bioetl -g "*.py"` |
| DI-V004 | Import-time side effects | Module-level assignments |
| DI-V005 | Factory in business logic | Factories outside `composition/` |

## Validation Workflow
1. Read target files (focus on changed files).
2. Check imports against matrix (ignore `TYPE_CHECKING`).
3. Verify naming: Classes PascalCase+suffix, Functions snake_case+prefix, Modules lowercase_snake_case.
4. Detect anti-patterns: DI violations, direct `import structlog`, sentinel values, `print()`, hardcoded secrets.
5. Verify type annotations on public functions.
6. Generate structured report with exact file:line references.

## Valid Patterns (Do Not Flag)
- Optional parameters with defaults.
- NoOp implementations (Null Object pattern).
- Re-exports for compatibility.
- Large files with clean delegation.
- Graceful degradation.
- Int→float coercion in Gold schemas.

## Verification Commands
```bash
rg "from bioetl\\.infrastructure" src/bioetl/application -g "*.py" | rg -v "TYPE_CHECKING"
rg "from bioetl\\.application" src/bioetl/infrastructure -g "*.py" | rg -v "TYPE_CHECKING"
rg "print\\(" src/bioetl -g "*.py" | rg -v "# noqa"
rg "self\\.[a-z_]* = [A-Z][a-zA-Z]*\\(" src/bioetl/application -g "*.py"
pytest tests/architecture/ -v
mypy src/bioetl/ --strict
```

## Report Format
```markdown
## Architecture Validation Report
**Date**: YYYY-MM-DD | **Scope**: {files} | **Status**: PASS|FAIL|WARN

| Category | Issues | Severity |
|---|---|---|
| Import Violations | N | CRITICAL/MEDIUM |
| DI Violations | N | CRITICAL |
| Naming Violations | N | MEDIUM |
| Anti-Patterns | N | HIGH |

### Critical Issues (Must Fix)
- **File**: `path:line` | **Rule**: ARCH-NNN | **Fix**: ...

### Verification: `pytest tests/architecture/ -v && mypy src/bioetl/ --strict && make lint`
```

## Constraints
- **MUST** flag all import boundary violations (except `TYPE_CHECKING`).
- **MUST** provide exact file:line references.
- **MUST NOT** flag `TYPE_CHECKING` imports or valid patterns listed above.
- **MUST NOT** make assumptions without code verification.
