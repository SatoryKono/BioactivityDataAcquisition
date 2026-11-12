# Adaptive table build

Run these commands from `grafana/plugins/bioetl-selectorshell-panel`:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run test:ci
npm run typecheck
npm exec -- webpack -c ./webpack.adaptive.config.ts --env production
```

The adaptive entry point is `src/adaptive-module.ts`; its output is
`dist-adaptive`. The existing `npm run build` command builds the selector shell
in `dist`.

`adaptive-build-provenance.ts` records SHA-256 hashes of every build input after
normalizing CRLF to LF, checks that inputs did not change during compilation,
and records hashes of the emitted files in `dist-adaptive/build-provenance.json`.
Keep that receipt with the bundle. The initial recovery reproduced all seven
original output files byte for byte. Subsequent source fixes require a fresh
build and receipt; retain the previous receipt as the historical reference.

Unit tests cover the adaptive table and the existing selector shell. These
checks establish build reproducibility and component contracts; browser render
and operator acceptance are separate checks.
