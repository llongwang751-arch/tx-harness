"""Prepare/release/export a real CUA desktop pilot; never controls UI itself.

The human-reviewed AX slice file is required for export. Participant outputs are
copied byte-for-byte, including failures/extras; no retry or repair is performed.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from harness_eval.core import evaluate, inventory

def now(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p,x): p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def locations(case):
    name=f'workbuddy-{case}-desktop-r1'
    return name,Path('D:/harness-participants')/('pilot-'+name),ROOT/'private/pilots'/name,ROOT/'public/pilots'/name

def prepare(case):
    name,w,p,_=locations(case)
    if w.exists() or p.exists(): raise FileExistsError('Refuse overwrite/retry')
    w.mkdir(parents=True); p.mkdir(parents=True)
    shutil.copyfile(ROOT/'cases'/case/'prompt.md',w/'prompt.md')
    shutil.copytree(ROOT/'cases'/case/'inputs',w/'inputs');(w/'outputs').mkdir()
    prompt=(w/'prompt.md').read_text(encoding='utf-8')+'\n将交付文件写入 outputs/，不要修改 inputs/。\n'
    (p/'submitted-prompt.txt').write_bytes(prompt.encode('utf-8'))
    source=p/'collector-source';source.mkdir()
    for file in (Path(__file__),ROOT/'scripts/workbuddy_desktop_collector.mjs'): shutil.copyfile(file,source/file.name)
    save(p/'initial-inventory.json',inventory(w))
    save(p/'plan.json',{'run_id':name,'product_id':'workbuddy','case_id':case,'prepared_at':now(),
        'workspace':str(w),'source_prompt_sha256':sha(w/'prompt.md'),'submitted_prompt_sha256':sha(p/'submitted-prompt.txt'),
        'prompt_adapter_appendix':'将交付文件写入 outputs/，不要修改 inputs/。','timeout_seconds':1200,
        'formal_eligible':False,'collector_source_sha256':inventory(source)})
    print(json.dumps({'prepared':name,'initial_files':list(inventory(w)),'outputs_initially_empty':True},ensure_ascii=False))

def release(case,mode):
    if case!='T04': raise ValueError('Release allowed only for T04')
    _,w,p,_=locations(case);protocol=read(ROOT/'cases/T04/case.json')['release_protocol']
    if (p/'release.json').exists() or (w/'inputs/rates.json').exists(): raise FileExistsError('Exactly one release')
    start=read(p/'execution-start.json');started=datetime.fromisoformat(start['started_at'].replace('Z','+00:00'))
    observed=read(p/'observed-request.json') if mode=='active' else None
    if mode=='active' and (not observed or not observed.get('request_text')): raise ValueError('Actual semantic request needed')
    if mode=='passive' and (datetime.now(timezone.utc)-started).total_seconds()<120: raise ValueError('Too early for passive release')
    shutil.copytree(w/'outputs',p/'outputs-before-release')
    source=ROOT/'cases/T04'/protocol['release_files'][0]['source'];shutil.copyfile(source,w/'inputs/rates.json')
    available=now(); response=protocol['response_text'];(p/'supplement-prompt.txt').write_bytes(response.encode('utf-8'))
    save(p/'release.json',{'mode':mode,'file_available_at':available,'file_sha256':sha(w/'inputs/rates.json'),
        'source_file_sha256':sha(source),'seconds_since_initial_prompt':(datetime.fromisoformat(available)-started).total_seconds(),
        'observed_request':observed,'response_text':response,'response_text_sha256':sha(p/'supplement-prompt.txt'),
        'outputs_before_release':inventory(p/'outputs-before-release'),'observer_delay':'Product request emission time unknown; first observed time and file availability recorded separately'})
    print(json.dumps({'released':mode,'file_available_at':available,'file_sha256':sha(w/'inputs/rates.json')},ensure_ascii=False))

def export(case):
    name,w,p,d=locations(case)
    if d.exists(): raise FileExistsError('Refuse overwrite public package')
    plan=read(p/'plan.json');start=read(p/'execution-start.json');finish=read(p/'execution-end.json');review=read(p/'public-review.json')
    initial=read(p/'initial-inventory.json');final=inventory(w)
    unchanged=all(final.get(k)==v for k,v in initial.items())
    captures=[json.loads(l) for l in (p/'capture-log.jsonl').read_text(encoding='utf-8').splitlines()]
    by_label={r['label']:r for r in captures};events=[]
    for selection in review['selections']:
        cap=by_label[selection['capture']];ax=p/cap['ax'];lines=ax.read_text(encoding='utf-8').splitlines();items=[]
        for first,last in selection['line_ranges']:
            for i in range(first,last+1):
                line=lines[i-1].strip()
                if any(word in line.lower() for word in ('accountsnapshot','file://','thinking','reasoning','nickname','uid')) or re.search(r'[A-Z]:[/\\]+Users[/\\]',line,re.I): raise ValueError('Private field in reviewed selection')
                if '思考' in line: raise ValueError('Thought content is not publishable')
                items.append({'source_line':i,'text':line})
        events.append({'event_id':'ui-'+str(cap['index']),'kind':'native_ui_observation','received_at':cap['at'],'phase':cap['label'],'labels':items,'private_ax_sha256':sha(ax)})
    d.mkdir(parents=True);shutil.copyfile(w/'prompt.md',d/'case-prompt.md');shutil.copyfile(p/'submitted-prompt.txt',d/'submitted-prompt.txt')
    shutil.copytree(w/'inputs',d/'inputs');shutil.copytree(w/'outputs',d/'outputs');shutil.copytree(p/'collector-source',d/'collector-source')
    (d/'visible-events.jsonl').write_bytes(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in events).encode('utf-8'))
    verification=evaluate(ROOT/'cases'/case,d/'outputs');save(d/'verification.json',verification)
    release_record=read(p/'release.json') if (p/'release.json').exists() else None
    if release_record:
        save(d/'release.json',release_record);shutil.copytree(p/'outputs-before-release',d/'outputs-before-release');shutil.copyfile(p/'supplement-prompt.txt',d/'supplement-prompt.txt')
    completed=datetime.fromisoformat(finish['completion_observed_at'].replace('Z','+00:00'));started=datetime.fromisoformat(start['started_at'].replace('Z','+00:00'))
    meta={'run_id':name,'product_id':'workbuddy','case_id':case,'track':'pilot','formal_eligible':False,'formal_sample':False,
        'surface':'WorkBuddy 5.7.7 native desktop new task via documented CUA','visible_conditions':review['visible_conditions'],
        'underlying_model_version':None,'active_skills':None,'explicit_user_skill_selected':False,'skills_disabled_verified':False,
        'os_sandbox_verified':False,'network_absence_independently_verified':False,'actual_tool_calls':None,
        'started_at':start['started_at'],'completion_observed_at':finish['completion_observed_at'],
        'elapsed_to_completion_observation_seconds':(completed-started).total_seconds(),'timed_out':finish.get('timed_out',False),
        'timing_basis':'Send-action pre-receipt to first observed completed UI; service finish time unknown; observer interval is an upper bound',
        'initial_inventory':initial,'final_inventory':final,'original_inputs_and_prompt_unchanged':unchanged,
        'case_prompt_sha256':sha(d/'case-prompt.md'),'actual_paste_source_sha256':sha(d/'submitted-prompt.txt'),
        'prompt_adapter_appendix':plan['prompt_adapter_appendix'],'prompt_transport':'Actual file bytes decoded UTF-8 and native CUA pasted; internal model-request bytes unknown',
        'source_snapshot_sha256':inventory(d/'collector-source'),'product_deliverables':inventory(d/'outputs'),
        'release':release_record,'objective_score':verification['objective_score'],'total_score':None,'manual_score':None,'pure_harness_score':None,
        'output_repairs_by_evaluator':False,'unscheduled_prompts':[],'completion_basis':finish['completion_basis'],
        'confidence':'High for byte-preserved artifacts/independent criteria and explicitly visible labels; internal execution/attribution unresolved',
        'attribution':'Recorded end-to-end configuration only; no pure Harness causal conclusion',
        'collector_issues':review.get('collector_issues',[]),
        'redaction':'Human-reviewed exact AX line slices only; all thought/planning sections, account URL/ID, private sidebars, raw screenshots/system context omitted',
        'private_capture_sha256':{r['ax']:sha(p/r['ax']) for r in captures},
        'limitations':['One exploratory attempt; not an independent replicate per tool or artifact.','Model selector label does not attest backend deployment.','Active builtin/user Skills and full tool arguments are unknown.','Visible artifact/incident declarations do not prove network isolation or internal recovery responsibility.']}
    save(d/'metadata.json',meta)
    passed=sum(c['passed'] for c in verification['checks']);extras=set(inventory(d/'outputs'))-set(read(ROOT/'cases'/case/'case.json')['required_outputs'])
    readme=f'# WorkBuddy {case} 原生桌面预试\n\n真实新任务；没有修复产物、额外策略提示或选择性重试。客观检查 {passed}/{len(verification["checks"])}，{verification["objective_score"]}/60；额外原生产物{len(extras)}份全部保留。原始输入和题目未改：{unchanged}。\n\n完成观察上界{meta["elapsed_to_completion_observation_seconds"]:.3f}秒，精确服务时刻未知。模型/权限/账户可见条件见metadata；实际底模、Skill与完整工具调用不可见。E2现场只公开审阅的配置/执行标签和最终答复，思考、账号和私有历史不公开。\n\n一个探索性episode，正式样本0；manual、总分、纯Harness分null。T04的release文件及补发前产物（如有）单列，不用incident声明替代实际现场。\n\n复核：`python -X utf8 -m harness_eval verify --case {case} --outputs public/pilots/{name}/outputs`。manifest覆盖原字节证据；哈希不单独证明来源真实性。\n'
    (d/'README.md').write_bytes(readme.encode('utf-8'));save(d/'manifest.json',inventory(d,exclude=('manifest.json',)))
    print(json.dumps({'exported':name,'checks':f'{passed}/{len(verification["checks"])}','objective_score':verification['objective_score'],'extra_outputs':len(extras),'unchanged':unchanged},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','release','export'));parser.add_argument('--case',required=True,choices=('T02','T03','T04','T05'));parser.add_argument('--mode',choices=('active','passive'))
    a=parser.parse_args()
    if a.action=='prepare':prepare(a.case)
    elif a.action=='release':release(a.case,a.mode)
    else:export(a.case)
