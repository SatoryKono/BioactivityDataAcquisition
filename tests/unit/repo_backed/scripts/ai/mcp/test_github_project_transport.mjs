import assert from 'node:assert/strict';
import {test} from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';

const helper=process.env.BIOETL_TEST_GITHUB_HELPER||fileURLToPath(new URL('../../../../../../scripts/ai/mcp/support/github_project_transport.mjs',import.meta.url));
const {dispatch,UNMANAGED}=await import(pathToFileURL(helper));
const repo=process.env.BIOETL_TEST_REPO_ROOT||fileURLToPath(new URL('../../../../../../',import.meta.url));
const gitCandidates=['/usr/bin/git','/bin/git','C:/Program Files/Git/cmd/git.exe','C:/Program Files/Git/bin/git.exe'];
const gitBinary=gitCandidates.find(candidate=>{try{return fs.statSync(candidate).isFile();}catch{return false;}});
assert.ok(gitBinary,'Git binary must be available on a fixed path');
const commonResult=spawnSync(gitBinary,['--no-optional-locks','rev-parse','--git-common-dir'],{cwd:repo,encoding:'utf8',windowsHide:true});
assert.equal(commonResult.status,0,'Source checkout Git identity must be available');
const common=fs.realpathSync(path.resolve(repo,commonResult.stdout.trim()));
const keys=['GITHUB_PERSONAL_ACCESS_TOKEN','GITHUB_HOST','HTTP_PROXY','HTTPS_PROXY','NO_PROXY','SSL_CERT_FILE','SSL_CERT_DIR','OTHER_SECRET'];
const envKeys=[...keys,...keys.map(x=>x.toLowerCase())];
const oldEnv=Object.fromEntries(envKeys.map(k=>[k,process.env[k]]));
test.beforeEach(()=>{for(const key of envKeys)delete process.env[key];process.env.GITHUB_PERSONAL_ACCESS_TOKEN='ghp_OFFLINE_PROTOCOL_FIXTURE_123456';process.env.OTHER_SECRET='OFFLINE_UNRELATED';});
test.afterEach(()=>{for(const key of envKeys){if(oldEnv[key]===undefined)delete process.env[key];else process.env[key]=oldEnv[key];}});

function fixture(t,code=0){
    const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'bioetl-github-transport-'));
    const marker=path.join(tmp,'route.json'),capture=path.join(tmp,'capture.json'),child=path.join(tmp,'capture.mjs');
    fs.writeFileSync(child,"import fs from 'node:fs';fs.writeFileSync(process.argv[2],JSON.stringify({payload:JSON.parse(process.env.PC_AGENT_GITHUB_PROJECT_PAYLOAD),other:!!process.env.OTHER_SECRET}));process.exit(Number(process.argv[3]));");
    const route={command:process.execPath,args:[child,capture,String(code)]};
    const policy={version:1,workspaces:[{roots:[repo],git_common_dir:{windows:common,wsl:common}}],runtimes:{windows:route,wsl:route}};
    fs.writeFileSync(marker,JSON.stringify(policy));
    const options={root:repo,binary:process.execPath,args:['stdio'],marker,explicit:true,convertPath:x=>path.resolve(x)};
    t.after(()=>{const resolved=fs.realpathSync(tmp);assert.equal(path.dirname(resolved),fs.realpathSync(os.tmpdir()));fs.rmSync(resolved,{recursive:true});});
    return {tmp,marker,capture,policy,options};
}

test('missing default marker keeps the original unmanaged route',async t=>{
    const f=fixture(t);assert.equal(await dispatch({...f.options,marker:path.join(f.tmp,'missing'),explicit:false}),UNMANAGED);
});
test('missing explicit marker fails closed',async t=>{
    const f=fixture(t);await assert.rejects(dispatch({...f.options,marker:path.join(f.tmp,'missing')}));
});
test('invalid policy and source cycle fail closed',async t=>{
    const f=fixture(t);fs.writeFileSync(f.marker,'{');await assert.rejects(dispatch(f.options));
    fs.writeFileSync(f.marker,JSON.stringify({source:f.marker}));await assert.rejects(dispatch(f.options));
});
test('unmanaged scope does not dispatch',async t=>{
    const f=fixture(t);f.policy.workspaces[0].roots=[f.tmp];fs.writeFileSync(f.marker,JSON.stringify(f.policy));
    assert.equal(await dispatch(f.options),UNMANAGED);assert(!fs.existsSync(f.capture));
});
test('symlink checkout outside managed scope stays unmanaged',async t=>{
    const f=fixture(t);
    const linkRoot=path.join(f.tmp,'linked-repo');
    fs.symlinkSync(repo,linkRoot);
    f.policy.workspaces[0].roots=[f.tmp];
    fs.writeFileSync(f.marker,JSON.stringify(f.policy));
    assert.equal(await dispatch({...f.options,root:linkRoot}),UNMANAGED);
    assert(!fs.existsSync(f.capture));
});
test('Git common-directory mismatch refuses the managed route',async t=>{
    const f=fixture(t);f.policy.workspaces[0].git_common_dir={windows:f.tmp,wsl:f.tmp};fs.writeFileSync(f.marker,JSON.stringify(f.policy));
    await assert.rejects(dispatch(f.options));assert(!fs.existsSync(f.capture));
});
test('provider secret uses environment, not argv; unrelated integrations are stripped',async t=>{
    const f=fixture(t);assert.equal(await dispatch(f.options),0);const seen=JSON.parse(fs.readFileSync(f.capture,'utf8'));
    assert.equal(seen.payload.env.GITHUB_PERSONAL_ACCESS_TOKEN,process.env.GITHUB_PERSONAL_ACCESS_TOKEN);assert.equal(seen.other,false);
    assert(!JSON.stringify(f.policy).includes(process.env.GITHUB_PERSONAL_ACCESS_TOKEN));
    assert.deepEqual(seen.payload.args,['stdio']);assert.equal(seen.payload.root,path.resolve(repo));
});
test('managed child exit 78 never grants native fallback',async t=>{
    const f=fixture(t,78);assert.equal(await dispatch(f.options),1);
});
test('Git Bash executable spelling resolves a real exe before handoff',async t=>{
    const f=fixture(t),exe=path.join(f.tmp,'provider.exe');fs.writeFileSync(exe,'OFFLINE_NOT_EXECUTED');
    assert.equal(await dispatch({...f.options,binary:exe.slice(0,-4)}),0);
    assert.equal(JSON.parse(fs.readFileSync(f.capture,'utf8')).payload.binary,exe);
});
