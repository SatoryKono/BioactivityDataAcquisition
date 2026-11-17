# Local picomatch security backport

This is a private BioETL build, **not an upstream release**. Version
`4.0.8-bioetl.2` identifies modified code based on upstream `4.0.7`.
It addresses GHSA-fc5q-39xc-vjpf / CVE-2026-112366 with the proposed upstream
fix from https://github.com/micromatch/picomatch/pull/194 at commit
`7be3276fb8bd215a8c73fa066bcaf696c244ad88` in `maximilliangrand/picomatch`
(`hasMixedWildcards` single-branch ReDoS guard in `lib/parse.js`).

The archive contains the JavaScript implementation and MIT license from upstream
`4.0.7` plus that guard. `provenance.json` pins each packaged file hash.
The local amendment also rejects a top-level unbounded wildcard in every repeated
extglob branch, including `+(*)` and `+(*a)`. The upstream mixed-wildcard
guard alone leaves these inputs vulnerable. Package metadata uses a private
version and description.
As with braces-backport, the third-party implementation is shipped only in the
archive, avoiding a second installed source tree. Each archived source file is
bound by provenance hashes; the local amendment is retained in
`single-branch-wildcard.patch`. Regression tests unpack and execute the actual
archive. The tarball is built with `npm pack`. Architecture tests bind consumer lockfiles
to the archive integrity. **No OSV advisory is ignored or suppressed.**

Replace this backport when an official release incorporates the fix
(`first_patched_version` / npm `>4.0.7`). Before removing it, regenerate the
jscpd and Grafana plugin lockfiles and verify the Class-lane OSV gate.
