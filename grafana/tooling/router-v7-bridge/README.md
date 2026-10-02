# Grafana Router 7 bridge candidate

This private package is an isolated migration candidate for issues #11888 and
#11889. It is not installed in the shipped plugins or the Grafana host.

`CompatRouter` connects legacy v5 history to public Router 7 contexts.
`CompatRoute` preserves legacy Route rendering and supplies a matching Router 7
route context. Public Router 7 exports are re-exported; removed private Router 6
APIs are deliberately not recreated with placeholders. Additional SDK consumers
must be checked before using this as a replacement for the v6 compat package.

`InternalLink` accepts internal route destinations and resolves mixed separators
before constructing the link. The ordinary `Link` export preserves Router 7
support for intentional external URLs.

Run `npm ci --ignore-scripts`, `npm test`, `npm run typecheck`, `npm run build`, and `npm audit --json`
in this directory.
The tests cover shared history, route parameters, exact matching, listener cleanup,
internal navigation, and hydration constructor injection. Passing these checks
does not establish Grafana host compatibility or close either security issue.

The npm alias `react-router-v7` points to the actual upstream `react-router`
7.18.4 artifact; its upstream package name and version remain visible in the lock.
It keeps the v5 peer dependency separate instead of overriding the legacy router.

Before production adoption, build the SDK and host with the candidate, verify all
imported APIs, test actual plugin navigation on an isolated host, and satisfy
exact-SHA CI and source-bound acceptance. Preserve manifests, lockfiles, image
digest, and data backups for rollback. Neither advisory suppression nor reduced
security thresholds is part of this candidate.

To check the static compat imports in an unmodified Grafana 13.2.3 checkout,
run `node verify-host-apis.mjs --source <checkout> --output <receipt.json>`.
The receipt binds the inspected files to their SHA-256 hashes. It checks named
value imports and flags default/namespace imports for review. It does not prove
host compilation, third-party plugin compatibility, or runtime acceptance.
