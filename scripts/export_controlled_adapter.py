"""Export reviewed fixture-only evidence; never publish raw prompts/SDK wire logs."""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tomllib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from controlled_model_fixture import marked_payloads

PRIVATE=ROOT/'private/controlled-adapter-v1'
PUBLIC=ROOT/'public/supplements/controlled-adapter-v1'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def lines(path):return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()] if path.is_file() else []
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def jsonl(path,values):path.write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in values),encoding='utf-8',newline='\n')

def sanitize(value,run_id):
    if isinstance(value,list):return [sanitize(v,run_id) for v in value]
    if isinstance(value,dict):return {sanitize(k,run_id):sanitize(v,run_id) for k,v in value.items()}
    if not isinstance(value,str):return value
    for raw,label in ((str(Path('D:/harness-controlled-v1')/run_id),'<RUN_ROOT>'),
                      (str(ROOT),'<EVAL_REPO>'),(str(PRIVATE/run_id),'<PRIVATE_EVIDENCE>'),
                      (sys.executable,'<PYTHON>'),(os.environ.get('USERPROFILE',''),' <USERPROFILE>')):
        if not raw:continue
        for variant in (raw.replace('\\','\\\\'),raw,raw.replace('\\','/')):
            value=value.replace(variant,label.strip())
    return value

def pid_alive(pid):
    if os.name!='nt':return None
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.restype=ctypes.c_void_p
    handle=kernel.OpenProcess(0x1000,False,pid)
    if not handle:return None if ctypes.get_last_error()==5 else False
    try:
        code=ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code)):return None
        return code.value==259
    finally:kernel.CloseHandle(ctypes.c_void_p(handle))

def project_launch(launch,run_id):
    if 'reviewed_actual_overrides' in launch:
        values=launch['reviewed_actual_overrides'].get('shell_environment_policy.set')
        if values is not None:
            summary={'variable_names':sorted(values),'values_withheld':True,
                'sha256':hashlib.sha256(json.dumps(values,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()}
            launch['environment_value_receipt']=summary
            launch['reviewed_actual_overrides']['shell_environment_policy.set']={'redacted':summary}
            launch['args']=[arg.split('=',1)[0]+'=<values withheld; see environment_value_receipt>'
                if arg.startswith('shell_environment_policy.set=') else arg for arg in launch['args']]
    return sanitize(launch,run_id)

def export(run_id):
    source=PRIVATE/run_id;target=PUBLIC/run_id
    target.mkdir(parents=True,exist_ok=False)
    execution=read(source/'execution.json');native=[];reviewed=[]
    projection_source=source/('native.stdout.jsonl' if execution['product_id']=='codex' else 'visible-parent-events.jsonl')
    original=lines(projection_source)
    accepted=False
    for number,row in enumerate(original,1):
        event=row if execution['product_id']=='codex' else row.get('event',{})
        provenance={'public_scene_line':len(reviewed)+1,'private_source_line':number}
        if execution['product_id']=='codex':
            item=event.get('item',{});kind=event.get('type')
            if kind=='turn.started':accepted=True
            permitted=kind in ('thread.started','turn.started','turn.completed','turn.failed','error') or (
                kind in ('item.started','item.completed') and (item.get('type') in ('agent_message','error') or
                item.get('type')=='mcp_tool_call' and item.get('server')=='contract' and item.get('tool')=='probe_commit'))
            if not permitted:continue
            reviewed.append(sanitize(event,run_id))
            if item.get('type')=='mcp_tool_call':
                common={'call_id':None,'native_item_id':item['id'],
                        'correlation':'Native CLI exposes item ID, not model call ID; unique frozen-argument call only',**provenance}
                if kind=='item.started':native.append({'kind':'tool_call',**common,'tool_name':'probe_commit','arguments':item['arguments']})
                if kind=='item.completed':
                    payloads=marked_payloads(item.get('result'))
                    native.append({'kind':'tool_result',**common,'payload':payloads[0] if len(payloads)==1 else None,
                        'is_error':None,'is_error_source':'not_exposed','native_status':item.get('status'),
                        'native_error':item.get('error')})
            if kind=='item.completed' and item.get('type')=='agent_message':
                native.append({'kind':'assistant_text','text':item['text'],**provenance})
            if kind in ('turn.completed','turn.failed'):
                native.append({'kind':'terminal','normal':kind=='turn.completed','reason':kind,
                               'exit_code':execution.get('exit_code'),**provenance})
        else:
            kind=event.get('type')
            if kind=='status' and event.get('phase')=='turn_start':accepted=True
            permitted=kind in ('status','text') or kind in ('tool_call','tool_result') and event.get('callId')=='call_controlled_1'
            if not permitted:continue
            reviewed.append(event)
            if kind=='tool_call':native.append({'kind':'tool_call','call_id':event['callId'],
                'tool_name':event['tool'],'arguments':event['input'],**provenance})
            if kind=='tool_result':
                payloads=marked_payloads(event.get('result'))
                native.append({'kind':'tool_result','call_id':event['callId'],'payload':payloads[0] if len(payloads)==1 else None,
                    'is_error':None,'is_error_source':'not_exposed','native_status':event.get('status'),**provenance})
            if kind=='text' and event.get('text'):native.append({'kind':'assistant_text','text':event['text'],**provenance})
            if kind=='status' and event.get('phase')=='turn_end':
                reason=event.get('reason',{}).get('kind')
                native.append({'kind':'terminal','normal':reason=='completed','reason':reason,
                               'exit_code':execution.get('exit_code'),**provenance})
    jsonl(target/'native-events.jsonl',native)
    jsonl(target/'reviewed-native-scene.jsonl',reviewed)
    execution.update(task_accepted=accepted,
        actual_submission_attempt=execution['actual_submitted'],
        actual_submitted=accepted,
        admission_definition='Ordinary native turn_start/turn.started observed; stdin write alone is only an attempt',
        calibration_issue='config_rejected' if not accepted else 'approval_blocked' if run_id=='CA02-codex-calibration' else None,
        source_original_execution_sha256=digest(source/'execution.json'),
        source_original_native_sha256=digest(projection_source),
        source_review='Only ordinary fixture tool, final text and status events; raw SDK/system/Skill content stays private')
    execution.setdefault('registration_file','calibration.json')
    mcp=lines(source/'mcp-events.jsonl')
    pids={row['pid'] for row in mcp}
    pids.add(read(source/'process.json')['pid'])
    execution['cleanup_observation']={'checked_after_all_runs':True,
        'only_recorded_test_processes':True,'pid_checks':[{'pid':pid,'alive':pid_alive(pid)} for pid in sorted(pids)],
        'limitation':'PID liveness after collection, not complete OS network/process provenance'}
    save(target/'execution.json',execution)
    launch=read(source/'launch.json')
    if execution['product_id']=='codex':
        overrides={}
        for index,arg in enumerate(launch['args']):
            if arg=='-c':
                key,value=launch['args'][index+1].split('=',1)
                try:overrides[key]=tomllib.loads('value='+value)['value']
                except tomllib.TOMLDecodeError:overrides[key]={'unparsed_original':value}
        launch['reviewed_actual_overrides']=overrides
    elif (source/'patch.json').is_file():launch['reviewed_actual_patch']=read(source/'patch.json')
    save(target/'launch.json',project_launch(launch,run_id))
    for name in ('model-events.jsonl','mcp-events.jsonl'):
        # These services log only the synthetic fixture and ordinary MCP protocol.
        if (source/name).is_file():shutil.copyfile(source/name,target/name)
        else:(target/name).write_bytes(b'')
    if not accepted:
        diagnostic=sanitize((source/'native.stderr.txt').read_text(encoding='utf-8'),run_id)
        (target/'admission-error.txt').write_text(diagnostic,encoding='utf-8',newline='\n')
    if (source/'collected/artifact.txt').is_file():
        (target/'collected').mkdir();shutil.copyfile(source/'collected/artifact.txt',target/'collected/artifact.txt')
    save(target/'manifest.json',{'schema':'controlled-fixture-evidence-manifest/v1','run_id':run_id,
         'files':[{'path':p.relative_to(target).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p)}
                  for p in sorted(target.rglob('*')) if p.is_file()]})
    print(json.dumps({'run_id':run_id,'accepted':accepted,'files':len(read(target/'manifest.json')['files']),
                     'remaining_test_pids':[p for p in execution['cleanup_observation']['pid_checks'] if p['alive']]},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-id',required=True)
    export(parser.parse_args().run_id)
