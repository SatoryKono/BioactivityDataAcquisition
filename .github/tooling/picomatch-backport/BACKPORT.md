# Local picomatch security backport

This is a private BioETL build, **not an upstream release**. Version
`4.0.8-bioetl.3` identifies modified code based on upstream `4.0.7`.

It addresses GHSA-fc5q-39xc-vjpf / CVE-2026-112366:

1. Base guard from https://github.com/micromatch/picomatch/pull/194 at commit
   `7be3276fb8bd215a8c73fa066bcaf696c244ad88` (`hasMixedWildcards` lineage).
2. BioETL `hasUnboundedWildcard`: any top-level `*` in a repeated `+(...)` /
   `*(...)` branch (closes `+(*)` / `+(*a)` that #194 left open).
3. BioETL `hasNestedUnboundedWildcard`: nested extglob bodies such as
   `@(*a)` inside `+(@(*a))` / `*(@(*a))`, which bypass top-level scans because
   wildcards sit inside parentheses.

As with braces-backport, third-party sources ship **only** in the npm archive
(no unpacked `lib/` tree). `provenance.json` pins packaged file hashes.
Regression tests unpack the archive and run timed ReDoS probes. **No OSV
advisory is ignored or suppressed.**

Replace this backport when an official release incorporates a complete fix
(`first_patched_version` / npm `>4.0.7` that closes nested cases). Before
removing it, regenerate jscpd and Grafana plugin lockfiles and verify the
Class-lane OSV gate.
