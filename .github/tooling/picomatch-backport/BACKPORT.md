# Local picomatch security backport

This is a private BioETL build, **not an upstream release**. Version
`4.0.8-bioetl.8` identifies modified code based on upstream `4.0.7`.

It addresses GHSA-fc5q-39xc-vjpf / CVE-2026-112366 with a **fail-closed**
boundary on repeated `+(...)` / `*(...)` bodies, plus compile-time bounds:

1. Base guard from micromatch/picomatch#194 (literal fallback path).
2. Allowlist: the body of a repeated extglob must be a fixed ASCII word
   (`[A-Za-z0-9_]+`). Any other body uses the existing literal-escape fallback.
3. The allowlist runs **before** optional `maxExtglobRecursion`.
4. Risk analysis runs **only** for repeated `+(`/`*(` (not on every `?(…)`
   close), and nested extglob depth is capped (`DEFAULT_MAX_EXTGLOB_NESTING`,
   default 32) with literal fallback — preventing compile-time DoS on
   deeply nested `?(a`…`)` patterns without requiring `.test()`.

Third-party sources ship **only** in the npm archive (braces layout).
Regression tests unpack the archive and run timed ReDoS / compile probes.
**No OSV advisory is ignored or suppressed.**
