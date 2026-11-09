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
import {spawn,spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
export const UNMANAGED=78;
const normalized=x=>x.replaceAll('\\','/').replace(/\/$/,'').toLowerCase();
const exists=p=>{try{return fs.statSync(p).isFile();}catch(e){if(e.code==='ENOENT')return false;throw e;}};
function nativePath(raw){
    if(process.platform==='win32'){
        const mounted=raw.match(/^\/mnt\/([a-z])\/(.*)$/i)||raw.match(/^\/([a-z])\/(.*)$/i);
        return mounted?mounted[1].toUpperCase()+':/'+mounted[2]:raw;
    }
    const windows=raw.match(/^([a-z]):[\\/](.*)$/i);
    return windows?'/mnt/'+windows[1].toLowerCase()+'/'+windows[2].replaceAll('\\','/'):raw;
}
function policyFile(marker,explicit){
    if(!exists(marker)){if(explicit)throw new Error('Explicit route marker missing');return null;}
    const seen=new Set();
    for(let i=0;i<3;i++){
        const actual=fs.realpathSync(marker);if(seen.has(actual))throw new Error('Route indirection cycle');seen.add(actual);
        const data=JSON.parse(fs.readFileSync(marker,'utf8').replace(/^\uFEFF/,''));
        if(data.source){marker=path.resolve(path.dirname(marker),nativePath(data.source));continue;}
        if(data.version!==1||!Array.isArray(data.workspaces))throw new Error('Unknown route schema');return data;
    }throw new Error('Too many route indirections');
}
function commonDirectory(root){
    const marker=path.join(root,'.git');if(fs.lstatSync(marker).isSymbolicLink())throw new Error('Linked Git marker');
    if(fs.statSync(marker).isDirectory())return fs.realpathSync(marker);
    const text=fs.readFileSync(marker,'utf8').trim();if(!text.startsWith('gitdir: '))throw new Error('Invalid Git marker');
    const gitdir=path.resolve(root,nativePath(text.slice(8).trim()));
    if(normalized(fs.realpathSync(nativePath(fs.readFileSync(path.join(gitdir,'gitdir'),'utf8').trim())))!==normalized(fs.realpathSync(marker)))throw new Error('Git backlink mismatch');
    return fs.realpathSync(path.resolve(gitdir,nativePath(fs.readFileSync(path.join(gitdir,'commondir'),'utf8').trim())));
}
function matches(root,scope){
    const choices=[...(scope.roots||[])];if(choices.some(x=>typeof x!=='string'))throw new Error('Invalid roots');
    if(choices.some(x=>normalized(x)===normalized(root)))return true;
    return (scope.patterns||[]).some(raw=>new RegExp('^'+normalized(raw).split('*').map(x=>x.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('.*')+'$').test(normalized(root)));
}
function windowsPath(value){
    if(process.platform==='win32')return path.resolve(value);
    if(!process.env.WSL_INTEROP)throw new Error('Windows project profile requires WSL interop');
    const p=spawnSync('wslpath',['-w',value],{encoding:'utf8'});if(p.status!==0)throw new Error('Path conversion failed');return p.stdout.trim();
}
export async function dispatch({root,binary,args,approved='',marker,explicit=false,convertPath=windowsPath}){
    const policy=policyFile(marker,explicit);if(!policy)return UNMANAGED;
    const actual=fs.realpathSync(root);if(normalized(actual)!==normalized(path.resolve(root)))throw new Error('Project reparse path');
    const scope=policy.workspaces.find(x=>matches(actual,x));if(!scope)return UNMANAGED;
    const platform=process.platform==='win32'?'windows':'wsl',expected=scope.git_common_dir?.[platform];
    if(!expected||normalized(commonDirectory(actual))!==normalized(fs.realpathSync(nativePath(expected))))throw new Error('Project Git identity mismatch');
    const route=policy.runtimes?.[platform];
    if(!route||typeof route.command!=='string'||!Array.isArray(route.args)||!route.args.every(x=>typeof x==='string'))throw new Error('No managed runtime');
    const env={};
    for(const key of ['GITHUB_PERSONAL_ACCESS_TOKEN','GITHUB_HOST','HTTP_PROXY','HTTPS_PROXY','NO_PROXY','SSL_CERT_FILE','SSL_CERT_DIR']){
        const value=process.env[key]??process.env[key.toLowerCase()];if(value)env[key]=value;
    }
    for(const key of ['SSL_CERT_FILE','SSL_CERT_DIR'])if(env[key]&&path.isAbsolute(env[key]))env[key]=convertPath(env[key]);
    // Git Bash may resolve an .exe command without returning its extension.
    let physicalBinary=nativePath(binary);
    if(!exists(physicalBinary)&&exists(physicalBinary+'.exe'))physicalBinary+='.exe';
    const payload={root:convertPath(actual),binary:convertPath(physicalBinary),args,approved_sha256:approved,env,cwd:convertPath(process.cwd())};
    const allowed=new Set(['PATH','HOME','USERPROFILE','SYSTEMROOT','WINDIR','TEMP','TMP','TMPDIR','APPDATA','LOCALAPPDATA','COMSPEC','PATHEXT','LANG','LC_ALL','WSL_INTEROP','WSL_DISTRO_NAME']);
    const childEnv=Object.fromEntries(Object.entries(process.env).filter(([k])=>allowed.has(k.toUpperCase())));
    childEnv.PC_AGENT_GITHUB_PROJECT_PAYLOAD=JSON.stringify(payload);
    if(process.platform!=='win32')childEnv.WSLENV='PC_AGENT_GITHUB_PROJECT_PAYLOAD';
    return new Promise(resolve=>{
        const child=spawn(route.command,route.args,{env:childEnv,stdio:'inherit',windowsHide:true});
        const finish=code=>resolve(Number.isInteger(code)&&code!==UNMANAGED?code:1);
        child.on('error',()=>finish(1));child.on('exit',finish);
        process.once('SIGTERM',()=>child.kill('SIGTERM'));process.once('SIGINT',()=>child.kill('SIGINT'));
    });
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
    try{
        const a=process.argv.slice(2),split=a.indexOf('--');
        if(a[0]!=='--root'||a[2]!=='--binary'||a[4]!=='--approved-sha'||split!==6)throw new Error('Invalid project transport invocation');
        const configured=process.env.PC_AGENT_GITHUB_PROJECT_ROUTES;
        process.exitCode=await dispatch({root:a[1],binary:a[3],approved:a[5]==='-'?'':a[5],args:a.slice(split+1),
            marker:configured||path.join(os.homedir(),'.config','pc-agent','github-project-route.json'),explicit:Boolean(configured)});
    }catch{process.stderr.write('Managed project GitHub transport refused; no credential printed or native fallback.\n');process.exitCode=1;}
}
