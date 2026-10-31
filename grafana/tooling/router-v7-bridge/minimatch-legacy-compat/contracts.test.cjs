"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { createRequire } = require("node:module");
const { pathToFileURL } = require("node:url");
const { spawnSync } = require("node:child_process");
const { test } = require("node:test");

const project = createRequire(path.resolve(process.cwd(), "package.json"));
const fixed = project("minimatch-fixed");
const candidate = process.env.BIOETL_MINIMATCH_CONTROL_MODULE
  ? require(process.env.BIOETL_MINIMATCH_CONTROL_MODULE)
  : project("minimatch");
const { glob, globStream, globSync } = process.env.BIOETL_GLOB_CONTROL_MODULE
  ? require(process.env.BIOETL_GLOB_CONTROL_MODULE)
  : project("glob");

test("private packed artifact matches canonical source and installed entry point", () => {
  const metadata = JSON.parse(
    fs.readFileSync(path.join(__dirname, "package.json")),
  );
  const archive = path.join(
    __dirname,
    `${metadata.name}-${metadata.version}.tgz`,
  );
  const members = ["README.md", "index.cjs", "index.d.ts", "package.json"];
  const listing = spawnSync("tar", ["-tf", archive], { encoding: "utf8" });
  assert.equal(listing.status, 0, listing.stderr);
  assert.deepEqual(
    listing.stdout.trim().split(/\r?\n/).sort(),
    members.map((name) => `package/${name}`).sort(),
  );
  for (const name of members) {
    const extracted = spawnSync("tar", ["-xOf", archive, `package/${name}`]);
    assert.equal(extracted.status, 0, extracted.stderr.toString());
    assert.deepEqual(
      extracted.stdout,
      fs.readFileSync(path.join(__dirname, name)),
    );
  }
  assert.deepEqual(
    fs.readFileSync(project.resolve("minimatch")),
    fs.readFileSync(path.join(__dirname, "index.cjs")),
  );
});

test("callable CommonJS and named ESM exports use the actual fixed matcher", async () => {
  assert.equal(typeof candidate, "function");
  assert.equal(candidate, fixed.minimatch);
  assert.equal(candidate.Minimatch, fixed.Minimatch);
  const named = await import(pathToFileURL(project.resolve("minimatch")).href);
  assert.equal(named.minimatch, fixed.minimatch);
  assert.equal(named.Minimatch, fixed.Minimatch);
});

test("existing ESLint and webpack matching contracts remain usable", () => {
  for (const [file, pattern, options, expected] of [
    ["src/a.ts", "src/**/*.ts", {}, true],
    ["src/a.js", "src/**/*.ts", {}, false],
    [".hidden", "*", {}, false],
    [".hidden", "*", { dot: true }, true],
    ["src/A.TS", "**/*.ts", { nocase: true }, true],
    ["src/a.ts", "*.ts", { matchBase: true }, true],
    ["src/a.ts", "!**/*.js", {}, true],
    ["a.ts", "#comment", {}, false],
  ]) {
    assert.equal(candidate(file, pattern, options), expected);
    assert.equal(
      new candidate.Minimatch(pattern, options).match(file),
      expected,
    );
  }
  assert.deepEqual(["a.js", "a.ts"].filter(candidate.filter("*.ts")), ["a.ts"]);
  assert.deepEqual(candidate.match(["a.js", "a.ts"], "*.ts"), ["a.ts"]);
  assert.deepEqual(candidate.braceExpand("a{b,c}.ts"), ["ab.ts", "ac.ts"]);
  assert.equal(candidate.defaults({ nocase: true })("A.TS", "*.ts"), true);
  assert.equal(
    new (candidate.defaults({ dot: true }).Minimatch)("*").match(".a"),
    true,
  );
});

test("globparts amplification respects the explicit upstream expansion cap", () => {
  for (const size of [4, 8, 12]) {
    const pattern =
      "root/" +
      Array.from({ length: size }, (_, i) => `**/../a${i}/b${i}/`).join("") +
      "src/*.ts";
    const matcher = new candidate.Minimatch(pattern, {
      optimizationLevel: 2,
      braceExpandMax: 8,
    });
    assert.ok(
      matcher.globParts.length <= 8,
      `amplified globparts: size=${size}, rows=${matcher.globParts.length}`,
    );
    assert.equal(typeof matcher.match("src/a.ts"), "boolean");
  }
});

function syntheticTree() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "bioetl-glob-control-"));
  for (const a of ["a", "b", "c"]) {
    for (const b of ["x", "y", "z"]) {
      const directory = path.join(root, a, b);
      fs.mkdirSync(directory, { recursive: true });
      fs.writeFileSync(path.join(directory, "fixture.ts"), "synthetic\n");
    }
  }
  return root;
}

function removeSyntheticTree(root) {
  assert.equal(path.dirname(root), path.resolve(os.tmpdir()));
  assert.ok(path.basename(root).startsWith("bioetl-glob-control-"));
  fs.rmSync(root, { recursive: true });
}

test("glob14 reads the complete synthetic fixture through sync and async APIs", async () => {
  const root = syntheticTree();
  try {
    const expected = globSync("**/*.ts", { cwd: root }).sort();
    assert.equal(expected.length, 9);
    assert.deepEqual((await glob("**/*.ts", { cwd: root })).sort(), expected);
  } finally {
    removeSyntheticTree(root);
  }
});

for (const mode of ["promise", "stream"]) {
  for (const trigger of ["timeout", "cancellation"]) {
    test(`glob14 ${mode} stops filesystem traversal after ${trigger}`, async () => {
      const root = syntheticTree();
      const controller = new AbortController();
      const reason = new Error("synthetic glob cancellation");
      const timed = trigger === "timeout";
      let deadline;
      let reads = 0;
      let completeFirstRead;
      const firstReadCompleted = new Promise((resolve) => {
        completeFirstRead = resolve;
      });
      const instrumented = {
        ...fs,
        readdir(...args) {
          reads++;
          const readNumber = reads;
          const callback = args.pop();
          if (timed) {
            if (readNumber === 1) {
              deadline = AbortSignal.timeout(10);
              deadline.addEventListener(
                "abort", () => controller.abort(deadline.reason), { once: true },
              );
            }
            return fs.readdir(...args, (...result) => {
              setTimeout(() => {
                callback(...result);
                if (readNumber === 1) completeFirstRead();
              }, 30);
            });
          }
          if (reads === 1) controller.abort(reason);
          return fs.readdir(...args, (...result) => {
            callback(...result);
            if (readNumber === 1) completeFirstRead();
          });
        },
      };
      try {
        const options = {
          cwd: root,
          fs: instrumented,
          signal: controller.signal,
        };
        const run = async () => {
          if (mode === "promise") await glob("**/*", options);
          else
            for await (const entry of globStream("**/*", options)) void entry;
        };
        await assert.rejects(
          run(),
          timed ? { name: "TimeoutError" } : /synthetic glob cancellation/,
        );
        if (timed) assert.equal(deadline.aborted, true, "real deadline did not fire");
        await firstReadCompleted;
        await new Promise((resolve) => setImmediate(resolve));
        assert.equal(reads, 1, "filesystem work continued after rejection");
      } finally {
        removeSyntheticTree(root);
      }
    });
  }
}
