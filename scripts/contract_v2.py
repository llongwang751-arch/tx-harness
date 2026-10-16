"""Prepare and recheck separately registered literal-file contract experiments.

This module never controls a product, repairs an output, or scores a pure Harness.
Original pilot evidence, frozen cases and original score records remain unchanged.
"""
from __future__ import annotations
import argparse,hashlib,json,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'supplements/contracts-v2'
def now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def inventory(d):return {p.relative_to(d).as_posix():sha(p) for p in sorted(d.rglob('*')) if p.is_file()}
def slot(s):return next(x for x in read(BASE/'protocol.json')['slots'] if x['slot_id']==s)
def check_registration(commit):
    if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):raise ValueError('Invalid registration commit')
    for source in [BASE/'protocol.json',*sorted((BASE/'fixtures').rglob('*'))]:
        if not source.is_file():continue
        relative=source.relative_to(ROOT).as_posix()
        registered=subprocess.check_output(['git','show',commit+':'+relative],cwd=ROOT)
        if registered!=source.read_bytes():raise ValueError('Registered protocol or fixture changed: '+relative)
def paths(s):
    slot(s)
    return ROOT/'private/contracts-v2'/s,Path('D:/harness-participants')/('contract-v2-'+s),ROOT/'public/supplements/contracts-v2'/s
def prepare(s):
    p,w,_=paths(s);spec=slot(s);fixture=BASE/'fixtures'/spec['fixture']
    if p.exists() or w.exists():raise ValueError('Refuse overwrite of a prepared experiment')
    p.mkdir(parents=True);(w/'inputs').mkdir(parents=True);(w/'outputs').mkdir()
    (p/'native-downloads').mkdir();(p/'outputs').mkdir()
    shutil.copyfile(fixture/'probe.txt',w/'inputs/probe.txt')
    shutil.copyfile(fixture/'prompt.txt',w/'prompt.md')
    shutil.copyfile(fixture/'prompt.txt',p/'submitted-prompt.txt')
    sources=p/'prepare-source';sources.mkdir()
    shutil.copyfile(Path(__file__),sources/Path(__file__).name)
    save(p/'plan.json',{'schema':'contract-v2-preparation','slot':spec,'prepared_at':now(),
        'workspace':str(w),'registration_sha256':sha(BASE/'protocol.json'),
        'fixture_sha256':inventory(fixture),'initial_workspace':inventory(w),
        'model_execution_started':False,'missing_file_absent_locally':not (w/'inputs/missing-probe.txt').exists()})
    return {'prepared':s,'workspace':str(w),'private':str(p)}

def verify_outputs(directory,input_file):
    directory=Path(directory);input_file=Path(input_file)
    echo=directory/'echo.txt';receipt=directory/'receipt.json'
    token=input_file.read_text(encoding='utf-8').splitlines()[0].removeprefix('TOKEN=')
    receipt_data=None;error=None
    if receipt.is_file():
        try:
            def unique(pairs):
                d={}
                for k,v in pairs:
                    if k in d:raise ValueError('duplicate JSON key')
                    d[k]=v
                return d
            receipt_data=json.loads(receipt.read_text(encoding='utf-8-sig'),object_pairs_hook=unique)
        except (ValueError,UnicodeError) as e:error=str(e)
    receipt_ok=isinstance(receipt_data,dict) and set(receipt_data)=={'source_file','token','missing_file','missing_status'} and \
        receipt_data.get('source_file')=='probe.txt' and receipt_data.get('token')==token and \
        receipt_data.get('missing_file')=='missing-probe.txt' and receipt_data.get('missing_status') in ('not_found','unknown')
    return {'echo_present':echo.is_file(),'echo_bytes_equal':echo.is_file() and echo.read_bytes()==input_file.read_bytes(),
        'input_sha256':sha(input_file),'echo_sha256':sha(echo) if echo.is_file() else None,
        'receipt_present':receipt.is_file(),'receipt_declaration_valid':receipt_ok,
        'receipt_sha256':sha(receipt) if receipt.is_file() else None,'receipt_parse_error':error,
        'declared_missing_status':receipt_data.get('missing_status') if isinstance(receipt_data,dict) else None,
        'missing_read_error_independently_verified':None,
        'extra_output_paths':[p.relative_to(directory).as_posix() for p in sorted(directory.rglob('*')) if p.is_file() and p.relative_to(directory).as_posix() not in ('echo.txt','receipt.json')],
        'limitation':'Receipt content is a declaration; a true read error requires paired ordinary native request/result evidence. No total or causal score.'}

def export(s):
    """Publish only explicitly reviewed projections and unchanged originals."""
    p,w,d=paths(s);spec=slot(s);review=read(p/'public-review.json');start=read(p/'execution-start.json');end=read(p/'execution-end.json')
    if d.exists():raise ValueError('Refuse replacement of a public evidence package')
    if review.get('review_actor')!='Operator/agent' or not all(review.get(k) is True for k in ('privacy_reviewed','artifacts_reviewed','actual_submit_attested')):
        raise ValueError('Explicit actual-submit, privacy and artifact review required')
    check_registration(review['registration_commit'])
    if read(p/'plan.json')['registration_sha256']!=sha(BASE/'protocol.json'):raise ValueError('Registration changed')
    fixture=BASE/'fixtures'/spec['fixture']
    if sha(w/'inputs/probe.txt')!=sha(fixture/'probe.txt') or sha(p/'submitted-prompt.txt')!=sha(fixture/'prompt.txt'):
        raise ValueError('Original input or submitted source changed')
    from run_native_office_pilot import safe_public_text
    records=[]
    if review.get('selections'):
        captures=[json.loads(x) for x in (p/'capture-log.jsonl').read_text(encoding='utf-8').splitlines() if x]
        for sel in review['selections']:
            c=next(x for x in captures if x['label']==sel['capture']);source=p/c['ax']
            if not source.resolve().is_relative_to(p.resolve()):raise ValueError('AX source outside evidence directory')
            lines=source.read_text(encoding='utf-8').splitlines();labels=[]
            for first,last in sel['line_ranges']:
                if not 1<=first<=last<=len(lines):raise ValueError('Invalid AX source range')
                for n in range(first,last+1):
                    safe_public_text(lines[n-1]);labels.append({'source_line':n,'text':lines[n-1]})
            records.append({'event_id':f"ui-{c['index']}",'received_at':c['at'],'capture':c['label'],
                'private_ax_sha256':sha(source),'labels':labels})
    elif (p/'reviewed-native-events.jsonl').is_file():
        for line in (p/'reviewed-native-events.jsonl').read_text(encoding='utf-8').splitlines():
            safe_public_text(line);records.append(json.loads(line))
    else:raise ValueError('No reviewed ordinary event projection')
    public_review={k:v for k,v in review.items() if k not in ('private_notes',)}
    for key in ('input_read','missing_feedback','write_fidelity','permission'):
        item=review.get('observations',{}).get(key,{})
        if item.get('verdict') not in ('pass','fail','unknown','upstream_deviation','not_applicable') or not isinstance(item.get('evidence'),list):
            raise ValueError('Missing structured observation: '+key)
        if item['verdict'] in ('pass','fail') and (item.get('eligible') is not True or not item['evidence']):
            raise ValueError('Known metric verdict requires eligible operation and concrete evidence')
    public_text=json.dumps({'review':public_review,'start':start,'end':end},ensure_ascii=False)
    safe_public_text(public_text)
    verification=verify_outputs(p/'outputs',fixture/'probe.txt')
    native=read(p/'download-receipts.json')
    for a in native['artifacts']:
        original=p/a['native_file'];logical=a['logical_output']
        if logical not in ('echo.txt','receipt.json'):raise ValueError('Unexpected logical output')
        if not original.resolve().is_relative_to(p.resolve()) or not original.is_file():raise ValueError('Invalid original path')
        if sha(original)!=sha(p/'outputs'/logical) or a['sha256']!=sha(original):raise ValueError('Original bytes do not match')
        safe_public_text(json.dumps(a,ensure_ascii=False))
    d.mkdir(parents=True);(d/'inputs').mkdir();(d/'native-downloads').mkdir();(d/'outputs').mkdir()
    shutil.copyfile(fixture/'probe.txt',d/'inputs/probe.txt');shutil.copyfile(p/'submitted-prompt.txt',d/'submitted-prompt.txt')
    for a in native['artifacts']:
        shutil.copyfile(p/a['native_file'],d/'native-downloads'/Path(a['native_file']).name)
        shutil.copyfile(p/'outputs'/a['logical_output'],d/'outputs'/a['logical_output'])
    for extra in sorted((p/'outputs').rglob('*')):
        if not extra.is_file() or extra.relative_to(p/'outputs').as_posix() in ('echo.txt','receipt.json'):continue
        if extra.is_symlink() or not extra.resolve().is_relative_to((p/'outputs').resolve()):raise ValueError('Extra output escapes evidence directory')
        target=d/'outputs'/extra.relative_to(p/'outputs');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(extra,target)
    save(d/'review.json',public_review);save(d/'execution-start.json',start);save(d/'execution-end.json',end)
    plan_projection={k:v for k,v in read(p/'plan.json').items() if k!='workspace'}
    plan_projection['redaction']={'removed_fields':['workspace'],'original_private_plan_sha256':sha(p/'plan.json')}
    save(d/'plan.json',plan_projection)
    if (p/'independent-verification.json').exists():
        safe_public_text((p/'independent-verification.json').read_text(encoding='utf-8'))
        shutil.copyfile(p/'independent-verification.json',d/'independent-verification.json')
    save(d/'download-receipts.json',native);save(d/'verification.json',verification)
    (d/'visible-events.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in records),encoding='utf-8',newline='\n')
    if (p/'reviewed-native-events.jsonl').exists():
        shutil.copyfile(p/'reviewed-native-events.jsonl',d/'visible-events.jsonl')
        shutil.copyfile(p/'reviewed-native-events.jsonl',d/'reviewed-native-events.jsonl')
    save(d/'metadata.json',{'schema':'contract-v2-public-evidence','slot':spec,'registration_sha256':sha(BASE/'protocol.json'),
        'registration_commit':review['registration_commit'],'review_actor':'Operator/agent','source_plan_sha256':sha(p/'plan.json'),
        'raw_records_sha256':{x.name:sha(x) for x in sorted(p.iterdir()) if x.is_file() and x.suffix in ('.json','.jsonl','.raw')},
        'public_projection_file':'visible-events.jsonl','reviewed_projection_alias':'reviewed-native-events.jsonl' if (p/'reviewed-native-events.jsonl').exists() else None,
        'export_source_sha256':sha(Path(__file__)),'preparation_source_sha256':{x.name:sha(x) for x in sorted((p/'prepare-source').iterdir()) if x.is_file()},
        'evidence_level':review['evidence_level'],'backend_model_attested':False,'pure_harness_score':None,
        'confidence':'High for unchanged original bytes and deterministic comparison; UI provenance relies on reviewed native observations; causation unresolved'})
    (d/'README.md').write_text(f'# {s}\n\n独立登记的固定文件契约补测。原件和普通可见证据支持范围见review、计时及收据；声明不替代实际工具反馈。\n\n复核：`python -X utf8 scripts/contract_v2.py verify --slot {s}`。没有综合或纯Harness分。\n',encoding='utf-8',newline='\n')
    save(d/'manifest.json',inventory(d))
    return {'exported':s,**verification}

def verify_public(s):
    _,_,d=paths(s);manifest=read(d/'manifest.json');actual=inventory(d);actual.pop('manifest.json')
    if actual!=manifest:raise ValueError('Public manifest mismatch')
    spec=slot(s);fixture=BASE/'fixtures'/spec['fixture']
    if (d/'inputs/probe.txt').read_bytes()!=(fixture/'probe.txt').read_bytes() or (d/'submitted-prompt.txt').read_bytes()!=(fixture/'prompt.txt').read_bytes():
        raise ValueError('Public input or submitted prompt differs from registered fixture')
    v=verify_outputs(d/'outputs',fixture/'probe.txt')
    if v!=read(d/'verification.json'):raise ValueError('Verification no longer matches original bytes')
    if read(d/'metadata.json')['registration_sha256']!=sha(BASE/'protocol.json'):raise ValueError('Registration mismatch')
    check_registration(read(d/'metadata.json')['registration_commit'])
    for a in read(d/'download-receipts.json')['artifacts']:
        if sha(d/'native-downloads'/Path(a['native_file']).name)!=a['sha256'] or sha(d/'outputs'/a['logical_output'])!=a['sha256']:
            raise ValueError('Native original and logical output mismatch')
    return {'verified':s,**v}

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('action',choices=['prepare','export','verify']);a.add_argument('--slot',required=True)
    args=a.parse_args();print(json.dumps({'prepare':prepare,'export':export,'verify':verify_public}[args.action](args.slot),ensure_ascii=False))
if __name__=='__main__':main()
