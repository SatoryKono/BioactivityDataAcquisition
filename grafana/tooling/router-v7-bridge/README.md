# Grafana Router 7 bridge candidate

This private package is an isolated migration candidate for issues #11888 and
#11889. The migration is prepared for plugin builds and an isolated Grafana host; the running shared host still requires rollout.

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
The separate `react-router-dom-v5` alias preserves legacy history contexts without a v5/v7 peer dependency conflict.

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

The Grafana integration patch targets unmodified upstream v13.2.3. Apply it with
`git -c core.autocrlf=false apply --check grafana-v13.2.3.patch`, then apply it
without `--check` inside that upstream checkout. Run `yarn install --immutable`
and the production build with Node 24. The patch also changes the plugin loader
shared router export and removes Router 6 from the upstream lock.

Generate the private dependency artifact with
`npm pack --ignore-scripts --pack-destination .`. Plugin manifests consume the
resulting archive as their compat dependency. The upstream Router 7 artifact
remains unchanged; the archive contains this implemented bridge, not renamed
Router 6 code. Rebuild the archive and lockfiles together after bridge changes.
The host and plugin candidates must pass runtime acceptance before rollout.
