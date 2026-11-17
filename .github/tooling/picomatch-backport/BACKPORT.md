# Local picomatch security backport

This is a private BioETL build, **not an upstream release**. Version
`4.0.8-bioetl.9` identifies modified code based on upstream `4.0.7`.

It addresses GHSA-fc5q-39xc-vjpf / CVE-2026-112366 with a **fail-closed**
boundary:

1. Base guard from micromatch/picomatch#194 (literal fallback path).
2. Repeated `+(...)` / `*(...)` bodies must be a fixed ASCII word
   (`[A-Za-z0-9_]+`); otherwise literal-escape fallback.
3. Allowlist runs **before** optional `maxExtglobRecursion`.
4. Risk analysis runs only for repeated `+(`/`*(`; nested extglob depth
   capped (`DEFAULT_MAX_EXTGLOB_NESTING=32`).
5. Nested `+(…)` / `*(…)` under `@`/`?`/`!` is treated as risky; trailing
   regex `+` is not attached onto a group that already contains an
   unbounded quantifier (closes `@(+(a))+` / `(+(a))+`).

Third-party sources ship **only** in the npm archive.
**No OSV advisory is ignored or suppressed.**
