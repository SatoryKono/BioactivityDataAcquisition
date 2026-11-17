# Local picomatch security backport

This is a private BioETL build, **not an upstream release**. Version
`4.0.8-bioetl.16` identifies modified code based on upstream `4.0.7`.

It addresses GHSA-fc5q-39xc-vjpf / CVE-2026-112366 with a **fail-closed**
boundary:

1. Base guard from micromatch/picomatch#194 (literal fallback path).
2. Repeated `+(...)` / `*(...)` bodies must be a fixed ASCII word
   (`[A-Za-z0-9_]+`); otherwise literal-escape fallback.
3. Allowlist runs **before** optional `maxExtglobRecursion`.
4. Risk analysis runs only for repeated `+(`/`*(`; nested extglob depth
   capped (`DEFAULT_MAX_EXTGLOB_NESTING=32`).
5. Nested `+(…)` / `*(…)` under `@`/`?`/`!` is treated as risky; trailing
   raw `+` inside or after groups is literal. This closes both nested
   quantifiers (`@(+(a))+` / `(+(a))+`) and ambiguous finite alternatives
   (`(a|aa)+` / `@(a|aa)+` / `{a,aa}+`). Explicit `+(word)` extglobs remain supported.
6. Nested `@(...)` body markers propagate to parent negate `inner` (`*` / `/`).
   Closed character classes and double-quoted `+(…)` / `*(…)` are not treated as
   nested repeated extglobs; single quotes and unclosed `[` stay literal and do
   not hide later `+(…)` / `*(…)`.
7. At most one compiled quantified extglob (`+(word)`, `*(word)`, or
   `?(...)`) per pattern; further sequential copies stay fully literal,
   including their parentheses. Raw `?`
   after a parenthesized group is also literal.
8. Patterns compiling multiple overlapping alternative-bearing groups use whole-pattern
   literal fallback. This includes compositions of raw parentheses, `@(...)`,
   and `{...,...}`. Overlap uses effective regex flags, including both
   `nocase` and explicit `flags: "i"`; a single overlapping group and disjoint fixed-word alternatives stay supported.

9. Source nesting beyond 32 groups triggers one whole-pattern literal escape
   before tokenization, bounding the cost of deep fallback.

These restrictions intentionally narrow complex glob semantics. Ordinary
file-extension and path globs remain supported; consumers are regression-tested.

Third-party sources ship **only** in the npm archive.
**No OSV advisory is ignored or suppressed.**
