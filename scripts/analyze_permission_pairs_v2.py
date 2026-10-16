"""Audit S02's recorded launch conditions; no new metric or causal score.

Build from retained private launch receipts only with --from-private. --check needs
only public projections. Environment values stay private; their canonical digest
allows detecting a change in the explicitly configured file-tool environment.
"""
import argparse,copy,hashlib,json,re,tomllib
from pathlib import Path
from contract_v2 import ROOT,BASE,read,save,sha
from run_native_office_pilot import safe_public_text

OUT=ROOT/'reports/permission-pairs-v2.json'

def digest_value(v):
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()

def normalize_launch(args,workspace,repository,home):
    prefixes=[(str(workspace),'<participant-workspace>'),(str(repository),'<evaluation-repository>'),(str(home),'<user-home>')]
    def norm(v):
        if isinstance(v,dict):return {norm(k):norm(x) for k,x in v.items()}
        if isinstance(v,list):return [norm(x) for x in v]
        if not isinstance(v,str):return v
        v=v.replace('\\','/')
        for prefix,marker in prefixes:
            base=prefix.replace('\\','/').rstrip('/')
            v=re.sub(re.escape(base)+r'(?=/|$)',lambda _:marker,v,flags=re.I)
        return v
    config={};positionals=[];i=0
    while i<len(args):
        if args[i]=='-c':
            key,value=args[i+1].split('=',1);parsed=tomllib.loads('value='+value)['value']
            config[key]=({'values_omitted':True,'canonical_value_sha256':digest_value(parsed)}
                         if key=='shell_environment_policy.set' else norm(parsed));i+=2
        else:positionals.append(norm(args[i]));i+=1
    return {'positionals':positionals,'config':config}

def pair_summary(records):
    result=[]
    for rep in (1,2,3):
        rows={r['arm']:r for r in records if r['replicate']==rep}
        if set(rows)!={'allow','deny'}:
            result.append({'replicate':rep,'state':'incomplete','sealed_arms':sorted(rows)});continue
        a,d=rows['allow'],rows['deny'];left=copy.deepcopy(a['normalized_launch']);right=copy.deepcopy(d['normalized_launch'])
        key='permissions.harness_pilot.filesystem';target='<participant-workspace>/outputs'
        afs=left['config'].get(key,{});dfs=right['config'].get(key,{})
        arm_values={'allow':afs.pop(target,None),'deny':dfs.pop(target,None)}
        checks={'recorded_launch_equal_except_output_permission_and_normalized_paths':left==right,
                'expected_output_overrides':arm_values=={'allow':'write','deny':'read'},
                'cli_version_equal':a['version']==d['version'],
                'requested_model_equal':a['requested_model']==d['requested_model'],
                'input_sha256_equal':a['input_sha256']==d['input_sha256'],
                'prompt_sha256_equal':a['prompt_sha256']==d['prompt_sha256']}
        result.append({'replicate':rep,'state':'complete','slots':[a['slot_id'],d['slot_id']],
                       'actual_output_overrides':arm_values,'checks':checks,'all_recorded_checks_match':all(checks.values())})
    return result

def build():
    rows=[]
    for spec in read(BASE/'protocol.json')['slots']:
        if spec['card']!='S02':continue
        s=spec['slot_id'];public=ROOT/'public/supplements/contracts-v2'/s
        if not (public/'manifest.json').exists():continue
        private=ROOT/'private/contracts-v2'/s;start=read(public/'execution-start.json');plan=read(private/'plan.json')
        launch=read(private/'launch-private.json')
        rows.append({'slot_id':s,'replicate':spec['replicate'],'arm':spec['arm'],
             'public_manifest_sha256':sha(public/'manifest.json'),'private_launch_sha256':sha(private/'launch-private.json'),
             'version':start['version'],'requested_model':start['requested_model'],
             'input_sha256':sha(public/'inputs/probe.txt'),'prompt_sha256':sha(public/'submitted-prompt.txt'),
             'normalized_launch':normalize_launch(launch['args'],plan['workspace'],ROOT,Path.home())})
    result={'schema':'recorded-s02-pair-conditions-v2','records':rows,'pairs':pair_summary(rows),
      'normalization':'Windows path separators normalized; only exact workspace, evaluator repository and home prefixes replaced. Only outputs override removed for pair comparison. Explicit file-tool environment values replaced by their canonical SHA-256.',
      'limits':'A reviewed private-launch projection, not deployment or OS attestation. Unrecorded process environment, backend identity, service changes, fresh contexts, paths and time effects remain unresolved. No total, security-wide or pure Harness causal score.'}
    safe_public_text(json.dumps(result,ensure_ascii=False));return result

def check(data):
    safe_public_text(json.dumps(data,ensure_ascii=False))
    specs={s['slot_id']:s for s in read(BASE/'protocol.json')['slots'] if s['card']=='S02'}
    expected={s for s in specs if (ROOT/'public/supplements/contracts-v2'/s/'manifest.json').exists()}
    actual=[r['slot_id'] for r in data['records']]
    assert len(actual)==len(set(actual)) and set(actual)==expected,'Sealed arm coverage drift'
    assert data['pairs']==pair_summary(data['records']),'Pair audit drift'
    for row in data['records']:
        p=ROOT/'public/supplements/contracts-v2'/row['slot_id'];m=read(p/'metadata.json');start=read(p/'execution-start.json')
        spec=specs[row['slot_id']]
        assert row['arm']==spec['arm'] and row['replicate']==spec['replicate']
        assert sha(p/'manifest.json')==row['public_manifest_sha256']
        assert m['raw_records_sha256']['launch-private.json']==row['private_launch_sha256']
        assert sha(p/'inputs/probe.txt')==row['input_sha256'] and sha(p/'submitted-prompt.txt')==row['prompt_sha256']
        assert start['version']==row['version'] and start['requested_model']==row['requested_model']
        args=row['normalized_launch']['positionals']
        assert args[args.index('--model')+1]==row['requested_model'],'Actual requested model drift'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--from-private',action='store_true');p.add_argument('--check',action='store_true');a=p.parse_args()
    if a.from_private:save(OUT,build())
    data=read(OUT);check(data)
    print(json.dumps({'public_arms':len(data['records']),'complete_pairs':sum(r['state']=='complete' for r in data['pairs']),
                      'matching_complete_pairs':sum(r.get('all_recorded_checks_match') is True for r in data['pairs']),'verified':True}))
