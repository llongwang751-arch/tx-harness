"""Run one real official Harness against the fixed local model/MCP fixture.

No paid/remote model, existing credentials or global user settings are used.
Run once per registered ID. Transport calibration is retained separately from
the later frozen four-arm component comparison. Never run arms concurrently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from controlled_model_fixture import FixtureServer, MODEL, MARKER, encoded, now, sha
from run_codex_pilot import native_codex, command, toml, stop_tree
from run_dsh_sdk_pilot import SdkPeer

BASE=ROOT/'supplements/controlled-adapter-v1'
WORK=Path('D:/harness-controlled-v1')
PRIVATE=ROOT/'private/controlled-adapter-v1'


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return sha(path.read_bytes())


def clean_environment():
    allowed={'PATH','SYSTEMROOT','SYSTEMDRIVE','WINDIR','COMSPEC','PATHEXT','USERPROFILE',
             'APPDATA','LOCALAPPDATA','TEMP','TMP','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMDATA'}
    return {key:value for key,value in os.environ.items() if key.upper() in allowed}


def verify_registration(commit,phase,filename=None):
    protocol_path=BASE/(filename or ('calibration.json' if phase=='calibration' else 'protocol.json'))
    if protocol_path.parent.resolve()!=BASE.resolve():
        raise ValueError('Registration must be directly in the controlled supplement')
    relative=protocol_path.relative_to(ROOT).as_posix()
    if subprocess.check_output(['git','show',f'{commit}:{relative}'],cwd=ROOT)!=protocol_path.read_bytes():
        raise ValueError('Protocol differs from registered git blob')
    protocol=read(protocol_path)
    if protocol['phase']!=phase:
        raise ValueError('Registration phase differs')
    for name,spec in protocol['files'].items():
        path=ROOT/name
        if digest(path)!=spec['sha256'] or path.stat().st_size!=spec['bytes']:
            raise ValueError('Frozen fixture/adapter changed: '+name)
        if subprocess.check_output(['git','show',f'{commit}:{name}'],cwd=ROOT)!=path.read_bytes():
            raise ValueError('Registered adapter blob differs: '+name)
    return protocol


def config_toml(value):
    # JSON arrays of objects are not TOML arrays of inline tables. The legacy
    # helper predates this fixture; keep old frozen launchers unchanged.
    if isinstance(value,list):return '['+','.join(config_toml(item) for item in value)+']'
    if isinstance(value,dict):return '{'+','.join(toml(key)+'='+config_toml(item) for key,item in value.items())+'}'
    return toml(value)


def codex_launch(workspace,home,tool,mode,journal,base_url):
    exe=native_codex()
    args=command(exe,workspace,MODEL)
    args.pop()  # stdin prompt sentinel; append explicit one-run overrides first.
    overrides={
        'model_provider':'controlled',
        'model_providers.controlled':{'name':'Controlled local fixture','base_url':base_url,
            'wire_api':'responses','requires_openai_auth':False,'supports_websockets':False,
            'request_max_retries':0,'stream_max_retries':0,'stream_idle_timeout_ms':30000},
        'features.prefer_mxc':False,
        'features.skill_mcp_dependency_install':False,
        'skills.config':[{'path':str(home/'skills/.system'/name),'enabled':False}
                         for name in ('imagegen','openai-docs','skill-creator','skill-installer')],
        'mcp_servers.contract':{'command':sys.executable,
            'args':[str(tool),'--workspace',str(workspace),'--mode',mode,'--journal',str(journal)],
            'cwd':str(workspace),'enabled':True,'required':True,
            'default_tools_approval_mode':'auto','startup_timeout_sec':20,'tool_timeout_sec':20}}
    for key,value in overrides.items():args+=['-c',key+'='+config_toml(value)]
    args+=['-']
    env=clean_environment();env['CODEX_HOME']=str(home)
    return exe,args,env


def dsh_launch(runroot,workspace,tool,mode,journal,base_url):
    # This whitelist API template was read from current official installed code;
    # it contains no existing account/profile/Skill content.
    # YAML supports JSON flow mappings; use a complete JSON-compatible list to
    # avoid escaping paths into YAML source through string interpolation.
    disabled=['skill-filesystem','skill-office','tool-skill','agent-instructions',
        'llm-deepseek','llm-deepseek-account','session-log-deepseek',
        'plugin-package-inventory-deepseek','session-telemetry-otel','tool-web',
        'tool-plugin-manager','tool-subagent','tool-subagent-fork','tool-subagent-control',
        'tool-subagent-list-agents','tool-workflow']
    patch=[{'id':'llm-pi-ai','config':{'providers':{'controlled':{
        'apiKeyEnv':'HARNESS_CONTROLLED_PLACEHOLDER_KEY','api':'openai-completions','baseURL':base_url,
        'retryPolicy':{'mode':'normal','maxRetries':0},'models':[{'id':MODEL,'name':MODEL,
            'contextWindow':262144,'maxTokens':1024,'input':['text'],'reasoningEfforts':False}]}}}}]
    patch += [{'id':name,'disabled':True} for name in disabled]
    patch += [{'insert':[{'id':'mcp-controlled-contract','name':'@deepseek-ai/dsh-mcp-client',
        'config':{'serverName':'contract','transport':'stdio','command':sys.executable,
            'args':[str(tool),'--workspace',str(workspace),'--mode',mode,'--journal',str(journal)],
            'cwd':str(workspace),'env':{},'failOnStartupError':True,'toolCallTimeoutMs':20000,
            'reconnect':{'enabled':False}}}]}]
    patch_path=runroot/'single-run.patch.yml'
    save(patch_path,patch)
    install=Path(os.environ['LOCALAPPDATA'])/'Programs/DeepSeek Harness'
    exe=install/'DeepSeek Harness.exe'
    cli=install/'resources/app.asar/dsh/node_modules/@deepseek-ai/dsh-desktop-host/lib/cli.js'
    args=[str(exe),'--expose-internals',str(cli),'--profile','sdk','--patch',str(patch_path)]
    env=clean_environment()
    env.update({'ELECTRON_RUN_AS_NODE':'1','DSH_HOME':str(runroot/'dsh-home'),
                'DSH_AGENTS_HOME':str(runroot/'agents-home'),
                'HARNESS_CONTROLLED_PLACEHOLDER_KEY':'non-secret-local-test-only',
                'DSH_TELEMETRY_DISABLED':'1','DSH_MAX_TOKENS_AS_SUCCESS':'false'})
    return exe,args,env,patch


def codex_turn(args,env,workspace,evidence,prompt,deadline):
    proc=subprocess.Popen(args,cwd=workspace,env=env,stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    save(evidence/'process.json',{'pid':proc.pid,'started_at':now(),'executable':args[0]})
    threads=[]
    def drain(stream,target):
        with target.open('wb') as f:
            for block in iter(lambda:stream.read(8192),b''):
                f.write(block);f.flush()
    for stream,name in ((proc.stdout,'native.stdout.jsonl'),(proc.stderr,'native.stderr.txt')):
        t=threading.Thread(target=drain,args=(stream,evidence/name),daemon=True);t.start();threads.append(t)
    submitted=now()
    try:
        proc.stdin.write(prompt.encode('utf-8'));proc.stdin.close()
        save(evidence/'submission.json',{'at':submitted,'actual_submitted':True,'method':'native_cli_stdin'})
        proc.wait(timeout=max(1,deadline-time.monotonic()))
        return {'exit_code':proc.returncode,'completed_at':now()}
    finally:
        stop_tree(proc)
        for t in threads:t.join(timeout=5)


def dsh_turn(args,env,workspace,evidence,prompt,run_id,deadline):
    proc=subprocess.Popen(args,cwd=workspace,env=env,stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
    save(evidence/'process.json',{'pid':proc.pid,'started_at':now(),'executable':args[0]})
    peer=SdkPeer(proc,evidence,run_id)
    try:
        request,_=peer.send('initialize',{'cwd':str(workspace),'provider':'controlled','model':MODEL,'maxTokens':1024})
        initialized=peer.response(request,deadline)
        save(evidence/'initialize.json',initialized)
        request,at=peer.send('session/prompt',{'sessionId':run_id,'contentBlocks':[{'type':'text','text':prompt}]})
        save(evidence/'submission.json',{'at':at,'actual_submitted':True,'method':'official_sdk_session_prompt'})
        peer.response(request,deadline)
        request,_=peer.send('session/wait',{'sessionId':run_id})
        wait=peer.response(request,deadline)
        save(evidence/'wait.json',{'at':now(),'result':wait,'status':peer.status,'turn_ends':peer.ends})
        request,_=peer.send('shutdown',{})
        peer.response(request,deadline)
        proc.stdin.close()
        proc.wait(timeout=min(10,max(1,deadline-time.monotonic())))
        return {'exit_code':proc.returncode,'completed_at':now()}
    finally:
        stop_tree(proc);peer.close_logs()


def run(run_id,phase,commit,filename=None):
    protocol=verify_registration(commit,phase,filename)
    spec=next(r for r in protocol['runs'] if r['run_id']==run_id)
    evidence=PRIVATE/run_id
    evidence.mkdir(parents=True,exist_ok=False)
    runroot=WORK/run_id
    runroot.mkdir(parents=True,exist_ok=False)
    workspace=runroot/'work';workspace.mkdir()
    for folder in ('codex-home','dsh-home','agents-home'):(runroot/folder).mkdir()
    runtime=runroot/'runtime';runtime.mkdir()
    tool=runtime/'controlled_probe_mcp.py'
    shutil.copyfile(ROOT/'scripts/controlled_probe_mcp.py',tool)
    fixture=read(BASE/'fixture.json')
    prompt=(BASE/'prompt.txt').read_text(encoding='utf-8')
    started=time.monotonic()
    result={'run_id':run_id,'phase':phase,'product_id':spec['product_id'],'mode':spec['mode'],
        'registration_commit':commit,'registration_file':filename or ('calibration.json' if phase=='calibration' else 'protocol.json'),
        'started_at':now(),'initial_workspace_inventory':[],
        'model_kind':'deterministic_local_transport_fixture','real_model_inference':False,
        'shared_tool_sha256':digest(tool),'frozen_arguments_sha256':sha(encoded(fixture['arguments'])),
        'timeout_seconds':protocol['timeout_seconds']}
    save(evidence/'execution-start.json',result)
    with FixtureServer(fixture['arguments'],evidence/'model-events.jsonl') as server:
        if spec['product_id']=='codex':
            exe,args,env=codex_launch(workspace,runroot/'codex-home',tool,spec['mode'],evidence/'mcp-events.jsonl',server.base_url)
            result['version']=subprocess.check_output([str(exe),'--version'],text=True).strip()
            result['skill_configuration']='Fresh isolated CODEX_HOME; host discovery skipped; plugins/hooks/memories/apps off; four packaged system-skill paths explicitly disabled; actual fixture path checked separately.'
            launch=codex_turn
        else:
            exe,args,env,patch=dsh_launch(runroot,workspace,tool,spec['mode'],evidence/'mcp-events.jsonl',server.base_url)
            result['version']=protocol['installed_versions']['dsh']
            result['skill_configuration']='Fresh DSH_HOME/DSH_AGENTS_HOME; filesystem and Office providers, Skill tool and agent-instructions disabled by one-run patch.'
            save(evidence/'patch.json',patch)
            launch=dsh_turn
        result['executable_sha256']=digest(exe)
        expected=protocol['executables'][spec['product_id']]
        if result['executable_sha256']!=expected['sha256'] or exe.stat().st_size!=expected['bytes']:
            raise ValueError('Installed executable differs from registered build')
        if spec['product_id']=='codex' and result['version']!=protocol['installed_versions']['codex']:
            raise ValueError('Installed Codex version changed')
        save(evidence/'launch.json',{'args':args,'environment_names':sorted(env),
              'external_credentials_forwarded':False,'base_url':server.base_url,
              'workspace':str(workspace),'version':result['version']})
        try:
            if spec['product_id']=='codex':
                terminal=launch(args,env,workspace,evidence,prompt,started+protocol['timeout_seconds'])
            else:
                terminal=launch(args,env,workspace,evidence,prompt,run_id,started+protocol['timeout_seconds'])
            result.update(terminal)
        except Exception as exc:
            result.update(runtime_error={'type':type(exc).__name__,'message':str(exc)},completed_at=now())
        result['local_model_requests']=server.state.requests
    file=workspace/'artifact.txt'
    if file.is_file():
        target=evidence/'collected/artifact.txt';target.parent.mkdir()
        with target.open('xb') as f:f.write(file.read_bytes())
        result['artifact']={'bytes':target.stat().st_size,'sha256':digest(target),'acquired_at':now()}
    else:
        result['artifact']=None
    result['ended_at']=now();result['elapsed_seconds']=time.monotonic()-started
    result['actual_submitted']=(evidence/'submission.json').is_file()
    result['mcp_journal_present']=(evidence/'mcp-events.jsonl').is_file()
    save(evidence/'execution.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-id',required=True)
    p.add_argument('--phase',choices=['calibration','main'],required=True)
    p.add_argument('--registration',required=True)
    p.add_argument('--protocol',help='Explicit immutable registration filename for a new calibration revision')
    a=p.parse_args();run(a.run_id,a.phase,a.registration,a.protocol)
