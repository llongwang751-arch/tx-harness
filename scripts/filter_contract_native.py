"""Remove potential Skill bodies before an evaluator reads DSH's ordinary projection.

This is a privacy projection, not a product action or a replacement for raw evidence.
One output row is retained for every input row; removed fields are hashed separately.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,ntpath
from pathlib import Path

SAFE_TARGETS={'inputs/probe.txt','inputs/missing-probe.txt','missing-probe.txt',
              'probe.txt','outputs/echo.txt','outputs/receipt.json','prompt.txt'}
TOOLS={'read','write','edit','pwsh','glob','grep','ls'}

def field_hash(value):
    data=value.encode('utf-8') if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def safe_target(target,workspace):
    if not isinstance(target,str):return False
    target=ntpath.normpath(target.replace('/','\\'))
    base=ntpath.normpath(str(workspace)).rstrip('\\')
    if ntpath.isabs(target):
        prefix=base+'\\'
        if not target.casefold().startswith(prefix.casefold()):return False
        target=target[len(prefix):]
    return target.replace('\\','/').casefold() in SAFE_TARGETS

def project(records,workspace):
    calls={};out=[];audit=[]
    for line,original in enumerate(records,1):
        row=copy.deepcopy(original);event=row.get('event')
        if not isinstance(event,dict) or event.get('type') not in {'status','text','tool_call','tool_result'}:
            raise ValueError(f'Not an ordinary projected event at line {line}')
        kind=event['type'];call=event.get('callId');reason=None
        if kind=='tool_call':
            tool=event.get('tool');params=event.get('input',{})
            if not isinstance(call,str) or not call:reason='request has no attributable call identifier'
            elif tool not in TOOLS:reason='tool body outside fixed-contract allowlist'
            elif tool in {'read','write','edit'} and not safe_target(params.get('file_path'),workspace):reason='file body outside registered synthetic files'
            elif tool=='pwsh' and 'skill' in str(params.get('command','')).casefold():reason='command references Skill material'
            if isinstance(call,str) and call:calls[call]=reason
            fields=('input',) if reason else ()
        elif kind=='tool_result':
            reason=calls.get(call,'unpaired result has no safe request')
            fields=('result',) if reason else ()
        else:fields=()
        for field in fields:
            if field not in event:continue
            note={'source_physical_line':line,'pointer':'/event/'+field,
                  'original_field_sha256':field_hash(event.pop(field)),
                  'rule':reason,'replacement':None}
            row.setdefault('evaluator_redactions',[]).append(note);audit.append(note)
        out.append(row)
    return out,audit

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--slot',required=True);a=p.parse_args()
    from contract_v2 import paths,sha,save
    private,workspace,_=paths(a.slot);source=private/'visible-parent-events.jsonl'
    target=private/'ordinary-contract-events.jsonl';audit_path=private/'ordinary-contract-redactions.json'
    if target.exists() or audit_path.exists():raise ValueError('Refuse overwriting an existing privacy projection')
    rows=[json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
    projected,audit=project(rows,workspace)
    target.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in projected),encoding='utf-8',newline='\n')
    save(audit_path,{'source_file':source.name,'source_sha256':sha(source),'projection_file':target.name,
        'projection_sha256':sha(target),'source_rows':len(rows),'projected_rows':len(projected),
        'filter_source_sha256':sha(Path(__file__)),'raw_unchanged':True,'redactions':audit})
    print(json.dumps({'slot':a.slot,'rows':len(projected),'removed_fields':len(audit),'raw_unchanged':True}))

if __name__=='__main__':main()
