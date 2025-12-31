# False Positives Log
Date: 2025-12-30

## Rejected Assertions

### FP-001: "Print statements in codebase"

**Assertion**: Codebase contains `print()` statements forbidden by rules.

**Validation**:
- Code: `grep` found prints in `pubmed_client.py`, `batch_executor.py`, etc.
- Verification: Manual inspection confirms ALL are inside `>>>` docstring examples or `...` ellipsis blocks.
- Category: VP-002 (Permitted exceptions for docstrings).

**Verdict**: INVALID

### FP-002: "MemoryLock requires Redis"

**Assertion**: `MemoryLock` is insufficient for production, Redis is required.

**Validation**:
- Docs: `ADR-010` explicitly states "Local-Only deployment" is the current architectural decision, rejecting Redis/distributed locks for now.
- Code: `MemoryLock` is correctly implemented for single-process usage.
- Category: Design Decision (ADR-010).

**Verdict**: INVALID
