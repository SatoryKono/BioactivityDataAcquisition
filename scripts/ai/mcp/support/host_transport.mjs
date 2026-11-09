// Optional machine-local routing for portable MCP wrappers. No provider fallback here.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {pathToFileURL} from 'node:url';

export const UNMANAGED = 78;
const names = new Set(['context7', 'brave-search', 'ast-grep']);
function normalized(value) {
    const pathValue = process.platform === 'win32' ? value.replaceAll('\\', '/').toLowerCase() : value;
    return pathValue.replace(/\/$/, '');
}

export function nativePath(value, platform = process.platform) {
    if (platform !== 'win32' && /^[A-Za-z]:[\\/]/.test(value))
        return `/mnt/${value[0].toLowerCase()}/${value.slice(3).replaceAll('\\', '/')}`;
    return value;
}

function exists(value) {
    try {
        fs.lstatSync(value);
        return true;
    } catch (error) {
        if (error.code === 'ENOENT') return false;
        throw error;
    }
}

function readPolicyFile(marker) {
    const data = JSON.parse(fs.readFileSync(marker, 'utf8').replace(/^\uFEFF/, ''));
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new TypeError('Invalid host route policy');
    if (Object.hasOwn(data, 'source')) {
        if (typeof data.source !== 'string' || !data.source) throw new Error('Invalid host route source');
    } else if (!Array.isArray(data.workspaces)) {
        throw new TypeError('Invalid workspace route list');
    }
    return data;
}

export function readPolicy(marker, explicit = false) {
    marker = nativePath(marker);
    if (!exists(marker)) {
        if (explicit) throw new Error('Configured host route file is missing');
        return null;
    }
    const seen = new Set();
    for (let depth = 0; depth < 3; depth++) {
        const identity = fs.realpathSync(marker);
        if (seen.has(identity)) throw new Error('Host route indirection cycle');
        seen.add(identity);
        const data = readPolicyFile(marker);
        if (!Object.hasOwn(data, 'source')) return data;
        const next = nativePath(data.source);
        marker = path.isAbsolute(next) ? next : path.resolve(path.dirname(marker), next);
    }
    throw new Error('Too many host route indirections');
}

export function gitCommonDirectory(root) {
    const marker = path.join(root, '.git');
    if (!exists(marker) || fs.lstatSync(marker).isSymbolicLink()) return null;
    if (fs.statSync(marker).isDirectory()) return fs.realpathSync(marker);
    const text = fs.readFileSync(marker, 'utf8').replace(/^\uFEFF/, '').trim();
    if (!text.startsWith('gitdir: ')) return null;
    const gitdir = path.resolve(root, nativePath(text.slice(8).trim()));
    const commonFile = path.join(gitdir, 'commondir'), backlinkFile = path.join(gitdir, 'gitdir');
    if (!exists(commonFile) || !exists(backlinkFile)) return null;
    const backlink = path.resolve(gitdir, nativePath(fs.readFileSync(backlinkFile, 'utf8').trim()));
    if (normalized(fs.realpathSync(backlink)) !== normalized(fs.realpathSync(marker))) return null;
    return fs.realpathSync(path.resolve(gitdir, nativePath(fs.readFileSync(commonFile, 'utf8').trim())));
}

function matches(root, scope) {
    if (!Array.isArray(scope.roots || []) || !Array.isArray(scope.patterns || [])) throw new Error('Invalid route scope');
    if ([...(scope.roots || []), ...(scope.patterns || [])].some(x => typeof x !== 'string')) throw new Error('Invalid route path');
    if ((scope.roots || []).some(value => normalized(nativePath(value)) === root)) return true;
    return (scope.patterns || []).some(value => {
        const escaped = normalized(nativePath(value)).split('*').map(part => part.replace(/[.*+?^${}()|[\]\\]/g, String.raw`\$&`)).join('.*');
        return new RegExp(`^${escaped}$`).test(root);
    });
}

function validateEntry(entry) {
    if (!entry || typeof entry.command !== 'string' || !entry.command.trim() || !Array.isArray(entry.args) ||
        !entry.args.every(value => typeof value === 'string') ||
        (entry.type !== undefined && entry.type !== 'stdio') ||
        ['env', 'headers', 'url'].some(key => Object.hasOwn(entry, key)) || entry.disabled || entry.enabled === false)
        throw new Error('Invalid or disabled managed stdio route');
    return {command: entry.command, args: [...entry.args]};
}

export function selectRoute(data, root, name, commonDirectory = gitCommonDirectory) {
    if (!names.has(name)) throw new Error('Unsupported routed server');
    let selected = null, managed = false;
    for (const scope of data.workspaces) {
        if (!scope || !matches(normalized(root), scope)) continue;
        managed = true;
        if (scope.git_common_dir) {
            const actual = commonDirectory(root);
            const expected = fs.realpathSync(nativePath(scope.git_common_dir));
            if (!actual || normalized(actual) !== normalized(expected)) throw new Error('Managed workspace Git identity mismatch');
        }
        if (!scope.entries || typeof scope.entries !== 'object') throw new Error('Invalid managed route entries');
        if (!Object.hasOwn(scope.entries, name)) continue;
        const entry = scope.entries[name];
        selected = validateEntry(entry);
        selected.args = selected.args.map(value => value === '{workspace_root}' ? root : value);
    }
    // Old route policies predate optional ast-grep routing; explicit entries still fail closed.
    if (managed && !selected && name !== 'ast-grep') throw new Error('Managed workspace has no route for the requested server');
    return selected;
}

export async function dispatch({root, name, extra = [], marker, explicit, validateOnly = false}) {
    const policy = readPolicy(marker, explicit);
    if (!policy) return UNMANAGED;
    const resolved = fs.realpathSync(root);
    const requested = normalized(path.resolve(root));
    const physical = normalized(resolved);
    if (physical !== requested && policy.workspaces.some(scope =>
        scope && (matches(physical, scope) || matches(requested, scope)))) {
        throw new Error('Managed workspace uses a reparse path');
    }
    const entry = selectRoute(policy, resolved, name);
    if (!entry) return UNMANAGED;
    if (extra.length) throw new Error('Extra arguments are unsupported by the fixed managed route');
    if (validateOnly) {
        process.stdout.write(`[OK] ${name} host route validation completed\n`);
        return 0;
    }
    return new Promise(resolve => {
        const child = spawn(entry.command, entry.args, {stdio: 'inherit', windowsHide: true});
        const terminate = () => child.kill('SIGTERM');
        const interrupt = () => child.kill('SIGINT');
        process.once('SIGTERM', terminate); process.once('SIGINT', interrupt);
        let finished = false;
        const finish = code => {
            if (finished) return;
            finished = true;
            process.off('SIGTERM', terminate); process.off('SIGINT', interrupt);
            // A managed adapter must never return the wrapper's permission to use legacy fallback.
            resolve(Number.isInteger(code) && code !== UNMANAGED ? code : 1);
        };
        child.on('error', () => finish(1));
        child.on('exit', code => finish(code));
    });
}

async function main() {
    const args = process.argv.slice(2);
    if (args[0] !== '--root' || args[2] !== '--server' || args[4] !== '--' || !args[1] || !names.has(args[3]))
        throw new Error('Invalid host transport invocation');
    const configured = process.env.PC_AGENT_MCP_ROUTES_FILE;
    return dispatch({root: args[1], name: args[3], extra: args.slice(5),
        marker: configured || path.join(os.homedir(), '.config', 'pc-agent', 'mcp-routes.json'),
        explicit: Boolean(configured), validateOnly: process.env.BIOETL_MCP_VALIDATE_ONLY === '1'});
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
    try { process.exitCode = await main(); }
    catch { process.stderr.write('Managed MCP route failed; no provider fallback started.\n'); process.exitCode = 1; }
}
