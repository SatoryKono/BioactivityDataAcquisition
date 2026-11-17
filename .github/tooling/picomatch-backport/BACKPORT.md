# Local picomatch security backport

This is a private BioETL build, **not an upstream release**. Version
`4.0.8-bioetl.5` identifies modified code based on upstream `4.0.7`.

It addresses GHSA-fc5q-39xc-vjpf / CVE-2026-112366:

1. Base guard from micromatch/picomatch#194.
2. `hasUnboundedWildcard`: top-level `*` in repeated `+(...)` / `*(...)`.
3. `hasNestedRiskyExtglob`: nested extglob bodies (wildcards and multi-branch
   risk rules).
4. General literal prefix-overlap: any normalized literal branches where one
   is a prefix of the other (`a|aa`, `ab|abab`), top-level or nested
   (`+(@(ab|abab))`).

Third-party sources ship **only** in the npm archive (braces layout).
Regression tests unpack the archive and run timed ReDoS probes with
48-unit ambiguous inputs. **No OSV advisory is ignored or suppressed.**
