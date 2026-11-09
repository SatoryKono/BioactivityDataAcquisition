/**
 * Optional post-policy GitHub transport. The shell wrapper first resolves repo
 * env, validates credentials, mandatory exclusions, access mode and approved SHA.
 * This helper reads a machine-local github-project-route.json (or an explicit
 * PC_AGENT_GITHUB_PROJECT_ROUTES marker). It accepts at most three source hops.
 * Policy: {version:1, workspaces:[{roots,patterns,git_common_dir:{windows,wsl}}],
 * runtimes:{windows:{command,args},wsl:{command,args}}}. No secrets belong there.
 * The resolved provider payload is sent only in a filtered child environment;
 * WSL uses Windows interop so local bearer/DPAPI data never leave Windows.
 * Exit 78 permits the original native route only if no policy/scope applies.
 * A managed child failure, including child exit 78, never permits fallback.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawn, spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

export const UNMANAGED = 78;
const WSLPATH_CANDIDATES = ['/usr/bin/wslpath', '/bin/wslpath'];
const PROVIDER_ENV_KEYS = [
  'GITHUB_PERSONAL_ACCESS_TOKEN',
  'GITHUB_HOST',
  'HTTP_PROXY',
  'HTTPS_PROXY',
  'NO_PROXY',
  'SSL_CERT_FILE',
  'SSL_CERT_DIR',
];
const CHILD_ENV_ALLOWLIST = new Set([
  'PATH',
  'HOME',
  'USERPROFILE',
  'SYSTEMROOT',
  'WINDIR',
  'TEMP',
  'TMP',
  'TMPDIR',
  'APPDATA',
  'LOCALAPPDATA',
  'COMSPEC',
  'PATHEXT',
  'LANG',
  'LC_ALL',
  'WSL_INTEROP',
  'WSL_DISTRO_NAME',
]);

const normalized = (value) =>
  value.replaceAll('\\', '/').replace(/\/$/, '').toLowerCase();

function exists(candidate) {
  try {
    return fs.statSync(candidate).isFile();
  } catch (error) {
    if (error.code === 'ENOENT') {
      return false;
    }
    throw error;
  }
}

function resolveFixedBinary(name, candidates) {
  for (const candidate of candidates) {
    if (exists(candidate)) {
      return candidate;
    }
  }
  throw new Error(`${name} binary missing from fixed paths`);
}

function nativePath(raw) {
  if (process.platform === 'win32') {
    const mounted =
      raw.match(/^\/mnt\/([a-z])\/(.*)$/i) || raw.match(/^\/([a-z])\/(.*)$/i);
    if (mounted) {
      return `${mounted[1].toUpperCase()}:/${mounted[2]}`;
    }
    return raw;
  }
  const windows = raw.match(/^([a-z]):[\\/](.*)$/i);
  if (windows) {
    return `/mnt/${windows[1].toLowerCase()}/${windows[2].replaceAll('\\', '/')}`;
  }
  return raw;
}

function policyFile(marker, explicit) {
  if (!exists(marker)) {
    if (explicit) {
      throw new Error('Explicit route marker missing');
    }
    return null;
  }
  const seen = new Set();
  let current = marker;
  for (let index = 0; index < 3; index += 1) {
    const actual = fs.realpathSync(current);
    if (seen.has(actual)) {
      throw new Error('Route indirection cycle');
    }
    seen.add(actual);
    const data = JSON.parse(fs.readFileSync(current, 'utf8').replace(/^\uFEFF/, ''));
    if (data.source) {
      current = path.resolve(path.dirname(current), nativePath(data.source));
      continue;
    }
    if (data.version !== 1 || !Array.isArray(data.workspaces)) {
      throw new Error('Unknown route schema');
    }
    return data;
  }
  throw new Error('Too many route indirections');
}

function commonDirectory(root) {
  const marker = path.join(root, '.git');
  if (fs.lstatSync(marker).isSymbolicLink()) {
    throw new Error('Linked Git marker');
  }
  if (fs.statSync(marker).isDirectory()) {
    return fs.realpathSync(marker);
  }
  const text = fs.readFileSync(marker, 'utf8').trim();
  if (!text.startsWith('gitdir: ')) {
    throw new Error('Invalid Git marker');
  }
  const gitdir = path.resolve(root, nativePath(text.slice(8).trim()));
  const backlink = nativePath(
    fs.readFileSync(path.join(gitdir, 'gitdir'), 'utf8').trim(),
  );
  if (
    normalized(fs.realpathSync(backlink)) !==
    normalized(fs.realpathSync(marker))
  ) {
    throw new Error('Git backlink mismatch');
  }
  const common = nativePath(
    fs.readFileSync(path.join(gitdir, 'commondir'), 'utf8').trim(),
  );
  return fs.realpathSync(path.resolve(gitdir, common));
}

function patternMatches(root, rawPattern) {
  const escaped = normalized(rawPattern)
    .split('*')
    .map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, String.raw`\$&`))
    .join('.*');
  return new RegExp(`^${escaped}$`).test(normalized(root));
}

function matches(root, scope) {
  const choices = [...(scope.roots || [])];
  if (choices.some((item) => typeof item !== 'string')) {
    throw new Error('Invalid roots');
  }
  if (choices.some((item) => normalized(item) === normalized(root))) {
    return true;
  }
  return (scope.patterns || []).some((raw) => patternMatches(root, raw));
}

function windowsPath(value) {
  if (process.platform === 'win32') {
    return path.resolve(value);
  }
  if (!process.env.WSL_INTEROP) {
    throw new Error('Windows project profile requires WSL interop');
  }
  const wslpath = resolveFixedBinary('wslpath', WSLPATH_CANDIDATES);
  const converted = spawnSync(wslpath, ['-w', value], {encoding: 'utf8'});
  if (converted.status !== 0) {
    throw new Error('Path conversion failed');
  }
  return converted.stdout.trim();
}

function resolveManagedCommand(command) {
  if (!path.isAbsolute(command)) {
    throw new Error('Managed runtime command must be an absolute path');
  }
  if (!exists(command)) {
    throw new Error('Managed runtime command missing');
  }
  return command;
}

function collectProviderEnv(convertPath) {
  const env = {};
  for (const key of PROVIDER_ENV_KEYS) {
    const value = process.env[key] ?? process.env[key.toLowerCase()];
    if (value) {
      env[key] = value;
    }
  }
  for (const key of ['SSL_CERT_FILE', 'SSL_CERT_DIR']) {
    if (env[key] && path.isAbsolute(env[key])) {
      env[key] = convertPath(env[key]);
    }
  }
  return env;
}

function resolvePhysicalBinary(binary) {
  let physicalBinary = nativePath(binary);
  // Git Bash may resolve an .exe command without returning its extension.
  if (!exists(physicalBinary) && exists(`${physicalBinary}.exe`)) {
    physicalBinary += '.exe';
  }
  return physicalBinary;
}

function readManagedRuntime(policy, platform) {
  const route = policy.runtimes?.[platform];
  if (
    !route ||
    typeof route.command !== 'string' ||
    !Array.isArray(route.args) ||
    !route.args.every((item) => typeof item === 'string')
  ) {
    throw new Error('No managed runtime');
  }
  return route;
}

function assertGitIdentity(scope, actual, platform) {
  const expected = scope.git_common_dir?.[platform];
  if (!expected) {
    throw new Error('Project Git identity mismatch');
  }
  const expectedCommon = fs.realpathSync(nativePath(expected));
  if (normalized(commonDirectory(actual)) !== normalized(expectedCommon)) {
    throw new Error('Project Git identity mismatch');
  }
}

function buildChildEnv(payload) {
  const childEnv = Object.fromEntries(
    Object.entries(process.env).filter(([key]) =>
      CHILD_ENV_ALLOWLIST.has(key.toUpperCase()),
    ),
  );
  childEnv.PC_AGENT_GITHUB_PROJECT_PAYLOAD = JSON.stringify(payload);
  if (process.platform !== 'win32') {
    childEnv.WSLENV = 'PC_AGENT_GITHUB_PROJECT_PAYLOAD';
  }
  return childEnv;
}

function spawnManaged(route, childEnv) {
  const managedCommand = resolveManagedCommand(route.command);
  return new Promise((resolve) => {
    const child = spawn(managedCommand, route.args, {
      env: childEnv,
      stdio: 'inherit',
      windowsHide: true,
    });
    const finish = (code) =>
      resolve(Number.isInteger(code) && code !== UNMANAGED ? code : 1);
    child.on('error', () => finish(1));
    child.on('exit', finish);
    process.once('SIGTERM', () => child.kill('SIGTERM'));
    process.once('SIGINT', () => child.kill('SIGINT'));
  });
}

export async function dispatch({
  root,
  binary,
  args,
  approved = '',
  marker,
  explicit = false,
  convertPath = windowsPath,
}) {
  const policy = policyFile(marker, explicit);
  if (!policy) {
    return UNMANAGED;
  }
  const logical = path.resolve(root);
  const actual = fs.realpathSync(logical);
  const scope = policy.workspaces.find(
    (workspace) => matches(actual, workspace) || matches(logical, workspace),
  );
  if (!scope) {
    return UNMANAGED;
  }
  if (normalized(actual) !== normalized(logical)) {
    throw new Error('Project reparse path');
  }
  const platform = process.platform === 'win32' ? 'windows' : 'wsl';
  assertGitIdentity(scope, actual, platform);
  const route = readManagedRuntime(policy, platform);
  const physicalBinary = resolvePhysicalBinary(binary);
  const payload = {
    root: convertPath(actual),
    binary: convertPath(physicalBinary),
    args,
    approved_sha256: approved,
    env: collectProviderEnv(convertPath),
    cwd: convertPath(process.cwd()),
  };
  return spawnManaged(route, buildChildEnv(payload));
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href
) {
  try {
    const argv = process.argv.slice(2);
    const split = argv.indexOf('--');
    if (
      argv[0] !== '--root' ||
      argv[2] !== '--binary' ||
      argv[4] !== '--approved-sha' ||
      split !== 6
    ) {
      throw new Error('Invalid project transport invocation');
    }
    const configured = process.env.PC_AGENT_GITHUB_PROJECT_ROUTES;
    process.exitCode = await dispatch({
      root: argv[1],
      binary: argv[3],
      approved: argv[5] === '-' ? '' : argv[5],
      args: argv.slice(split + 1),
      marker:
        configured ||
        path.join(os.homedir(), '.config', 'pc-agent', 'github-project-route.json'),
      explicit: Boolean(configured),
    });
  } catch {
    process.stderr.write(
      'Managed project GitHub transport refused; no credential printed or native fallback.\n',
    );
    process.exitCode = 1;
  }
}
