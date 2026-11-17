# Local picomatch security backport

This is a private BioETL build, **not an upstream release**. Version
`4.0.8-bioetl.4` identifies modified code based on upstream `4.0.7`.

It addresses GHSA-fc5q-39xc-vjpf / CVE-2026-112366:

1. Base guard from micromatch/picomatch#194
   (`7be3276fb8bd215a8c73fa066bcaf696c244ad88`).
2. `hasUnboundedWildcard`: top-level `*` in repeated `+(...)` / `*(...)`
   (closes `+(*)` / `+(*a)`).
3. `hasNestedRiskyExtglob`: nested extglob bodies — unbounded wildcards
   (`+(@(*a))`) and ambiguous alternations with shared prefixes
   (`+(@(a|aa))` / `*(@(a|aa))`).

Third-party sources ship **only** in the npm archive (braces layout).
`provenance.json` pins packaged file hashes. Regression tests unpack the
archive and run timed ReDoS probes (including 48-char ambiguous inputs).
**No OSV advisory is ignored or suppressed.**

Replace when an official release closes these cases. Before removing,
regenerate jscpd/Grafana lockfiles and verify the Class-lane OSV gate.
