# Callable and named minimatch entry points

This private build-tool adapter exposes the callable CommonJS entry point used
by pinned ESLint/webpack consumers and the named CommonJS/ESM exports used by
current glob/TypeScript consumers. Both delegate to unmodified upstream
minimatch 11.0.3. It contains no legacy matching algorithm and does not promise
the removed minimatch 3 regular-expression-generation API.

The fixed upstream supplies matching, `Minimatch`, defaults, filters, brace
expansion and the globparts amplification correction for
GHSA-g3hv-75wg-m249. The package is not an advisory exclusion or a renamed copy
of vulnerable source. Compatibility and security controls must pass before use.
The actual old-version negative controls reject the advisory transformations;
the fixed matcher enforces its explicit upstream expansion cap. The glob
controls observe real synthetic filesystem reads after promise/stream abort.

The adapter is Apache-2.0; the unmodified upstream dependency retains BlueOak-1.0.0
license. `npm pack --ignore-scripts` produces the private artifact; the contract
checks its source identity and the consumer locks retain the real upstream SRI.
