// Portable client hop to the Windows owner; never starts a local provider backend.
import {existsSync} from 'node:fs';
import {spawn} from 'node:child_process';
if (process.argv.slice(2).join(' ') !== 'context7') throw new Error('Unsupported managed service');
const node = process.platform === 'win32' ? 'C:/Program Files/nodejs/node.exe'
    : process.env.WSL_INTEROP ? '/mnt/c/Program Files/nodejs/node.exe' : null;
if (!node || !existsSync(node)) throw new Error('Windows interop unavailable; no fallback backend');
const child = spawn(node, ['D:/pc-agent/tools/shared-mcp/service-adapter.mjs', 'context7'],
    {stdio: 'inherit', windowsHide: true});
child.on('error', () => { process.exitCode = 1; });
child.on('exit', code => { process.exitCode = code ?? 1; });
