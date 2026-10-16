"""Run a single frozen contract slot through its official CLI/SDK; default dry run."""
from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys,time,uuid
from pathlib import Path
from contract_v2 import ROOT,BASE,read,save,sha,now,slot,paths,prepare,inventory,verify_outputs,check_registration
from run_codex_pilot import native_codex,command,toml,public_command,run_stage,stop_tree
from run_dsh_sdk_pilot import SdkPeer

def launch_codex(w,spec):
    exe=native_codex();args=command(exe,w,'gpt-6.1-sol')
    if spec['card']=='S02':
        for i,part in enumerate(args):
            if part.startswith('permissions.harness_pilot.filesystem='):
                args[i]=part[:-1]+','+toml(str(w/'outputs'))+'='+toml('read' if spec['arm']=='deny' else 'write')+'}'
                break
        else:raise ValueError('Missing named permission profile')
    return exe,args

def run(s,execute=False):
    spec=slot(s);p,w,_=paths(s)
    if spec['product_id'] not in ('codex','dsh'):raise ValueError('GUI products require documented native CUA')
    if not execute:
        if spec['product_id']=='codex':
            exe,args=launch_codex(w,spec)
            version=subprocess.run([str(exe),'--version'],capture_output=True,text=True,check=True).stdout.strip()
            return {'slot':spec,'execute':False,'version':version,'command':public_command(args)}
        return {'slot':spec,'execute':False,'surface':'official desktop-bundled SDK','model':'deepseek-flash','effort':'high'}
    registration=read(ROOT/'private/contracts-v2/registration.json')
    check_registration(registration['commit'])
    if registration['protocol_sha256']!=sha(BASE/'protocol.json'):raise ValueError('Frozen registration mismatch')
    if not p.exists():prepare(s)
    if (p/'execution-start.json').exists() or (p/'run-started.json').exists():raise ValueError('Refuse result-based rerun')
    save(p/'run-started.json',{'at':now(),'registration_commit':registration['commit'],'slot':s})
    for source in (Path(__file__),ROOT/'scripts/run_codex_pilot.py',ROOT/'scripts/run_dsh_sdk_pilot.py',ROOT/'scripts/run_dsh_multiturn_pilot.py',ROOT/'scripts/run_dsh_pilot.py'):
        shutil.copyfile(source,p/'prepare-source'/source.name)
    prompt=(p/'submitted-prompt.txt').read_text(encoding='utf-8');budget=read(BASE/'protocol.json')['timeout_seconds']
    if spec['product_id']=='codex':
        exe,args=launch_codex(w,spec)
        version=subprocess.run([str(exe),'--version'],capture_output=True,text=True,check=True).stdout.strip()
        save(p/'launch-private.json',{'version':version,'args':args})
        start=time.monotonic();result=run_stage(args,prompt,w,p,'native',start,start+budget)
        save(p/'execution-start.json',{'started_at':result['submitted_at'],'registration_commit':registration['commit'],
            'start_basis':'actual native stdin write timestamp','surface':'official native CLI exec','version':version,
            'requested_model':'gpt-6.1-sol','backend_model_attested':False,'permission_arm':spec['arm']})
        end={'completion_observed_at':result['ended_at'],'timed_out':result['timed_out'],'native_exit_code':result['exit_code'],
             'completion_basis':'native process exit; semantic/contract completion evaluated separately','provider_completed_at':None}
    else:
        install=Path(os.environ['LOCALAPPDATA'])/'Programs/DeepSeek Harness'
        executable=install/'DeepSeek Harness.exe';cli=install/'resources/app.asar/dsh/node_modules/@deepseek-ai/dsh-desktop-host/lib/cli.js'
        patch=p/'one-run.patch.yml'
        patch.write_text('- id: skill-filesystem\n  config:\n    includeDefaultRoots: false\n    watch: false\n    bundledSkillDir: '+json.dumps(str(install/'resources/runtime/office-skills').replace('\\','/'),ensure_ascii=False)+'\n- id: tool-web\n  disabled: true\n',encoding='utf-8')
        args=[str(executable),'--expose-internals',str(cli),'--patch',str(patch),'--profile','sdk']
        save(p/'launch-private.json',{'args':args,'patch_sha256':sha(patch)})
        env=os.environ.copy();env['ELECTRON_RUN_AS_NODE']='1';env['DSH_PERMISSION_MODE']='workspace-write'
        proc=subprocess.Popen(args,cwd=w,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        peer=SdkPeer(proc,p,'contract-v2-'+str(uuid.uuid4()));end=None
        try:
            request,_=peer.send('initialize',{'cwd':str(w),'provider':'deepseek-account','model':'deepseek-flash','reasoningEffort':'high'})
            initialize=peer.response(request,time.monotonic()+120)
            start=time.monotonic();request,at=peer.send('session/prompt',{'sessionId':peer.session_id,'contentBlocks':[{'type':'text','text':prompt}]})
            save(p/'execution-start.json',{'started_at':at,'registration_commit':registration['commit'],'start_basis':'actual outgoing session/prompt timestamp',
                'surface':'official desktop-bundled SDK','requested_model':'deepseek-flash','requested_effort':'high','backend_model_attested':False})
            peer.response(request,start+budget)
            while time.monotonic()<start+budget:
                peer.consume()
                if peer.ends and peer.status=='idle':break
                if proc.poll() is not None:raise RuntimeError('SDK exited before ordinary turn completion')
            end={'completion_observed_at':now(),'timed_out':time.monotonic()>=start+budget,'completion_basis':'ordinary parent turn/end plus idle',
                'provider_completed_at':None,'parent_turn_ends':peer.ends,'initialize_result_private':True}
            if proc.poll() is None:
                request,_=peer.send('shutdown',{});peer.response(request,time.monotonic()+30)
                proc.stdin.close()
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:stop_tree(proc)
            end['native_exit_code']=proc.returncode
        except Exception as exc:
            save(p/'runtime-error.json',{'at':now(),'error':str(exc),'kind':'unclassified; explicit review required'})
            if end is None:end={'completion_observed_at':now(),'timed_out':False,'completion_basis':'runtime exception, see private error','provider_completed_at':None}
        finally:
            stop_tree(proc);peer.close_logs()
    receipts=[]
    for source in sorted((w/'outputs').rglob('*')):
        if not source.is_file():continue
        if source.is_symlink() or not source.resolve().is_relative_to(w.resolve()):raise ValueError('Output escaped participant workspace')
        rel=source.relative_to(w/'outputs');target=p/'outputs'/rel;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        if rel.as_posix() in ('echo.txt','receipt.json'):
            original=p/'native-downloads'/rel.name;shutil.copyfile(source,original)
            receipts.append({'native_file':'native-downloads/'+rel.name,'logical_output':rel.as_posix(),'origin':'native_local_file',
                'original_filename':rel.name,'sha256':sha(original),'bytes':original.stat().st_size,
                'downloaded_at':None,'original_bytes_captured_at':now(),'source_relative_path':'outputs/'+rel.as_posix(),
                'provenance_scope':'actual isolated participant workspace; copy is collection, not a native download'})
    end['original_capture_completed_at']=now()
    end['inputs_unchanged']=sha(w/'inputs/probe.txt')==read(p/'plan.json')['initial_workspace']['inputs/probe.txt']
    end['final_workspace_inventory_private']=inventory(w)
    save(p/'execution-end-private.json',end)
    end.pop('final_workspace_inventory_private')
    save(p/'execution-end.json',end);save(p/'download-receipts.json',{'artifacts':receipts})
    result=verify_outputs(p/'outputs',w/'inputs/probe.txt');save(p/'independent-verification.json',result)
    return {'finished':s,'private':str(p),'timed_out':end['timed_out'],**result}

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--slot',required=True);a.add_argument('--execute',action='store_true')
    args=a.parse_args();print(json.dumps(run(args.slot,args.execute),ensure_ascii=False))
