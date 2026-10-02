import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
import * as bridge from './index.mjs';

const args = process.argv.slice(2);
const sourceArg = args.indexOf('--source');
assert.ok(sourceArg >= 0 && args[sourceArg + 1], 'Pass --source <Grafana checkout>');
const root = path.resolve(args[sourceArg + 1]);
const manifest = fs.readFileSync(path.join(root, 'package.json'), 'utf8');
assert.equal(JSON.parse(manifest).version, '13.2.3', 'This candidate targets the inspected Grafana 13.2.3 source');
const sha256 = (text) => createHash('sha256').update(text).digest('hex');
const records = [], imports = [], unsupported = [], dynamic = [];
function scan(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory() && !['node_modules', 'dist', 'build'].includes(entry.name)) scan(file);
    else if (entry.isFile() && /\.(?:tsx?|m?js)$/.test(entry.name)) {
      const text = fs.readFileSync(file, 'utf8');
      if (!text.includes('react-router-dom-v5-compat')) continue;
      const relative = path.relative(root, file).split(path.sep).join('/');
      records.push({ file: relative, sha256: sha256(text) });
      const source = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true);
      function visit(node) {
        if (ts.isImportDeclaration(node) && node.moduleSpecifier.text === 'react-router-dom-v5-compat') {
          const clause = node.importClause;
          if (clause && !clause.isTypeOnly) {
            if (clause.name || (clause.namedBindings && ts.isNamespaceImport(clause.namedBindings))) {
              unsupported.push({ file: relative, reason: 'default or namespace import requires manual review' });
            }
            for (const item of clause.namedBindings?.elements ?? []) {
              if (item.isTypeOnly) continue;
              const symbol = (item.propertyName ?? item.name).text;
              imports.push({ file: relative, symbol });
              if (!(symbol in bridge)) unsupported.push({ file: relative, symbol });
            }
          }
        }
        if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword &&
            node.arguments[0]?.text === 'react-router-dom-v5-compat') dynamic.push(relative);
        ts.forEachChild(node, visit);
      }
      visit(source);
    }
  }
}
scan(path.join(root, 'packages'));
scan(path.join(root, 'public', 'app'));
assert.ok(imports.length > 0, 'No compat imports found: cannot validate an empty source tree');
records.sort((a, b) => a.file.localeCompare(b.file));
const result = {
  grafana_version: '13.2.3', manifest_sha256: sha256(manifest),
  inspected_source_sha256: sha256(JSON.stringify(records)),
  files: records.length, value_imports: imports.length,
  symbols: [...new Set(imports.map((item) => item.symbol))].sort(),
  unsupported, dynamic_imports: [...new Set(dynamic)].sort(), records, imports,
  scope: 'Static compat value imports only. Not a host build, type check, runtime, or security closure receipt.',
};
const outputArg = args.indexOf('--output');
if (outputArg >= 0) fs.writeFileSync(args[outputArg + 1], JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify({ ...result, records: undefined, imports: undefined }));
assert.equal(unsupported.length, 0, 'Unsupported compat imports');
