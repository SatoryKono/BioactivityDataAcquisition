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

The source build also applies `grafana-alert-instance-link.patch`. Its URL
helper replaces the `tab` search parameter without corrupting an existing
`returnTo`, a Grafana subpath or a fragment. The workflow runs the upstream
Instances navigation test before compiling the frontend. Rebuilding this changed
frontend produces a new candidate; the existing image pins and historical
acceptance receipts do not attest this patch and must remain unchanged until the
candidate qualification and promotion procedure below is completed.

Generate the private dependency artifact with
`npm pack --ignore-scripts --pack-destination .`. Plugin manifests consume the
resulting archive as their compat dependency. The upstream Router 7 artifact
remains unchanged; the archive contains this implemented bridge, not renamed
Router 6 code. Rebuild the archive and lockfiles together after bridge changes.
The host and plugin candidates must pass runtime acceptance before rollout.

## Qualifying a changed image delivery

The Router bridge workflow defaults to `declared_delivery`: it retains complete
plugin-file, source-map, host-rootfs and managed-image parity against the shipped
pins. Source revalidation is valid only when the rebuilt delivery is unchanged.
Do not replace old image hashes with output from changed dependencies.

For changed output, an authorized image publisher must first supply separately
published immutable host and managed candidate digests from the committed source.
Dispatch the same workflow at that source with `qualification_target=candidate`,
`candidate_host_image` and `candidate_managed_image`. Both references must use the
owned `satorykono/bioetl-grafana-router7-canvas@sha256:` namespace and differ.
Candidate mode preserves dependency audits, type/lint/behavior tests and the
independent rebuild. It verifies every transferred plugin file, including maps,
complete image configuration/rootfs and trusted base/parent layers. The managed
recipe is a generated copy with only its parent rebound; tracked delivery pins
are not changed by qualification. Image exports use trusted host tools, without
executing binaries supplied by candidate images.

Only successful original candidate CI artifacts may feed
`python -m scripts.ops promote-router-host-release`. Keep the original plugin and
image-receipt artifacts before their seven-day retention expires. Promotion
materializes coupled pins and preserves release history; it does not qualify
default delivery, browser acceptance or runtime admission. Repeat the default
delivery workflow at the resulting head before any authorized rollout. Candidate
qualification neither publishes images nor deploys services. The promotion
command, including `--check`, performs API/Docker operations and writes evidence;
it is not a read-only diagnostic.

## Produce an unqualified image pair before candidate verification

The existing Router 7 bridge candidate workflow also accepts
`qualification_target=produce_candidate`. This mode requires a full
`producer_source_sha` equal to the dispatched ref's `GITHUB_SHA` and checkout
HEAD. Leave both candidate image inputs empty. Use a reviewed, published PR
ref containing this mode; a local preparation commit is not a runnable ref.

All existing dependency, type, lint, behavior and build gates still apply.
The producer builds the local host and managed images from one source tree
and exports their config IDs, build metadata, Docker archives, complete
source-built context and package input hashes in the separate
`router-v7-unqualified-build-products` artifact. It does not push images,
change delivery pins, run image qualification, or grant runtime acceptance.
The receipt state is `BUILT_UNQUALIFIED`; it is not an image parity receipt.

An independently authorized publisher must preserve the original artifact
identity, validate/load both archives and bind actual registry digests to
their config IDs before publication. Then run the existing `candidate` mode
on the same source to compare the published pair against fresh builds.
Only the owning promotion flow may update delivery evidence after successful
qualification. Default `declared_delivery` verification remains unchanged.

Keep original artifacts before retention expires. A failed producer run or
missing/incomplete artifact is not successful image production. Local mock
tests validate boundaries, not real Docker build/load or registry parity.

Source binding checks the workflow, `scripts.ops` facade and shared CLI
dispatcher as well as plugin sources, package/lock files, webpack and bridge
tooling. Only the two plugins' generated `dist/**` trees are excluded from
source diff, untracked-input checks and source tree hashes. Their complete
built files remain captured and hashed separately in the build artifacts.

Absent or empty qualification inputs (including ordinary PR event contexts)
select strict `declared_delivery` checks. Only explicit `candidate` or
`produce_candidate` inputs select their respective special paths. Workflow
conditions and Python input normalization follow the same rule. Unknown
modes fail unconditional input validation before any build or image I/O.

Build metadata is preserved byte for byte. Identity checks prefer an explicit
`containerimage.config.digest`. If absent, the Docker driver's legacy
`containerimage.digest` is accepted only when it equals the independently
inspected built image config ID (or that ID in the authenticated parity
receipt). An explicit conflicting config ID is always rejected; a differing
manifest digest never substitutes for the built config ID.
