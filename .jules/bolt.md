## 2026-10-11 - Python Native Short-Circuiting
**Learning:** Using `any()` with list literals in Python forces memory allocation and iteration overhead.
**Action:** Replace `any([a, b, c])` patterns with native chained logical operators `(a or b or c)` to leverage native short-circuiting at the bytecode level and reduce overhead.
