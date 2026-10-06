# Local braces security backport

This is a private BioETL build, **not an upstream release**. Version
`3.0.4-bioetl.1` identifies modified code based on upstream `3.0.3`.
It addresses CVE-2026-93687 / GHSA-vfj7-8cjw-p6xm with the proposed upstream
fix from https://github.com/micromatch/braces/pull/72 at commit
`28d440b5dd449dbf1fe6f3506cf94ecca4d02660` in `FSDevelop/braces`.

The archive contains the JavaScript implementation and MIT license unchanged
from that commit. `provenance.json` pins each upstream file hash; the upstream
commit remains the source of truth. Only package metadata differs:
the private version, description and omission of upstream development tooling.
The tarball is built with `npm pack`; architecture tests verify its bytes
against the pinned source hashes and each consumer lockfile's SHA-512 integrity.
No OSV advisory is ignored or suppressed.

The patch bounds brace/parenthesis nesting to 100, honors stricter limits,
bounds traversal of caller-supplied ASTs and rejects cyclic parent chains.
The pinned upstream suite passed 904 tests on Node 25.2.1. CI also tests the
installed package via `node .github/tooling/braces-backport/test.cjs
.github/tooling/jscpd`; the same command accepts either Grafana plugin path.

Replace this backport when an official release incorporates the fix. Before
removing it, rerun the depth, cyclic AST and ordinary expansion regressions,
regenerate all three consumer lockfiles, and verify the security scan.
