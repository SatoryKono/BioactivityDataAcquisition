import assert from 'node:assert/strict';
import {test} from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';

const helper=process.env.BIOETL_TEST_HOST_HELPER || fileURLToPath(new URL('../../../../../../scripts/ai/mcp/support/host_transport.mjs',import.meta.url));
const sourceMcp=process.env.BIOETL_TEST_MCP_DIR || path.dirname(path.dirname(helper));
const route=await import(pathToFileURL(helper));
const fixtures=path.resolve(process.env.BIOETL_TEST_FIXTURES || path.join(os.tmpdir(),'bioetl-host-transport-tests'));
fs.mkdirSync(fixtures,{recursive:true});

function fixture(t){
    const root=fs.mkdtempSync(path.join(fixtures,'case with spaces-'));
    t.after(()=>{
        const resolved=fs.realpathSync(root),base=fs.realpathSync(fixtures);
        assert(resolved.startsWith(base+path.sep));
        fs.rmSync(resolved,{recursive:true});
    });
    return root;
}
function json(file,data){fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(data));}
function policy(root,code=0){return {workspaces:[{roots:[root],entries:{
    context7:{command:process.execPath,args:['-e',`process.stdout.write('PROTOCOL_SENTINEL');process.exitCode=${code}`]},
    'brave-search':{command:process.execPath,args:['-e',`process.stdout.write('PROTOCOL_SENTINEL');process.exitCode=${code}`]},
}}]};}
function invoke(root,marker,extra=[],updates={}){
    const env={...process.env,PC_AGENT_MCP_ROUTES_FILE:marker,BIOETL_MCP_VALIDATE_ONLY:'0',...updates};
    return spawnSync(process.execPath,[helper,'--root',root,'--server','context7','--',...extra],{
        env,encoding:'utf8',windowsHide:true,timeout:15000});
}

test('missing default marker means unmanaged; missing explicit marker fails closed',t=>{
    const root=fixture(t),marker=path.join(root,'missing.json');
    assert.equal(route.readPolicy(marker),null);
    assert.throws(()=>route.readPolicy(marker,true));
    assert.equal(invoke(root,marker).status,1);
});
test('relative policy indirection resolves and cycles are rejected',t=>{
    const root=fixture(t),marker=path.join(root,'marker.json'),target=path.join(root,'policy.json');
    json(marker,{source:'policy.json'});json(target,policy(root));
    assert.equal(route.readPolicy(marker).workspaces.length,1);
    json(target,{source:'marker.json'});assert.throws(()=>route.readPolicy(marker));
});
test('invalid JSON and invalid policy shape fail closed without payload disclosure',t=>{
    const root=fixture(t),marker=path.join(root,'policy.json');
    fs.writeFileSync(marker,'BROKEN_PRIVATE_VALUE');
    const result=invoke(root,marker);assert.equal(result.status,1);assert(!result.stderr.includes('PRIVATE_VALUE'));assert.equal(result.stdout,'');
    json(marker,[]);assert.throws(()=>route.readPolicy(marker));
});
test('scope filtering, patterns and fixed Git identity are enforced',t=>{
    const root=fixture(t),common=path.join(root,'common');fs.mkdirSync(common);
    const data=policy(root);data.workspaces[0].git_common_dir=common;
    assert(route.selectRoute(data,root,'context7',()=>common));
    assert.throws(()=>route.selectRoute(data,root,'context7',()=>null));
    assert.throws(()=>route.selectRoute(data,root,'context7',()=>root));
    assert.equal(route.selectRoute(data,path.join(root,'other'),'context7',()=>common),null);
    data.workspaces[0].roots=[];data.workspaces[0].patterns=[root+'/*'];
    assert(route.selectRoute(data,path.join(root,'child'),'context7',()=>common));
    assert.equal(route.gitCommonDirectory(root),null);
});
test('workspace route matching follows platform case semantics',()=>{
    const data=policy('/workspace/Approved');
    assert(route.selectRoute(data,'/workspace/Approved','context7'));
    const other=route.selectRoute(data,'/workspace/approved','context7');
    if(process.platform==='win32') assert(other);
    else assert.equal(other,null);
});
test('Windows policy paths map only when a non-Windows client needs them',()=>{
    assert.equal(route.nativePath(String.raw`D:\host\routes.json`,'linux'),'/mnt/d/host/routes.json');
    assert.equal(route.nativePath(String.raw`D:\host\routes.json`,'win32'),String.raw`D:\host\routes.json`);
});
test('credential-bearing, remote, disabled and malformed entries are rejected',t=>{
    const root=fixture(t);
    for(const update of [{env:{}},{headers:{}},{url:'http://example.org'},{disabled:true},{enabled:false},{args:'bad'},{command:''},{type:'http'}]){
        const data=policy(root);Object.assign(data.workspaces[0].entries.context7,update);
        assert.throws(()=>route.selectRoute(data,root,'context7'));
    }
    const missing=policy(root);missing.workspaces[0].entries={};
    assert.throws(()=>route.selectRoute(missing,root,'context7'));
});
test('managed dispatch preserves stdout and never treats child code 78 as fallback',t=>{
    const root=fixture(t),marker=path.join(root,'policy.json');
    json(marker,policy(root));const first=invoke(root,marker);assert.equal(first.status,0);assert.equal(first.stdout,'PROTOCOL_SENTINEL');assert.equal(first.stderr,'');
    json(marker,policy(root,78));assert.equal(invoke(root,marker).status,1);
    json(marker,policy(root,9));assert.equal(invoke(root,marker).status,9);
});
test('missing adapter, extra arguments and validate-only never start legacy code',t=>{
    const root=fixture(t),marker=path.join(root,'policy.json');
    const data=policy(root);data.workspaces[0].entries.context7.command=path.join(root,'missing-command');json(marker,data);
    assert.equal(invoke(root,marker).status,1);
    json(marker,policy(root));const extra=invoke(root,marker,['--other']);assert.equal(extra.status,1);assert.equal(extra.stdout,'');
    const validation=invoke(root,marker,[],{BIOETL_MCP_VALIDATE_ONLY:'1'});
    assert.equal(validation.status,0);assert.match(validation.stdout,/validation completed/);assert(!validation.stdout.includes('PROTOCOL_SENTINEL'));
});

const ps=process.env.BIOETL_TEST_POWERSHELL || (process.platform==='win32'?'powershell.exe':'pwsh');
const bash=process.env.BIOETL_TEST_BASH || (process.platform==='win32'?'C:/Program Files/Git/bin/bash.exe':'bash');
const shellAvailable={
    ps1:spawnSync(ps,['-NoProfile','-NonInteractive','-Command','exit 0'],{windowsHide:true,timeout:10000}).status===0,
    sh:spawnSync(bash,['--version'],{windowsHide:true,timeout:10000}).status===0,
};
function wrapperFixture(t,stem,shell){
    const root=fixture(t),mcp=path.join(root,'scripts/ai/mcp'),support=path.join(mcp,'support');
    fs.mkdirSync(support,{recursive:true});
    const file=path.join(mcp,`mcp_${stem}_wrapper.${shell}`);
    fs.copyFileSync(path.join(sourceMcp,path.basename(file)),file);fs.copyFileSync(helper,path.join(support,'host_transport.mjs'));
    fs.copyFileSync(path.join(sourceMcp,'support/invoke_host_transport.ps1'),path.join(support,'invoke_host_transport.ps1'));
    fs.writeFileSync(path.join(support,'load_repo_env.ps1'),'function Import-BioetlRepoEnv {}\n');
    fs.writeFileSync(path.join(support,'token_validation.ps1'),'function Test-McpOptionalToken {}\nfunction Test-McpRequiredToken {}\nfunction Exit-McpValidateOnly {}\n');
    fs.writeFileSync(path.join(support,'mcp_docker_prune.ps1'),'function Remove-McpExitedContainers {}\n');
    fs.writeFileSync(path.join(support,'load_repo_env.sh'),'load_repo_env_if_present() { :; }\n');
    fs.writeFileSync(path.join(support,'token_validation.sh'),'mcp_validate_optional_token() { :; }\nmcp_validate_required_token() { :; }\nmcp_exit_if_validate_only() { :; }\nmcp_prepare_npm_cache() { :; }\n');
    fs.writeFileSync(path.join(support,'mcp_docker_prune.sh'),'remove_mcp_exited_containers() { :; }\n');
    fs.writeFileSync(path.join(support,'docker_cli_resolver.sh'),'resolve_docker_bin() { printf docker; }\n');
    const driver=path.join(root,shell==='ps1'?'driver.ps1':'driver.sh');
    fs.writeFileSync(driver,shell==='ps1'?
        'function npx { [Console]::Out.Write("LEGACY_SENTINEL"); $global:LASTEXITCODE=0 }\nfunction docker { [Console]::Out.Write("LEGACY_SENTINEL"); $global:LASTEXITCODE=0 }\n$wrapperArgs=@($args|Select-Object -Skip 1)\n& $args[0] @wrapperArgs\nexit $LASTEXITCODE\n':
        'fake_bin="$BIOETL_TEST_FAKE_BIN"\nif command -v cygpath >/dev/null 2>&1; then fake_bin="$(cygpath -u "$fake_bin")"; fi\nexport PATH="$fake_bin:$PATH"\n[[ "$(command -v npx)" == "$fake_bin/npx" && "$(command -v docker)" == "$fake_bin/docker" ]] || exit 96\nbash "$@"\n');
    const bin=path.join(root,'bin');fs.mkdirSync(bin);
    for(const command of ['npx','docker'])fs.writeFileSync(path.join(bin,command),'#!/usr/bin/env bash\nprintf LEGACY_SENTINEL\n',{mode:0o755});
    return {root,file,driver,support,bin};
}
function wrapperRun(f,marker,shell,extra=[],updates={},input=undefined){
    const env={...process.env,PC_AGENT_MCP_ROUTES_FILE:marker,BIOETL_MCP_VALIDATE_ONLY:'0',BIOETL_TEST_FAKE_BIN:f.bin,...updates};
    return spawnSync(shell==='ps1'?ps:bash,shell==='ps1'?['-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',f.driver,f.file,...extra]:[f.driver,f.file,...extra],
        {env,input,encoding:'utf8',windowsHide:true,timeout:20000,cwd:fixtures});
}
for(const shell of ['ps1','sh'])for(const stem of ['context7','brave_search']){
    test(`${stem}.${shell}: route runs before legacy side effects and preserves stdout`,{skip:!shellAvailable[shell]},t=>{
        const f=wrapperFixture(t,stem,shell),marker=path.join(f.root,'policy.json');json(marker,policy(f.root));
        fs.writeFileSync(path.join(f.support,`load_repo_env.${shell}`),shell==='ps1'?'throw "LEGACY_SIDE_EFFECT"\n':'exit 93\n');
        const result=wrapperRun(f,marker,shell);assert.equal(result.status,0,result.stderr);assert.equal(result.stdout,'PROTOCOL_SENTINEL');assert.equal(result.stderr,'');
    });
    test(`${stem}.${shell}: unmanaged route preserves portable fallback`,{skip:!shellAvailable[shell]},t=>{
        const f=wrapperFixture(t,stem,shell),marker=path.join(f.root,'policy.json');json(marker,{workspaces:[]});
        const result=wrapperRun(f,marker,shell);assert.equal(result.status,0,result.stderr);assert.equal(result.stdout,'LEGACY_SENTINEL');
    });
    test(`${stem}.${shell}: failed managed adapter cannot trigger legacy fallback`,{skip:!shellAvailable[shell]},t=>{
        const f=wrapperFixture(t,stem,shell),marker=path.join(f.root,'policy.json');json(marker,policy(f.root,78));
        const result=wrapperRun(f,marker,shell);assert.equal(result.status,1,result.stderr);assert.equal(result.stdout,'PROTOCOL_SENTINEL');assert(!result.stdout.includes('LEGACY'));
        fs.writeFileSync(marker,'{broken');const malformed=wrapperRun(f,marker,shell);assert.equal(malformed.status,1);assert.equal(malformed.stdout,'');
    });
    test(`${stem}.${shell}: validation and extra arguments cannot start a provider`,{skip:!shellAvailable[shell]},t=>{
        const f=wrapperFixture(t,stem,shell),marker=path.join(f.root,'policy.json');json(marker,policy(f.root));
        const validated=wrapperRun(f,marker,shell,[],{BIOETL_MCP_VALIDATE_ONLY:'1'});assert.equal(validated.status,0,validated.stderr);assert.match(validated.stdout,/validation completed/);
        const extra=wrapperRun(f,marker,shell,['unexpected']);assert.equal(extra.status,1,extra.stderr);assert.equal(extra.stdout,'');
    });
    if(shell==='ps1')test(`${stem}.ps1: SDK environment without PATHEXT resolves Node`,{skip:!shellAvailable[shell]},t=>{
        const f=wrapperFixture(t,stem,shell),marker=path.join(f.root,'policy.json');json(marker,policy(f.root));
        // Undefined omits the variables, matching the MCP SDK's inherited-env whitelist.
        const result=wrapperRun(f,marker,shell,[],{PATHEXT:undefined,OS:undefined});
        assert.equal(result.status,0,result.stderr);assert.equal(result.stdout,'PROTOCOL_SENTINEL');
    });
    test(`${stem}.${shell}: protocol input is forwarded to the managed adapter`,{skip:!shellAvailable[shell]},t=>{
        const f=wrapperFixture(t,stem,shell),marker=path.join(f.root,'policy.json');
        const data=policy(f.root);const name=stem==='context7'?'context7':'brave-search';
        data.workspaces[0].entries[name].args=['-e',"process.stdin.on('data',b=>process.stdout.write(b))"];
        json(marker,data);const payload='{"jsonrpc":"2.0","id":1,"method":"initialize"}\n';
        const result=wrapperRun(f,marker,shell,[],{PATHEXT:undefined,OS:undefined},payload);
        assert.equal(result.status,0,result.stderr);assert.equal(result.stdout,payload);
    });
}
