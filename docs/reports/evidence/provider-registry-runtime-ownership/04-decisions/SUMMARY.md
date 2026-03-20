# Provider Registry Runtime Ownership Decision Summary

## Accepted Decision

- `DEC-provider-registry-runtime-stop-at-named-bootstrap-seam`

## Decision

For RF-07D, the project will stop at the current named runtime bootstrap seam
and will not start explicit runtime `ProviderRegistry` instance threading unless
new caller-driven evidence appears.

## Why

- the hidden runtime dependency has already been reduced behind an explicit seam;
- runtime tests and ratchets now protect that seam;
- explicit instance ownership is clearly valuable in local factory seams, but a
  natural runtime owner is not yet present.

## Reopen Criteria

Reopen RF-07D4 only if at least one of these becomes true:

- a runtime caller naturally owns an isolated `ProviderRegistry` instance;
- the current named seam blocks a real testability or isolation need;
- runtime execution needs multiple independent registry contexts.
